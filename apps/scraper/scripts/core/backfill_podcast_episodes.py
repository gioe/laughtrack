#!/usr/bin/env python3
"""Backfill canonical podcast episode rows for accepted PodcastIndex feeds."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from curl_cffi import requests
from dotenv import dotenv_values

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger

_SOURCE = "podcast_index"
_PODCAST_INDEX_EPISODES_BY_FEED_ID_URL = "https://api.podcastindex.org/api/1.0/episodes/byfeedid"
_DEFAULT_MAX_EPISODES_PER_FEED = 100
_MAX_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0
_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PodcastIndexCredentials:
    api_key: str
    api_secret: str
    user_agent: str = "LaughTrack/1.0"


@dataclass(frozen=True)
class AcceptedPodcastFeed:
    podcast_id: int
    source_podcast_id: str
    feed_url: Optional[str]
    title: str
    comedian_ids: list[int]
    comedian_names: list[str]
    association_types: list[str]


@dataclass(frozen=True)
class PodcastEpisodeRow:
    podcast_id: int
    source: str
    source_episode_id: str
    guid: Optional[str]
    title: str
    description: Optional[str]
    release_date: Optional[str]
    duration_seconds: Optional[int]
    episode_url: Optional[str]
    audio_url: Optional[str]
    external_ids: dict[str, Any]
    evidence: dict[str, Any]
    source_payload: dict[str, Any]


@dataclass
class BackfillSummary:
    feeds_scanned: int = 0
    episodes_inserted: int = 0
    episodes_updated: int = 0
    episodes_skipped: int = 0
    api_failures: int = 0
    per_feed_errors: list[str] = field(default_factory=list)


_LOAD_ACCEPTED_FEEDS_SQL = """
    SELECT DISTINCT
        p.id,
        p.source_podcast_id,
        p.feed_url,
        p.title,
        cp.comedian_id,
        c.name,
        cp.association_type
    FROM comedian_podcasts cp
    JOIN podcasts p ON p.id = cp.podcast_id
    JOIN comedians c ON c.id = cp.comedian_id
    WHERE cp.review_status = 'accepted'
      AND p.source = %s
      AND (%s::text[] IS NULL OR p.source_podcast_id = ANY(%s::text[]))
      AND (%s::int[] IS NULL OR cp.comedian_id = ANY(%s::int[]))
      AND (%s::text[] IS NULL OR c.name = ANY(%s::text[]))
    ORDER BY p.id, cp.comedian_id
    {limit_clause}
