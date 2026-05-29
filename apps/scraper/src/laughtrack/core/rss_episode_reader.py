"""Source-agnostic RSS podcast episode ingestion."""

from __future__ import annotations

import calendar
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import feedparser
from curl_cffi import requests

_TIMEOUT_SECONDS = 30
_MAX_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0
_CACHE_KEY = "rss_episode_reader"


@dataclass(frozen=True)
class PodcastRssFeed:
    podcast_id: int
    source: str
    source_podcast_id: str
    feed_url: Optional[str]
    title: str
    source_payload: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class RssEpisodeRow:
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


@dataclass(frozen=True)
class RssFetchResult:
    episodes: list[RssEpisodeRow] = field(default_factory=list)
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    not_modified: bool = False


@dataclass(frozen=True)
class EpisodeUpsertResult:
    episode_id: Optional[int]
    inserted: bool
    changed: bool


@dataclass
class RssSyncSummary:
    episodes_seen: int = 0
    episodes_inserted: int = 0
    episodes_updated: int = 0
    episodes_unchanged: int = 0
    episodes_skipped: int = 0
    not_modified: bool = False


class RssFeedParseError(RuntimeError):
    """Raised when a feed cannot be parsed as usable RSS/Atom."""


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
    WHERE podcast_episodes.podcast_id IS DISTINCT FROM EXCLUDED.podcast_id
       OR podcast_episodes.guid IS DISTINCT FROM COALESCE(EXCLUDED.guid, podcast_episodes.guid)
       OR podcast_episodes.title IS DISTINCT FROM EXCLUDED.title
       OR podcast_episodes.description IS DISTINCT FROM EXCLUDED.description
       OR podcast_episodes.release_date IS DISTINCT FROM EXCLUDED.release_date
       OR podcast_episodes.duration_seconds IS DISTINCT FROM EXCLUDED.duration_seconds
       OR podcast_episodes.episode_url IS DISTINCT FROM EXCLUDED.episode_url
       OR podcast_episodes.audio_url IS DISTINCT FROM EXCLUDED.audio_url
       OR podcast_episodes.external_ids IS DISTINCT FROM EXCLUDED.external_ids
       OR podcast_episodes.evidence IS DISTINCT FROM EXCLUDED.evidence
       OR podcast_episodes.source_payload IS DISTINCT FROM EXCLUDED.source_payload
    RETURNING id, (xmax = 0) AS inserted
"""

_UPDATE_PODCAST_CACHE_SQL = """
    UPDATE podcasts
    SET source_payload = %s::jsonb,
        updated_at = NOW()
    WHERE id = %s
