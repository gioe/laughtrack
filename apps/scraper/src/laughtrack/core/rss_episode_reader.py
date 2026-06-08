"""Source-agnostic RSS podcast episode ingestion."""

from __future__ import annotations

import calendar
import json
import re
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

# Episode-number prefix stripped from titles before logical-dup matching.
# Matches "EP67:" / "Episode 67 -" / "#67 " / "67." / "67:" / "67)" patterns
# that publishers swap in and out across feed revisions, causing the same
# logical episode to ingest as multiple rows when sourced via different RSS
# feeds. Two branches: when a marker word (EP/Episode/#) is present, a trailing
# whitespace is sufficient as the boundary; when the prefix is a bare digit,
# require an explicit separator so legitimate titles like "67 Wines" aren't
# stripped. Strips at most one prefix from the start of the title.
_TITLE_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"(?:ep(?:isode)?|#)\s*\d+(?:\s*[:.\-\)\]]|\s+)\s*"
    r"|"
    r"\d+\s*[:.\-\)\]]\s*"
    r")",
    re.IGNORECASE,
)

# Per-feed reachability backoff. A feed that fails to fetch
# UNREACHABLE_FAILURE_THRESHOLD runs in a row is benched (skipped by the load
# query) for UNREACHABLE_COOLDOWN_DAYS, after which it is re-attempted exactly
# once per cooldown window. Any successful fetch (200 or 304) resets the
# counter, so a feed that recovers rejoins the normal rotation immediately and
# is never permanently blacklisted.
UNREACHABLE_FAILURE_THRESHOLD = 3
UNREACHABLE_COOLDOWN_DAYS = 7


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
    WITH input_values AS (
        SELECT
            %s::integer AS podcast_id,
            %s::text AS source,
            %s::text AS source_episode_id,
            %s::text AS guid,
            %s::text AS title,
            %s::text AS description,
            %s::timestamptz AS release_date,
            %s::integer AS duration_seconds,
            %s::text AS episode_url,
            %s::text AS audio_url,
            %s::jsonb AS external_ids,
            %s::jsonb AS evidence,
            %s::jsonb AS source_payload
    ),
    inserted AS (
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
        SELECT
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
        FROM input_values
        ON CONFLICT DO NOTHING
        RETURNING id, true AS inserted, true AS changed
    ),
    target AS (
        SELECT
            podcast_episodes.id,
            (podcast_episodes.source = input_values.source
                AND podcast_episodes.source_episode_id = input_values.source_episode_id) AS same_source
        FROM podcast_episodes
        CROSS JOIN input_values
        WHERE NOT EXISTS (SELECT 1 FROM inserted)
          AND (
            (podcast_episodes.source, podcast_episodes.source_episode_id)
                = (input_values.source, input_values.source_episode_id)
            OR (
                input_values.release_date IS NOT NULL
                AND podcast_episodes.podcast_id = input_values.podcast_id
                AND podcast_episodes.release_date = input_values.release_date
                AND LOWER(REGEXP_REPLACE(BTRIM(podcast_episodes.title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                    = LOWER(REGEXP_REPLACE(BTRIM(input_values.title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
            )
          )
        ORDER BY
            CASE
                WHEN (podcast_episodes.source, podcast_episodes.source_episode_id)
                    = (input_values.source, input_values.source_episode_id)
                THEN 0
                ELSE 1
            END,
            podcast_episodes.id
        LIMIT 1
    ),
    updated AS (
        UPDATE podcast_episodes
        SET podcast_id = input_values.podcast_id,
            guid = COALESCE(input_values.guid, podcast_episodes.guid),
            title = input_values.title,
            description = input_values.description,
            release_date = input_values.release_date,
            duration_seconds = input_values.duration_seconds,
            episode_url = input_values.episode_url,
            audio_url = input_values.audio_url,
            external_ids = input_values.external_ids,
            evidence = input_values.evidence,
            source_payload = input_values.source_payload,
            updated_at = NOW()
        FROM input_values
        WHERE podcast_episodes.id = (SELECT id FROM target WHERE same_source)
          AND (
            podcast_episodes.podcast_id IS DISTINCT FROM input_values.podcast_id
            OR podcast_episodes.guid IS DISTINCT FROM COALESCE(input_values.guid, podcast_episodes.guid)
            OR podcast_episodes.title IS DISTINCT FROM input_values.title
            OR podcast_episodes.description IS DISTINCT FROM input_values.description
            OR podcast_episodes.release_date IS DISTINCT FROM input_values.release_date
            OR podcast_episodes.duration_seconds IS DISTINCT FROM input_values.duration_seconds
            OR podcast_episodes.episode_url IS DISTINCT FROM input_values.episode_url
            OR podcast_episodes.audio_url IS DISTINCT FROM input_values.audio_url
            OR podcast_episodes.external_ids IS DISTINCT FROM input_values.external_ids
            OR podcast_episodes.evidence IS DISTINCT FROM input_values.evidence
            OR podcast_episodes.source_payload IS DISTINCT FROM input_values.source_payload
          )
        RETURNING podcast_episodes.id, false AS inserted, true AS changed
    ),
    unchanged AS (
        SELECT id, false AS inserted, false AS changed
        FROM target
        WHERE NOT EXISTS (SELECT 1 FROM updated)
    )
    SELECT id, inserted, changed FROM inserted
    UNION ALL
    SELECT id, inserted, changed FROM updated
    UNION ALL
    SELECT id, inserted, changed FROM unchanged
    LIMIT 1
"""

_UPDATE_PODCAST_CACHE_SQL = """
    UPDATE podcasts
    SET source_payload = %s::jsonb,
        updated_at = NOW()
    WHERE id = %s
"""

# Logical-dup lookup. The unique constraint on (source, source_episode_id)
# catches re-ingests of the exact same row, but the same logical episode often
# arrives under different (source, source_episode_id) keys when a podcast is
# polled via multiple feeds (e.g. iTunes vs PodcastIndex vs the publisher's
# own RSS). Match by (podcast_id, release_date, normalized title) so feeds
# that stamp batches of distinct episodes with the same timestamp still keep
# separate rows.
_LOOKUP_LOGICAL_BY_RELEASE_DATE_SQL = """
    SELECT id FROM podcast_episodes
    WHERE podcast_id = %s
      AND release_date = %s::timestamptz
      AND LOWER(REGEXP_REPLACE(BTRIM(title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
          = LOWER(REGEXP_REPLACE(BTRIM(%s), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
      AND (source, source_episode_id) IS DISTINCT FROM (%s, %s)
    ORDER BY id
    LIMIT 1
"""

# Fallback for episodes with no release_date — match within podcast on
# title with episode-number prefixes stripped, so "67: Foo" and "Foo" collapse.
_LOOKUP_LOGICAL_BY_NULL_DATE_SQL = """
    SELECT id, title FROM podcast_episodes
    WHERE podcast_id = %s
      AND release_date IS NULL
      AND (source, source_episode_id) IS DISTINCT FROM (%s, %s)
"""

_LOOKUP_BY_SOURCE_EPISODE_ID_SQL = """
    SELECT id FROM podcast_episodes
    WHERE source = %s
      AND source_episode_id = %s
    LIMIT 1
"""


def _normalize_title(title: Optional[str]) -> str:
    """Strip a leading episode-number prefix and lowercase for logical-dup matching."""
    if not title:
        return ""
    return _TITLE_PREFIX_RE.sub("", title.strip(), count=1).strip().lower()


def find_logical_episode_id(conn: Any, episode: "RssEpisodeRow") -> Optional[int]:
    """Return the id of an existing logical-duplicate row, or None.

    A logical duplicate is one already in podcast_episodes for the same
    (podcast_id, release_date, normalized title) under a *different*
    (source, source_episode_id) pair. When release_date is NULL, match instead
    by normalized title within the podcast.

    Imported by backfill_podcast_episodes.py so the RSS-reader and PodcastIndex
    write paths share one definition of "same logical episode".
    """
    if episode.release_date:
        with conn.cursor() as cur:
            cur.execute(
                _LOOKUP_LOGICAL_BY_RELEASE_DATE_SQL,
                (
                    episode.podcast_id,
                    episode.release_date,
                    episode.title,
                    episode.source,
                    episode.source_episode_id,
                ),
            )
            row = cur.fetchone()
        return int(row[0]) if row else None

    normalized = _normalize_title(episode.title)
    if not normalized:
        return None
    with conn.cursor() as cur:
        cur.execute(
            _LOOKUP_LOGICAL_BY_NULL_DATE_SQL,
            (episode.podcast_id, episode.source, episode.source_episode_id),
        )
        rows = cur.fetchall() or []
    for row in rows:
        if _normalize_title(row[1]) == normalized:
            return int(row[0])
    return None


def find_episode_id_by_source(conn: Any, episode: "RssEpisodeRow") -> Optional[int]:
    """Return the row id for an exact source episode key, or None."""
    with conn.cursor() as cur:
        cur.execute(
            _LOOKUP_BY_SOURCE_EPISODE_ID_SQL,
            (episode.source, episode.source_episode_id),
        )
        row = cur.fetchone()
    return int(row[0]) if row else None


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
    # Collapse logical duplicates: same podcast at the same release_date and
    # normalized title but arriving under a different (source, source_episode_id).
    # Lock to first-seen — preserve the existing canonical row's id AND its
    # metadata (title/description/audio_url/etc.). Episode_appearances are
    # FK-bound to podcast_episodes.id, so the id must not change; metadata
    # divergence between feeds is intentionally locked to the first feed that
    # ingested the episode. Same-source re-ingests are excluded from this
    # branch and still flow through the normal ON CONFLICT upsert below, which
    # does refresh metadata.
    existing_id = find_logical_episode_id(conn, episode)
    if existing_id is not None:
        return EpisodeUpsertResult(episode_id=existing_id, inserted=False, changed=False)

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
        # Under READ COMMITTED, INSERT ... ON CONFLICT can wait on a concurrent
        # insert that was not visible to this statement's snapshot. If the
        # conflict path then returns no target row, issue a fresh lookup so the
        # caller still gets the canonical id after the winner commits.
        episode_id = find_episode_id_by_source(conn, episode) or find_logical_episode_id(
            conn,
            episode,
        )
        return EpisodeUpsertResult(episode_id=episode_id, inserted=False, changed=False)
    return EpisodeUpsertResult(episode_id=int(row[0]), inserted=bool(row[1]), changed=True)


def record_fetch_success(conn: Any, podcast: PodcastRssFeed, result: RssFetchResult) -> None:
    """Persist conditional-cache headers and clear any reachability backoff state.

    A successful fetch (HTTP 200 or 304) means the feed is reachable, so we drop
    the consecutive-failure counter and stamp ``last_success_at``. The write is
    skipped entirely when nothing changed, so steady-state feeds without ETags
    do not incur an extra UPDATE per run.
    """
    payload = dict(podcast.source_payload or {})
    cache = dict(payload.get(_CACHE_KEY) or {})

    needs_write = False
    if result.etag and cache.get("etag") != result.etag:
        cache["etag"] = result.etag
        needs_write = True
    if result.last_modified and cache.get("last_modified") != result.last_modified:
        cache["last_modified"] = result.last_modified
        needs_write = True
    if cache.get("consecutive_failures") or cache.get("last_failure_at"):
        cache.pop("consecutive_failures", None)
        cache.pop("last_failure_at", None)
        needs_write = True

    if not needs_write:
        return

    cache["last_success_at"] = datetime.now(timezone.utc).isoformat()
    payload[_CACHE_KEY] = cache
    with conn.cursor() as cur:
        cur.execute(_UPDATE_PODCAST_CACHE_SQL, (json.dumps(payload, sort_keys=True), podcast.podcast_id))


def reachable_feed_clause() -> tuple[str, list[Any]]:
    """SQL boolean (true => feed is reachable / eligible) plus its bind params.

    AND it into a WHERE to skip feeds in reachability cooldown, or negate it to
    count benched feeds. A feed is eligible when it is under the consecutive
    failure threshold OR its cooldown has elapsed (so dead feeds are re-probed
    once per cooldown window and never permanently blacklisted). COALESCE keeps
    the predicate non-NULL for feeds that have never failed. Keeps the
    source_payload cache schema encapsulated in this module.

    Both casts are regex-guarded so a malformed cache value (a non-numeric
    ``consecutive_failures`` or non-ISO ``last_failure_at`` from a manual edit,
    legacy row, or future external writer) cannot raise 22P02/22007 and take
    down the entire load query. We only ever write well-formed values
    (``int()`` / ``datetime.isoformat()``), so the guard is a no-op in steady
    state; when it does trip, the value falls through ``COALESCE`` to the safe
    default (``0`` failures / ``'epoch'``), leaving the one offending feed
    *eligible* (re-probed) rather than crashing the query for every feed.
    """
    # CASE returns NULL when the extracted text fails the regex, so the cast is
    # never attempted on garbage; COALESCE then supplies the fail-safe default.
    clause = (
        "(COALESCE("
        "CASE WHEN (source_payload -> %s ->> 'consecutive_failures') ~ '^[0-9]+$'"
        " THEN (source_payload -> %s ->> 'consecutive_failures')::int END, 0) < %s"
        " OR COALESCE("
        "CASE WHEN (source_payload -> %s ->> 'last_failure_at')"
        " ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}'"
        " THEN (source_payload -> %s ->> 'last_failure_at')::timestamptz END, 'epoch'::timestamptz)"
        " <= NOW() - make_interval(days => %s))"
    )
    params: list[Any] = [
        _CACHE_KEY,
        _CACHE_KEY,
        UNREACHABLE_FAILURE_THRESHOLD,
        _CACHE_KEY,
        _CACHE_KEY,
        UNREACHABLE_COOLDOWN_DAYS,
    ]
    return clause, params


def record_fetch_failure(conn: Any, podcast: PodcastRssFeed) -> int:
    """Increment the feed's consecutive-failure counter and stamp ``last_failure_at``.

    Returns the new consecutive-failure count. Once it reaches
    ``UNREACHABLE_FAILURE_THRESHOLD`` the load query benches the feed for
    ``UNREACHABLE_COOLDOWN_DAYS`` (see ``sync_podcast_episodes_from_rss``).
    """
    payload = dict(podcast.source_payload or {})
    cache = dict(payload.get(_CACHE_KEY) or {})
    failures = int(cache.get("consecutive_failures") or 0) + 1
    cache["consecutive_failures"] = failures
    cache["last_failure_at"] = datetime.now(timezone.utc).isoformat()
    payload[_CACHE_KEY] = cache
    with conn.cursor() as cur:
        cur.execute(_UPDATE_PODCAST_CACHE_SQL, (json.dumps(payload, sort_keys=True), podcast.podcast_id))
    return failures


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
        record_fetch_success(conn, podcast, fetched)

    return summary


def sync_podcast_episodes_from_rss(
    conn: Any,
    podcast: PodcastRssFeed,
    *,
    dry_run: bool,
) -> RssSyncSummary:
    fetched = fetch_rss_episodes(podcast)
    return persist_rss_fetch_result(conn, podcast, fetched, dry_run=dry_run)