"""

_UPSERT_EPISODE_SQL = """
    INSERT INTO podcast_episodes (
        podcast_id,
        source,
        source_episode_id,
        guid,
        title,
        description,
        release_date,
        duration_seconds,
        episode_url,
        audio_url,
        external_ids,
        evidence,
        source_payload
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
    ON CONFLICT (source, source_episode_id) DO UPDATE SET
        podcast_id = EXCLUDED.podcast_id,
        guid = COALESCE(EXCLUDED.guid, podcast_episodes.guid),
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        release_date = EXCLUDED.release_date,
        duration_seconds = EXCLUDED.duration_seconds,
        episode_url = EXCLUDED.episode_url,
        audio_url = EXCLUDED.audio_url,
        external_ids = EXCLUDED.external_ids,
        evidence = EXCLUDED.evidence,
        source_payload = EXCLUDED.source_payload,
        updated_at = NOW()
    RETURNING (xmax = 0) AS inserted
"""


def _load_env_defaults(path: Path = Path(".env")) -> None:
    for key, value in dotenv_values(path).items():
        if value:
            os.environ.setdefault(key, value)


def _load_podcast_index_credentials() -> PodcastIndexCredentials:
    _load_env_defaults()
    api_key = os.environ.get("PODCASTINDEX_API_KEY") or os.environ.get("PODCAST_INDEX_API_KEY")
    api_secret = os.environ.get("PODCASTINDEX_API_SECRET") or os.environ.get(
        "PODCAST_INDEX_API_SECRET"
    )
    user_agent = os.environ.get("PODCASTINDEX_USER_AGENT") or os.environ.get(
        "PODCAST_INDEX_USER_AGENT",
        "LaughTrack/1.0",
    )
    if not api_key or not api_secret:
        print(
            "Error: set PODCASTINDEX_API_KEY and PODCASTINDEX_API_SECRET before "
            "running this script.",
            file=sys.stderr,
        )
        sys.exit(2)
    return PodcastIndexCredentials(api_key=api_key, api_secret=api_secret, user_agent=user_agent)


def _build_podcast_index_headers(credentials: PodcastIndexCredentials) -> dict[str, str]:
    auth_date = str(int(time.time()))
    authorization = hashlib.sha1(
        f"{credentials.api_key}{credentials.api_secret}{auth_date}".encode("utf-8")
    ).hexdigest()
    return {
        "User-Agent": credentials.user_agent,
        "X-Auth-Date": auth_date,
        "X-Auth-Key": credentials.api_key,
        "Authorization": authorization,
        "Accept": "application/json",
    }


def _parse_bound_timestamp(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        return int(raw)
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _iso_from_timestamp(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _string_or_none(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _int_or_none(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _episode_url_from_payload(episode: dict[str, Any]) -> Optional[str]:
    for key in ("link", "episodeUrl", "url"):
        value = _string_or_none(episode.get(key))
        if value and value.startswith(("http://", "https://")):
            return value
    return None


def _audio_url_from_payload(episode: dict[str, Any]) -> Optional[str]:
    for key in ("enclosureUrl", "audioUrl"):
        value = _string_or_none(episode.get(key))
        if value and value.startswith(("http://", "https://")):
            return value
    return None


def _source_episode_id(episode: dict[str, Any]) -> Optional[str]:
    episode_id = episode.get("id")
    if episode_id not in (None, ""):
        return str(episode_id)
    guid = _string_or_none(episode.get("guid"))
    if guid:
        return f"guid:{guid}"
    url = _episode_url_from_payload(episode) or _audio_url_from_payload(episode)
    if url:
        return f"url:{hashlib.sha1(url.encode('utf-8')).hexdigest()}"
    return None


def _extract_episodes(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        values = payload
    else:
        values = payload.get("items") or payload.get("episodes") or []
    return [item for item in values if isinstance(item, dict)]


def _episode_matches_until_bound(episode: dict[str, Any], until_ts: Optional[int]) -> bool:
    if until_ts is None:
        return True
    published = _int_or_none(episode.get("datePublished"))
    return published is None or published <= until_ts


def load_accepted_feeds(
    *,
    feed_ids: Optional[list[str]],
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    limit: Optional[int],
) -> list[AcceptedPodcastFeed]:
    limit_clause = "LIMIT %s" if limit else ""
    query = _LOAD_ACCEPTED_FEEDS_SQL.format(limit_clause=limit_clause)
    params: list[Any] = [
        _SOURCE,
        feed_ids,
        feed_ids,
        comedian_ids,
        comedian_ids,
        comedian_names,
        comedian_names,
    ]
    if limit:
        params.append(int(limit))

    grouped: dict[int, dict[str, Any]] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            for row in cur.fetchall():
                podcast_id = int(row[0])
                group = grouped.setdefault(
                    podcast_id,
                    {
                        "podcast_id": podcast_id,
                        "source_podcast_id": str(row[1]),
                        "feed_url": row[2],
                        "title": str(row[3]),
                        "comedian_ids": [],
                        "comedian_names": [],
                        "association_types": [],
                    },
                )
                comedian_id = int(row[4])
                if comedian_id not in group["comedian_ids"]:
                    group["comedian_ids"].append(comedian_id)
                comedian_name = str(row[5])
                if comedian_name not in group["comedian_names"]:
                    group["comedian_names"].append(comedian_name)
                association_type = str(row[6])
                if association_type not in group["association_types"]:
                    group["association_types"].append(association_type)

    return [AcceptedPodcastFeed(**group) for group in grouped.values()]


def _build_fetch_params(
    feed: AcceptedPodcastFeed,
    *,
    max_episodes_per_feed: int,
    since: Optional[str],
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "id": feed.source_podcast_id,
        "max": max_episodes_per_feed,
        "fulltext": "",
    }
    since_ts = _parse_bound_timestamp(since)
    if since_ts is not None:
        params["since"] = since_ts
    return params


def _retry_after_seconds(headers: dict[str, str] | None, attempt: int) -> float:
    retry_after = (headers or {}).get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    return _BASE_RETRY_DELAY_S * (2**attempt)


def fetch_feed_episodes(
    feed: AcceptedPodcastFeed,
    credentials: PodcastIndexCredentials,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.get(
                _PODCAST_INDEX_EPISODES_BY_FEED_ID_URL,
                headers=_build_podcast_index_headers(credentials),
                params=params,
                timeout=_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            if attempt + 1 >= _MAX_RETRIES:
                raise RuntimeError(
                    f"fetch failed for feed {feed.source_podcast_id}: {exc}"
                ) from exc
            time.sleep(_BASE_RETRY_DELAY_S * (2**attempt))
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt + 1 >= _MAX_RETRIES:
                raise RuntimeError(
                    f"HTTP {response.status_code} for feed {feed.source_podcast_id} "
                    f"after {_MAX_RETRIES} attempts"
                )
            time.sleep(_retry_after_seconds(response.headers, attempt))
            continue
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code} for feed {feed.source_podcast_id}")
        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"non-JSON response for feed {feed.source_podcast_id}: {exc}"
            ) from exc
        if isinstance(data, dict) and data.get("status") not in (None, True, "true"):
            raise RuntimeError(
                f"unsuccessful PodcastIndex response for feed {feed.source_podcast_id}: {data}"
            )
        return _extract_episodes(data)
    return []


def episode_from_payload(
    *,
    podcast_id: int,
    source_podcast_id: str,
    episode: dict[str, Any],
) -> Optional[PodcastEpisodeRow]:
    source_episode_id = _source_episode_id(episode)
    title = _string_or_none(episode.get("title"))
    if not source_episode_id or not title:
        return None

    guid = _string_or_none(episode.get("guid"))
    release_date = _iso_from_timestamp(episode.get("datePublished"))
    duration_seconds = _int_or_none(episode.get("duration"))
    episode_url = _episode_url_from_payload(episode)
    audio_url = _audio_url_from_payload(episode)
    podcast_index_episode_id = episode.get("id")
    podcast_index_feed_id = episode.get("feedId")
    external_ids = {
        "podcast_index_episode_id": podcast_index_episode_id,
        "podcast_index_feed_id": podcast_index_feed_id,
        "rss_guid": guid,
    }
    external_ids = {key: value for key, value in external_ids.items() if value not in (None, "")}
    evidence = {
        "provider": _SOURCE,
        "source_podcast_id": source_podcast_id,
        "feed_id": podcast_index_feed_id,
        "feed_title": episode.get("feedTitle"),
        "episode_url": episode_url,
        "audio_url": audio_url,
    }
    evidence = {key: value for key, value in evidence.items() if value not in (None, "")}

    return PodcastEpisodeRow(
        podcast_id=podcast_id,
        source=_SOURCE,
        source_episode_id=source_episode_id,
        guid=guid,
        title=title,
        description=_string_or_none(episode.get("description")),
        release_date=release_date,
        duration_seconds=duration_seconds,
        episode_url=episode_url,
        audio_url=audio_url,
        external_ids=external_ids,
        evidence=evidence,
        source_payload=episode,
    )


def _upsert_episode(conn: Any, episode: PodcastEpisodeRow) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            _UPSERT_EPISODE_SQL,
            (
                episode.podcast_id,
                episode.source,
                episode.source_episode_id,
                episode.guid,
                episode.title,
                episode.description,
                episode.release_date,
                episode.duration_seconds,
                episode.episode_url,
                episode.audio_url,
                json.dumps(episode.external_ids, sort_keys=True),
                json.dumps(episode.evidence, sort_keys=True),
                json.dumps(episode.source_payload, sort_keys=True),
            ),
        )
        row = cur.fetchone()
        return bool(row and row[0])


def backfill_podcast_episodes(
    *,
    dry_run: bool,
    confirm: bool,
    feed_ids: Optional[list[str]],
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    limit: Optional[int],
    max_episodes_per_feed: int,
    since: Optional[str],
    until: Optional[str],
) -> BackfillSummary:
    if dry_run == confirm:
        raise ValueError("choose exactly one of dry_run or confirm")

    credentials = _load_podcast_index_credentials()
    feeds = load_accepted_feeds(
        feed_ids=feed_ids,
        comedian_ids=comedian_ids,
        comedian_names=comedian_names,
        limit=limit,
    )
    until_ts = _parse_bound_timestamp(until)
    summary = BackfillSummary()
    conn = None if dry_run else get_connection()

    try:
        if conn is not None:
            conn = conn.__enter__()
        for feed in feeds:
            summary.feeds_scanned += 1
            params = _build_fetch_params(
                feed,
                max_episodes_per_feed=max_episodes_per_feed,
                since=since,
            )
            try:
                raw_episodes = fetch_feed_episodes(feed, credentials, params)
            except Exception as exc:
                summary.api_failures += 1
                message = f"feed {feed.source_podcast_id} ({feed.title}): {exc}"
                summary.per_feed_errors.append(message)
                Logger.warn(f"[podcast-index] episode backfill failed for {message}")
                continue

            for raw_episode in raw_episodes:
                if not _episode_matches_until_bound(raw_episode, until_ts):
                    summary.episodes_skipped += 1
                    continue
                episode = episode_from_payload(
                    podcast_id=feed.podcast_id,
                    source_podcast_id=feed.source_podcast_id,
                    episode=raw_episode,
                )
                if episode is None:
                    summary.episodes_skipped += 1
                    continue
                if dry_run:
                    continue
                inserted = _upsert_episode(conn, episode)
                if inserted:
                    summary.episodes_inserted += 1
                else:
                    summary.episodes_updated += 1
        if conn is not None:
            conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.__exit__(None, None, None)

    return summary


def _print_report(summary: BackfillSummary, *, dry_run: bool) -> None:
    prefix = "DRY RUN — " if dry_run else ""
    print(
        f"{prefix}Summary: {summary.feeds_scanned} feeds scanned, "
        f"{summary.episodes_inserted} episodes inserted, "
        f"{summary.episodes_updated} episodes updated, "
        f"{summary.episodes_skipped} episodes skipped, "
        f"{summary.api_failures} API failures"
    )
    for error in summary.per_feed_errors:
        print(f"  error: {error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill canonical podcast episodes for accepted PodcastIndex feeds",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Fetch and report without writing")
    mode.add_argument("--confirm", action="store_true", help="Write podcast_episodes rows")
    parser.add_argument("--feed-id", dest="feed_ids", action="append", default=None)
    parser.add_argument(
        "--comedian-id", dest="comedian_ids", type=int, action="append", default=None
    )
    parser.add_argument("--comedian-name", dest="comedian_names", action="append", default=None)
    parser.add_argument("--limit", type=int, default=None, help="Max accepted feeds to scan")
    parser.add_argument(
        "--max-episodes-per-feed",
        type=int,
        default=_DEFAULT_MAX_EPISODES_PER_FEED,
        help="Max episodes requested from PodcastIndex per feed",
    )
    parser.add_argument("--since", default=None, help="Unix timestamp or ISO date lower bound")
    parser.add_argument(
        "--until", default=None, help="Unix timestamp or ISO date upper bound filtered locally"
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.dry_run == args.confirm:
        parser.error("choose exactly one of --dry-run or --confirm")

    summary = backfill_podcast_episodes(
        dry_run=args.dry_run,
        confirm=args.confirm,
        feed_ids=args.feed_ids,
        comedian_ids=args.comedian_ids,
        comedian_names=args.comedian_names,
        limit=args.limit,
        max_episodes_per_feed=args.max_episodes_per_feed,
        since=args.since,
        until=args.until,
    )
    _print_report(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
