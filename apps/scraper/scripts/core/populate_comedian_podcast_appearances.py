#!/usr/bin/env python3
"""Backfill comedian podcast appearances from Podcast Index and RSS feeds.

Setup:
    1. Create a free Podcast Index API account at https://api.podcastindex.org/.
    2. Generate an API key and secret from the Podcast Index developer portal.
    3. Export these variables before running, or add them to apps/scraper/.env:
       PODCASTINDEX_API_KEY=...
       PODCASTINDEX_API_SECRET=...
       PODCASTINDEX_USER_AGENT=LaughTrack/1.0

Usage:
    python -m scripts.core.populate_comedian_podcast_appearances --limit 100 --dry-run
    python -m scripts.core.populate_comedian_podcast_appearances --limit 100
    python -m scripts.core.populate_comedian_podcast_appearances --comedian-ids 12 34
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from curl_cffi.requests import AsyncSession
from dotenv import dotenv_values
from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger

_PODCAST_INDEX_PERSON_SEARCH_URL = "https://api.podcastindex.org/api/1.0/search/byperson"
_SOURCE = "podcast_index"
_DEFAULT_MAX_EPISODES = 25
_DEFAULT_BATCH_SIZE = 10
_DEFAULT_REQUEST_DELAY_S = float(os.environ.get("PODCASTINDEX_REQUEST_DELAY_S", "1.0"))
_DEFAULT_MIN_CONFIDENCE = float(os.environ.get("PODCASTINDEX_MIN_CONFIDENCE", "0.75"))
_MAX_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0
_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PodcastIndexCredentials:
    api_key: str
    api_secret: str
    user_agent: str = "LaughTrack/1.0"


@dataclass(frozen=True)
class RssEpisodeMetadata:
    podcast_name: str
    episode_title: str
    release_date: Optional[str]
    episode_url: str
    guid: Optional[str]
    enclosure_url: Optional[str]


@dataclass(frozen=True)
class PodcastAppearanceRow:
    comedian_id: int
    source: str
    source_episode_id: str
    podcast_name: str
    episode_title: str
    release_date: Optional[str]
    episode_url: str
    match_confidence: float
    match_evidence: dict[str, Any]


@dataclass(frozen=True)
class PodcastIdentityLink:
    comedian_id: int
    source_feed_id: str
    review_status: str


@dataclass(frozen=True)
class PodcastAppearanceFetchResult:
    succeeded: bool
    rows: list[PodcastAppearanceRow]


_GET_COMEDIANS_SQL = """
    SELECT id, name
    FROM comedians
    WHERE parent_comedian_id IS NULL
      AND NULLIF(BTRIM(name), '') IS NOT NULL
      {extra_filter}
    ORDER BY popularity DESC NULLS LAST, total_shows DESC NULLS LAST, id
"""

_INSERT_SQL = """
    INSERT INTO comedian_podcast_appearances (
        comedian_id,
        source,
        source_episode_id,
        podcast_name,
        episode_title,
        release_date,
        episode_url,
        match_confidence,
        match_evidence
    )
    VALUES %s
    ON CONFLICT (comedian_id, source, source_episode_id) DO UPDATE SET
        podcast_name = EXCLUDED.podcast_name,
        episode_title = EXCLUDED.episode_title,
        release_date = EXCLUDED.release_date,
        episode_url = EXCLUDED.episode_url,
        match_confidence = EXCLUDED.match_confidence,
        match_evidence = EXCLUDED.match_evidence,
        updated_at = NOW()
"""

_VALUES_TEMPLATE = "(%s, %s, %s, %s, %s, %s::timestamptz, %s, %s, %s::jsonb)"

_GET_REVIEWED_IDENTITY_LINKS_SQL = """
    SELECT comedian_id, source_feed_id, LOWER(review_status)
    FROM comedian_podcast_identity_links
    WHERE comedian_id = ANY(%s::int[])
      AND source = %s