"""


def _string_or_none(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _cache_payload(podcast: PodcastRssFeed) -> dict[str, Any]:
    payload = dict(podcast.source_payload or {})
    cached = payload.get(_CACHE_KEY)
    return cached if isinstance(cached, dict) else {}


def _conditional_headers(podcast: PodcastRssFeed) -> dict[str, str]:
    cache = _cache_payload(podcast)
    headers = {"User-Agent": "LaughTrack/1.0", "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"}
    etag = _string_or_none(cache.get("etag"))
    last_modified = _string_or_none(cache.get("last_modified"))
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def _retry_after_seconds(headers: dict[str, str] | None, attempt: int) -> float:
    retry_after = (headers or {}).get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    return _BASE_RETRY_DELAY_S * (2**attempt)


def _fetch_feed(podcast: PodcastRssFeed) -> Any:
    if not podcast.feed_url:
        raise RuntimeError(f"podcast {podcast.podcast_id} has no feed_url")
    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.get(
                podcast.feed_url,
                headers=_conditional_headers(podcast),
                timeout=_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            if attempt + 1 >= _MAX_RETRIES:
                raise RuntimeError(f"fetch failed for podcast {podcast.podcast_id}: {exc}") from exc
            time.sleep(_BASE_RETRY_DELAY_S * (2**attempt))
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt + 1 >= _MAX_RETRIES:
                raise RuntimeError(
                    f"HTTP {response.status_code} for podcast {podcast.podcast_id} after {_MAX_RETRIES} attempts"
                )
            time.sleep(_retry_after_seconds(response.headers, attempt))
            continue
        if response.status_code >= 400 and response.status_code != 304:
            raise RuntimeError(f"HTTP {response.status_code} for podcast {podcast.podcast_id}")
        return response
    raise RuntimeError(f"fetch failed for podcast {podcast.podcast_id}")


def _iso_from_struct_time(value: Any) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _duration_seconds(value: Any) -> Optional[int]:
    raw = _string_or_none(value)
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    parts = raw.split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _json_safe(value: Any) -> dict[str, Any]:
    return json.loads(json.dumps(value, default=str))


def _audio_url(entry: Any) -> Optional[str]:
    for enclosure in entry.get("enclosures") or []:
        if isinstance(enclosure, dict):
            value = _string_or_none(enclosure.get("href") or enclosure.get("url"))
            if value and value.startswith(("http://", "https://")):
                return value
    return None


def _episode_from_entry(podcast: PodcastRssFeed, entry: Any) -> Optional[RssEpisodeRow]:
    guid = _string_or_none(entry.get("id") or entry.get("guid"))
    title = _string_or_none(entry.get("title"))
    if not guid or not title:
        return None

    episode_url = _string_or_none(entry.get("link"))
    audio_url = _audio_url(entry)
    external_ids = {"rss_guid": guid}
    evidence = {
        "provider": "rss",
        "source_podcast_id": podcast.source_podcast_id,
        "feed_url": podcast.feed_url,
        "episode_url": episode_url,
        "audio_url": audio_url,
    }
    evidence = {key: value for key, value in evidence.items() if value not in (None, "")}

    return RssEpisodeRow(
        podcast_id=podcast.podcast_id,
        source=podcast.source,
        source_episode_id=guid,
        guid=guid,
        title=title,
        description=_string_or_none(entry.get("summary") or entry.get("description")),
        release_date=_iso_from_struct_time(entry.get("published_parsed") or entry.get("updated_parsed")),
        duration_seconds=_duration_seconds(entry.get("itunes_duration")),
        episode_url=episode_url,
        audio_url=audio_url,
        external_ids=external_ids,
        evidence=evidence,
        source_payload=_json_safe(entry),
    )


def fetch_rss_episodes(podcast: PodcastRssFeed) -> RssFetchResult:
    response = _fetch_feed(podcast)
    etag = _string_or_none(response.headers.get("ETag") or response.headers.get("etag"))
    last_modified = _string_or_none(response.headers.get("Last-Modified") or response.headers.get("last-modified"))
    if response.status_code == 304:
        return RssFetchResult(etag=etag, last_modified=last_modified, not_modified=True)

    parsed = feedparser.parse(response.content)
    if parsed.get("bozo") and not parsed.get("entries"):
        raise RssFeedParseError(f"malformed RSS feed for podcast {podcast.podcast_id}: {parsed.get('bozo_exception')}")
    entries = parsed.get("entries") or []
    if not entries and not parsed.get("feed"):
        raise RssFeedParseError(f"malformed RSS feed for podcast {podcast.podcast_id}: no feed metadata")

    episodes = [episode for entry in entries if (episode := _episode_from_entry(podcast, entry)) is not None]
    return RssFetchResult(episodes=episodes, etag=etag, last_modified=last_modified, not_modified=False)


def upsert_episode_with_result(conn: Any, episode: RssEpisodeRow) -> EpisodeUpsertResult:
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
    if not row:
        return EpisodeUpsertResult(episode_id=None, inserted=False, changed=False)
    return EpisodeUpsertResult(episode_id=int(row[0]), inserted=bool(row[1]), changed=True)


def _update_podcast_cache(conn: Any, podcast: PodcastRssFeed, result: RssFetchResult) -> None:
    if not result.etag and not result.last_modified:
        return
    payload = dict(podcast.source_payload or {})
    cache = dict(payload.get(_CACHE_KEY) or {})
    if result.etag:
        cache["etag"] = result.etag
    if result.last_modified:
        cache["last_modified"] = result.last_modified
    payload[_CACHE_KEY] = cache
    with conn.cursor() as cur:
        cur.execute(_UPDATE_PODCAST_CACHE_SQL, (json.dumps(payload, sort_keys=True), podcast.podcast_id))


def persist_rss_fetch_result(
    conn: Any,
    podcast: PodcastRssFeed,
    fetched: RssFetchResult,
    *,
    dry_run: bool,
) -> RssSyncSummary:
    summary = RssSyncSummary(episodes_seen=len(fetched.episodes), not_modified=fetched.not_modified)
    seen_episode_ids: set[tuple[str, str]] = set()

    for episode in fetched.episodes:
        key = (episode.source, episode.source_episode_id)
        if key in seen_episode_ids:
            summary.episodes_skipped += 1
            continue
        seen_episode_ids.add(key)
        if dry_run:
            continue
        result = upsert_episode_with_result(conn, episode)
        if result.inserted:
            summary.episodes_inserted += 1
        elif result.changed:
            summary.episodes_updated += 1
        else:
            summary.episodes_unchanged += 1

    if not dry_run:
        _update_podcast_cache(conn, podcast, fetched)

    return summary


def sync_podcast_episodes_from_rss(
    conn: Any,
    podcast: PodcastRssFeed,
    *,
    dry_run: bool,
) -> RssSyncSummary:
    fetched = fetch_rss_episodes(podcast)
    return persist_rss_fetch_result(conn, podcast, fetched, dry_run=dry_run)