"""


def _load_env_defaults(path: Path = Path(".env")) -> None:
    for key, value in dotenv_values(path).items():
        if value:
            os.environ.setdefault(key, value)


def _load_podcast_index_credentials() -> PodcastIndexCredentials:
    api_key = os.environ.get("PODCASTINDEX_API_KEY") or os.environ.get("PODCAST_INDEX_API_KEY")
    api_secret = os.environ.get("PODCASTINDEX_API_SECRET") or os.environ.get("PODCAST_INDEX_API_SECRET")
    user_agent = os.environ.get("PODCASTINDEX_USER_AGENT") or os.environ.get(
        "PODCAST_INDEX_USER_AGENT",
        "LaughTrack/1.0",
    )
    if not api_key or not api_secret:
        print(
            "Error: set PODCASTINDEX_API_KEY and PODCASTINDEX_API_SECRET before running this script. "
            "Generate credentials at https://api.podcastindex.org/.",
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


def _build_person_search_params(search_term: str, max_episodes: int = _DEFAULT_MAX_EPISODES) -> dict[str, Any]:
    return {"q": search_term, "max": max_episodes, "fulltext": ""}


def _extract_episode_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items") or []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _normalized_terms(value: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 1]


def _match_evidence(
    comedian_name: str,
    episode_title: str,
    podcast_name: str,
    episode: dict[str, Any],
    metadata_source: str,
) -> dict[str, Any]:
    terms = _normalized_terms(comedian_name)
    haystack = set(_normalized_terms(f"{episode_title} {podcast_name}"))
    matched_terms = [term for term in terms if term in haystack]
    return {
        "search_term": comedian_name,
        "matched_terms": matched_terms,
        "episode_title": episode_title,
        "podcast_name": podcast_name,
        "podcast_index_episode_id": episode.get("id"),
        "podcast_index_guid": episode.get("guid"),
        "source_feed_id": _source_feed_id(episode),
        "source_feed_url": episode.get("feedUrl"),
        "feed_url": episode.get("feedUrl"),
        "metadata_source": metadata_source,
    }


def _match_confidence(evidence: dict[str, Any]) -> float:
    matched_terms = evidence.get("matched_terms")
    search_terms = _normalized_terms(str(evidence.get("search_term") or ""))
    if not isinstance(matched_terms, list) or not search_terms:
        return 0.0
    return round(len(matched_terms) / len(search_terms), 2)


def _iso_from_timestamp(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _iso_from_rss_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children_named(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(node) if _local_name(child.tag) == name]


def _first_child_text(node: ET.Element, name: str) -> Optional[str]:
    for child in _children_named(node, name):
        value = (child.text or "").strip()
        if value:
            return value
    return None


def _parse_rss_metadata(feed_xml: str) -> list[RssEpisodeMetadata]:
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError:
        return []
    channel = next((child for child in root.iter() if _local_name(child.tag) == "channel"), None)
    channel_title = _first_child_text(channel, "title") if channel is not None else None
    episodes: list[RssEpisodeMetadata] = []
    if channel is None:
        return episodes
    for item in _children_named(channel, "item"):
        title = _first_child_text(item, "title")
        link = _first_child_text(item, "link")
        guid = _first_child_text(item, "guid")
        pub_date = _iso_from_rss_date(_first_child_text(item, "pubDate"))
        enclosure = next(iter(_children_named(item, "enclosure")), None)
        enclosure_url = enclosure.attrib.get("url") if enclosure is not None else None
        episode_url = link or enclosure_url
        if not title or not episode_url:
            continue
        episodes.append(
            RssEpisodeMetadata(
                podcast_name=channel_title or "",
                episode_title=title,
                release_date=pub_date,
                episode_url=episode_url,
                guid=guid,
                enclosure_url=enclosure_url,
            )
        )
    return episodes


def _find_rss_match(episode: dict[str, Any], rss_items: list[RssEpisodeMetadata]) -> Optional[RssEpisodeMetadata]:
    guid = str(episode.get("guid") or "")
    link = str(episode.get("link") or "")
    enclosure = str(episode.get("enclosureUrl") or "")
    title_terms = _normalized_terms(str(episode.get("title") or ""))
    for item in rss_items:
        if guid and item.guid == guid:
            return item
        if link and item.episode_url == link:
            return item
        if enclosure and item.enclosure_url == enclosure:
            return item
        if title_terms and _normalized_terms(item.episode_title) == title_terms:
            return item
    return None


def _episode_url_from_index(episode: dict[str, Any]) -> Optional[str]:
    for key in ("link", "enclosureUrl"):
        value = episode.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _source_episode_id(episode: dict[str, Any]) -> Optional[str]:
    episode_id = episode.get("id")
    if episode_id not in (None, ""):
        return str(episode_id)
    guid = episode.get("guid")
    if guid:
        return f"guid:{guid}"
    url = _episode_url_from_index(episode)
    if url:
        return f"url:{hashlib.sha1(url.encode('utf-8')).hexdigest()}"
    return None


def _source_feed_id(episode: dict[str, Any]) -> Optional[str]:
    feed_id = episode.get("feedId")
    if feed_id not in (None, ""):
        return str(feed_id)
    feed_url = episode.get("feedUrl")
    if isinstance(feed_url, str) and feed_url:
        return f"feed_url:{hashlib.sha1(feed_url.encode('utf-8')).hexdigest()}"
    return None


def _parse_candidate_rows(
    comedian_id: int,
    comedian_name: str,
    payload: dict[str, Any],
    rss_by_feed_url: dict[str, str],
) -> list[PodcastAppearanceRow]:
    rows: list[PodcastAppearanceRow] = []
    parsed_rss: dict[str, list[RssEpisodeMetadata]] = {
        feed_url: _parse_rss_metadata(feed_xml)
        for feed_url, feed_xml in rss_by_feed_url.items()
        if feed_xml
    }
    for episode in _extract_episode_items(payload):
        source_episode_id = _source_episode_id(episode)
        if not source_episode_id:
            continue
        feed_url = episode.get("feedUrl")
        rss_match = parsed_rss.get(str(feed_url), [])
        rss_metadata = _find_rss_match(episode, rss_match)
        if rss_metadata:
            podcast_name = rss_metadata.podcast_name or str(episode.get("feedTitle") or "")
            episode_title = rss_metadata.episode_title
            release_date = rss_metadata.release_date or _iso_from_timestamp(episode.get("datePublished"))
            episode_url = rss_metadata.episode_url
            metadata_source = "rss"
        else:
            podcast_name = str(episode.get("feedTitle") or "")
            episode_title = str(episode.get("title") or "")
            release_date = _iso_from_timestamp(episode.get("datePublished"))
            episode_url = _episode_url_from_index(episode)
            metadata_source = "podcast_index"
        if not podcast_name or not episode_title or not episode_url:
            continue
        evidence = _match_evidence(
            comedian_name=comedian_name,
            episode_title=episode_title,
            podcast_name=podcast_name,
            episode=episode,
            metadata_source=metadata_source,
        )
        rows.append(
            PodcastAppearanceRow(
                comedian_id=comedian_id,
                source=_SOURCE,
                source_episode_id=source_episode_id,
                podcast_name=podcast_name,
                episode_title=episode_title,
                release_date=release_date,
                episode_url=episode_url,
                match_confidence=_match_confidence(evidence),
                match_evidence=evidence,
            )
        )
    return rows


def _retry_after_seconds(headers: dict[str, str] | None, attempt: int) -> float:
    retry_after = (headers or {}).get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    return _BASE_RETRY_DELAY_S * (2**attempt)


async def _fetch_json_with_retries(
    session: AsyncSession,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    comedian_id: int,
    comedian_name: str,
) -> tuple[bool, dict[str, Any]]:
    for attempt in range(_MAX_RETRIES):
        try:
            response = await session.get(url, headers=headers, params=params, timeout=_TIMEOUT_SECONDS)
        except Exception as exc:
            if attempt + 1 >= _MAX_RETRIES:
                Logger.warn(
                    f"[podcast-index] fetch failed for comedian {comedian_id} '{comedian_name}': {exc}"
                )
                return False, {}
            await asyncio.sleep(_BASE_RETRY_DELAY_S * (2**attempt))
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt + 1 >= _MAX_RETRIES:
                Logger.warn(
                    f"[podcast-index] HTTP {response.status_code} for comedian {comedian_id} '{comedian_name}' after {_MAX_RETRIES} attempts"
                )
                return False, {}
            delay = _retry_after_seconds(response.headers, attempt)
            Logger.warn(
                f"[podcast-index] HTTP {response.status_code} for comedian {comedian_id} '{comedian_name}' retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            continue

        if response.status_code >= 400:
            Logger.warn(
                f"[podcast-index] HTTP {response.status_code} for comedian {comedian_id} '{comedian_name}'"
            )
            return False, {}

        try:
            data = response.json()
        except Exception as exc:
            Logger.warn(
                f"[podcast-index] non-JSON response for comedian {comedian_id} '{comedian_name}': {exc}"
            )
            return False, {}

        if data.get("status") not in (None, True, "true"):
            Logger.warn(
                f"[podcast-index] unsuccessful response for comedian {comedian_id} '{comedian_name}': {data}"
            )
            return False, {}
        return True, data

    return False, {}


async def _fetch_rss_feed(session: AsyncSession, feed_url: str) -> Optional[str]:
    try:
        response = await session.get(feed_url, timeout=_TIMEOUT_SECONDS)
    except Exception as exc:
        Logger.warn(f"[podcast-index] RSS fetch failed for {feed_url}: {exc}")
        return None
    if response.status_code >= 400:
        Logger.warn(f"[podcast-index] RSS HTTP {response.status_code} for {feed_url}")
        return None
    return response.text


def _rss_feed_urls(payload: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for episode in _extract_episode_items(payload):
        feed_url = episode.get("feedUrl")
        if not isinstance(feed_url, str) or not feed_url.startswith(("http://", "https://")):
            continue
        parsed = urlparse(feed_url)
        if not parsed.netloc:
            continue
        if feed_url not in seen:
            seen.add(feed_url)
            urls.append(feed_url)
    return urls


async def _fetch_podcast_index_episode_result(
    session: AsyncSession,
    comedian_id: int,
    comedian_name: str,
    credentials: PodcastIndexCredentials,
    max_episodes: int = _DEFAULT_MAX_EPISODES,
) -> PodcastAppearanceFetchResult:
    succeeded, data = await _fetch_json_with_retries(
        session=session,
        url=_PODCAST_INDEX_PERSON_SEARCH_URL,
        headers=_build_podcast_index_headers(credentials),
        params=_build_person_search_params(comedian_name, max_episodes=max_episodes),
        comedian_id=comedian_id,
        comedian_name=comedian_name,
    )
    if not succeeded:
        return PodcastAppearanceFetchResult(succeeded=False, rows=[])

    rss_by_feed_url: dict[str, str] = {}
    for feed_url in _rss_feed_urls(data):
        rss = await _fetch_rss_feed(session, feed_url)
        if rss:
            rss_by_feed_url[feed_url] = rss

    return PodcastAppearanceFetchResult(
        succeeded=True,
        rows=_parse_candidate_rows(
            comedian_id=comedian_id,
            comedian_name=comedian_name,
            payload=data,
            rss_by_feed_url=rss_by_feed_url,
        ),
    )


def _load_target_comedians(
    comedian_ids: Optional[list[int]],
    comedian_name: Optional[str],
    limit: Optional[int],
) -> list[tuple[int, str]]:
    filters: list[str] = []
    params: list[Any] = []
    if comedian_ids:
        filters.append("AND id = ANY(%s::int[])")
        params.append(comedian_ids)
    if comedian_name:
        filters.append("AND name ILIKE %s")
        params.append(comedian_name)

    sql = _GET_COMEDIANS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        sql += f"\n    LIMIT {int(limit)}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            return [(row[0], row[1]) for row in cur.fetchall()]


def _row_values(rows: Iterable[PodcastAppearanceRow]) -> list[tuple[Any, ...]]:
    return [
        (
            row.comedian_id,
            row.source,
            row.source_episode_id,
            row.podcast_name,
            row.episode_title,
            row.release_date,
            row.episode_url,
            row.match_confidence,
            json.dumps(row.match_evidence, sort_keys=True),
        )
        for row in rows
    ]


def _replace_appearances(conn: Any, comedian_ids: list[int], rows: list[PodcastAppearanceRow]) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM comedian_podcast_appearances
            WHERE comedian_id = ANY(%s::int[])
              AND source = %s
            """,
            (comedian_ids, _SOURCE),
        )
        values = _row_values(rows)
        if values:
            execute_values(cur, _INSERT_SQL, values, template=_VALUES_TEMPLATE)
    return len(rows)


def _load_reviewed_identity_links(comedian_ids: list[int]) -> dict[tuple[int, str], PodcastIdentityLink]:
    if not comedian_ids:
        return {}
    links: dict[tuple[int, str], PodcastIdentityLink] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_GET_REVIEWED_IDENTITY_LINKS_SQL, (comedian_ids, _SOURCE))
            for comedian_id, source_feed_id, review_status in cur.fetchall():
                if review_status in {"verified", "ambiguous", "rejected"}:
                    link = PodcastIdentityLink(
                        comedian_id=int(comedian_id),
                        source_feed_id=str(source_feed_id),
                        review_status=str(review_status),
                    )
                    links[(link.comedian_id, link.source_feed_id)] = link
    return links


def _append_audit_rows(path: Path, rows: list[PodcastAppearanceRow]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _split_by_reviewed_identity_links(
    rows: list[PodcastAppearanceRow],
    min_confidence: float,
    identity_links: dict[tuple[int, str], PodcastIdentityLink],
) -> tuple[list[PodcastAppearanceRow], list[PodcastAppearanceRow], list[PodcastAppearanceRow]]:
    confirmed: list[PodcastAppearanceRow] = []
    audit: list[PodcastAppearanceRow] = []
    suppressed: list[PodcastAppearanceRow] = []
    for row in rows:
        source_feed_id = row.match_evidence.get("source_feed_id")
        link = (
            identity_links.get((row.comedian_id, str(source_feed_id)))
            if isinstance(source_feed_id, str) and source_feed_id
            else None
        )
        if link and link.review_status == "rejected":
            suppressed.append(row)
        elif link and link.review_status == "verified":
            confirmed.append(row)
        elif row.match_confidence >= min_confidence:
            confirmed.append(row)
        else:
            audit.append(row)
    return confirmed, audit, suppressed


async def _populate(
    comedians: list[tuple[int, str]],
    credentials: PodcastIndexCredentials,
    max_episodes: int,
    dry_run: bool,
    batch_size: int,
    request_delay: float,
    audit_path: Path,
    min_confidence: float,
    identity_links: Optional[dict[tuple[int, str], PodcastIdentityLink]] = None,
) -> dict[str, int]:
    all_confirmed_rows: list[PodcastAppearanceRow] = []
    audit_rows: list[PodcastAppearanceRow] = []
    suppressed_rows: list[PodcastAppearanceRow] = []
    processed_ids: list[int] = []
    failed = 0
    reviewed_identity_links = identity_links if identity_links is not None else {}

    async with AsyncSession() as session:
        for index, (comedian_id, name) in enumerate(comedians, start=1):
            if index > 1:
                if batch_size > 0 and (index - 1) % batch_size == 0:
                    print(f"Processed {index - 1} comedian(s); continuing next conservative batch")
                await asyncio.sleep(request_delay)
            result = await _fetch_podcast_index_episode_result(
                session=session,
                comedian_id=comedian_id,
                comedian_name=name,
                credentials=credentials,
                max_episodes=max_episodes,
            )
            if not result.succeeded:
                failed += 1
                print(f"{name}: lookup failed; preserving existing {_SOURCE} rows")
                continue
            confirmed, low_confidence, suppressed = _split_by_reviewed_identity_links(
                result.rows,
                min_confidence=min_confidence,
                identity_links=reviewed_identity_links,
            )
            processed_ids.append(comedian_id)
            all_confirmed_rows.extend(confirmed)
            audit_rows.extend(low_confidence)
            suppressed_rows.extend(suppressed)
            print(
                f"{name}: {len(result.rows)} candidate episode(s), "
                f"{len(confirmed)} confirmed, {len(low_confidence)} audit, "
                f"{len(suppressed)} suppressed"
            )

    if dry_run:
        for row in all_confirmed_rows + audit_rows + suppressed_rows:
            if row in suppressed_rows:
                disposition = "suppressed"
            elif row.match_confidence >= min_confidence:
                disposition = "confirmed"
            else:
                disposition = "audit"
            print(
                f"  {disposition} comedian_id={row.comedian_id} podcast={row.podcast_name!r} "
                f"title={row.episode_title!r} confidence={row.match_confidence:.2f} "
                f"source={row.match_evidence.get('metadata_source')} url={row.episode_url}"
            )
        written = 0
    else:
        if processed_ids:
            with get_connection() as conn:
                written = _replace_appearances(conn, processed_ids, all_confirmed_rows)
                conn.commit()
        else:
            written = 0
        _append_audit_rows(audit_path, audit_rows)

    return {
        "processed": len(comedians),
        "failed": failed,
        "matched_episodes": len(all_confirmed_rows) + len(audit_rows) + len(suppressed_rows),
        "written": written,
        "audit_rows": len(audit_rows),
        "suppressed_rows": len(suppressed_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate comedian podcast appearances from Podcast Index person search and RSS feeds",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max comedians to process")
    parser.add_argument("--comedian-ids", type=int, nargs="*", default=None)
    parser.add_argument("--comedian-name", default=None, help="Case-insensitive exact SQL pattern")
    parser.add_argument("--max-episodes", type=int, default=_DEFAULT_MAX_EPISODES, help="Max episodes per person search")
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE, help="Progress batch size")
    parser.add_argument("--request-delay", type=float, default=_DEFAULT_REQUEST_DELAY_S, help="Delay between comedians")
    parser.add_argument(
        "--audit-path",
        type=Path,
        default=Path("tmp/podcast_index_low_confidence.jsonl"),
        help="JSONL path for low-confidence matches in production mode",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=_DEFAULT_MIN_CONFIDENCE,
        help="Minimum token-match confidence for confirmed rows",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _load_env_defaults()
    credentials = _load_podcast_index_credentials()
    comedians = _load_target_comedians(args.comedian_ids, args.comedian_name, args.limit)
    if not comedians:
        print("No comedians matched.")
        return
    identity_links = _load_reviewed_identity_links([comedian_id for comedian_id, _ in comedians])

    print(f"Processing {len(comedians)} comedian(s)")
    summary = asyncio.run(
        _populate(
            comedians=comedians,
            credentials=credentials,
            max_episodes=args.max_episodes,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            request_delay=args.request_delay,
            audit_path=args.audit_path,
            min_confidence=args.min_confidence,
            identity_links=identity_links,
        )
    )
    print(summary)


if __name__ == "__main__":
    main()
