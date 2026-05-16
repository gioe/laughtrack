#!/usr/bin/env python3
"""Discover comedian podcast candidates from Podcast Index feed search."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from curl_cffi.requests import AsyncSession
from dotenv import dotenv_values

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger

_PODCAST_INDEX_SEARCH_URL = "https://api.podcastindex.org/api/1.0/search/byterm"
_SOURCE = "podcast_index"
_DEFAULT_MAX_RESULTS = 10
_DEFAULT_REQUEST_DELAY_S = float(os.environ.get("PODCASTINDEX_REQUEST_DELAY_S", "1.0"))
_MAX_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0
_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PodcastIndexCredentials:
    api_key: str
    api_secret: str
    user_agent: str = "LaughTrack/1.0"


@dataclass(frozen=True)
class PodcastDiscoveryComedian:
    comedian_id: int
    name: str
    aliases: list[str]


@dataclass(frozen=True)
class PodcastCandidate:
    comedian_id: int
    source: str
    source_podcast_id: str
    matched_name: str
    normalized_match: str
    confidence: float
    title: str
    author_name: Optional[str]
    feed_url: Optional[str]
    website_url: Optional[str]
    image_url: Optional[str]
    description: Optional[str]
    evidence: dict[str, Any]


_GET_DISCOVERY_COMEDIANS_SQL = """
    SELECT
        c.id,
        c.name,
        COALESCE(
            array_remove(array_agg(a.name ORDER BY a.name), NULL),
            ARRAY[]::text[]
        ) AS aliases
    FROM comedians c
    LEFT JOIN comedians a ON a.parent_comedian_id = c.id
        AND NULLIF(BTRIM(a.name), '') IS NOT NULL
    WHERE c.parent_comedian_id IS NULL
      AND NULLIF(BTRIM(c.name), '') IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM comedian_deny_list d
          WHERE LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))
      )
      {extra_filter}
    GROUP BY c.id, c.name
    ORDER BY c.popularity DESC NULLS LAST, c.total_shows DESC NULLS LAST, c.id
"""

_UPSERT_PODCAST_SQL = """
    INSERT INTO podcasts (
        source,
        source_podcast_id,
        slug,
        feed_url,
        title,
        author_name,
        website_url,
        image_url,
        description,
        evidence,
        source_payload,
        last_synced_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW())
    ON CONFLICT (source, source_podcast_id) DO UPDATE SET
        feed_url = EXCLUDED.feed_url,
        title = EXCLUDED.title,
        author_name = EXCLUDED.author_name,
        website_url = EXCLUDED.website_url,
        image_url = EXCLUDED.image_url,
        description = EXCLUDED.description,
        evidence = EXCLUDED.evidence,
        source_payload = EXCLUDED.source_payload,
        last_synced_at = NOW(),
        updated_at = NOW()
    RETURNING id
"""

_UPSERT_REVIEW_SQL = """
    INSERT INTO podcast_candidate_reviews (
        comedian_id,
        podcast_id,
        source,
        source_podcast_id,
        candidate_status,
        association_type,
        confidence,
        evidence
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (comedian_id, source, source_podcast_id) DO UPDATE SET
        podcast_id = EXCLUDED.podcast_id,
        association_type = EXCLUDED.association_type,
        confidence = EXCLUDED.confidence,
        evidence = EXCLUDED.evidence,
        updated_at = NOW()
"""

_FALSE_POSITIVE_TITLE_RE = re.compile(
    r"\b(best|top|roundup|calendar|tickets?|shows?|events?|open mic|stand[- ]?up)\b",
    re.IGNORECASE,
)


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
            "Error: set PODCASTINDEX_API_KEY and PODCASTINDEX_API_SECRET before running this script.",
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


def normalize_match_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    normalized = unicodedata.normalize("NFKD", unescaped).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"(?i)\b([a-z0-9]+)'s\b", r"\1", normalized)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def build_podcast_slug(title: str, source_podcast_id: str) -> str:
    raw = f"{title or 'podcast'} {source_podcast_id or ''}"
    normalized = unicodedata.normalize("NFKD", html.unescape(raw))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "podcast"


def build_search_terms(comedian: PodcastDiscoveryComedian) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in [comedian.name, *comedian.aliases]:
        cleaned = str(term or "").strip()
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        terms.append(cleaned)
    return terms


def _source_podcast_id(feed: dict[str, Any]) -> Optional[str]:
    feed_id = feed.get("id")
    if feed_id not in (None, ""):
        return str(feed_id)
    feed_url = feed.get("url")
    if isinstance(feed_url, str) and feed_url:
        return f"feed_url:{hashlib.sha1(feed_url.encode('utf-8')).hexdigest()}"
    return None


def _string_or_none(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _score_feed(
    comedian: PodcastDiscoveryComedian,
    feed: dict[str, Any],
    search_term: str,
) -> tuple[float, str, str]:
    title = normalize_match_text(str(feed.get("title") or ""))
    author = normalize_match_text(str(feed.get("author") or feed.get("ownerName") or ""))
    description = normalize_match_text(str(feed.get("description") or ""))
    canonical = normalize_match_text(comedian.name)
    search = normalize_match_text(search_term)
    alias_terms = {normalize_match_text(alias) for alias in comedian.aliases if normalize_match_text(alias)}

    if title == canonical:
        return 0.99, "title_exact", "title"
    if author == canonical:
        return 0.97, "author_exact", "author"
    if search in alias_terms and (title == search or title.startswith(f"{search} podcast")):
        return 0.94, "alias_title_exact", "title"
    if search and search in title:
        return 0.86, "title_contains", "title"
    if search and search in author:
        return 0.82, "author_contains", "author"
    if search and search in description:
        return 0.48, "description_contains", "description"
    if _FALSE_POSITIVE_TITLE_RE.search(str(feed.get("title") or "")):
        return 0.12, "false_positive_pattern", "title"
    return 0.22, "weak_search_result", "search_result"


def candidate_from_feed(
    comedian: PodcastDiscoveryComedian,
    feed: dict[str, Any],
    search_term: str,
    rank: int,
) -> Optional[PodcastCandidate]:
    source_podcast_id = _source_podcast_id(feed)
    title = _string_or_none(feed.get("title"))
    if not source_podcast_id or not title:
        return None

    author = _string_or_none(feed.get("author") or feed.get("ownerName"))
    feed_url = _string_or_none(feed.get("url"))
    website_url = _string_or_none(feed.get("link"))
    image_url = _string_or_none(feed.get("image") or feed.get("artwork"))
    description = _string_or_none(feed.get("description"))
    confidence, band, match_field = _score_feed(comedian, feed, search_term)
    normalized_match = normalize_match_text(search_term)
    evidence = {
        "search_term": search_term,
        "matched_name": search_term,
        "normalized_match": normalized_match,
        "rank": rank,
        "confidence_band": band,
        "match_field": match_field,
        "source_fields": {
            "podcast_index_feed_id": feed.get("id"),
            "title": title,
            "author": author,
            "owner_name": feed.get("ownerName"),
            "feed_url": feed_url,
            "website_url": website_url,
            "image_url": image_url,
            "description": description,
        },
    }
    return PodcastCandidate(
        comedian_id=comedian.comedian_id,
        source=_SOURCE,
        source_podcast_id=source_podcast_id,
        matched_name=search_term,
        normalized_match=normalized_match,
        confidence=confidence,
        title=title,
        author_name=author,
        feed_url=feed_url,
        website_url=website_url,
        image_url=image_url,
        description=description,
        evidence=evidence,
    )


def parse_search_payload(
    comedian: PodcastDiscoveryComedian,
    search_term: str,
    payload: dict[str, Any],
) -> list[PodcastCandidate]:
    feeds = payload.get("feeds") or []
    if not isinstance(feeds, list):
        return []
    candidates: list[PodcastCandidate] = []
    for rank, feed in enumerate(feeds, start=1):
        if not isinstance(feed, dict):
            continue
        candidate = candidate_from_feed(comedian, feed, search_term, rank)
        if candidate:
            candidates.append(candidate)
    return candidates


def load_target_comedians(
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    limit: Optional[int],
) -> list[PodcastDiscoveryComedian]:
    filters: list[str] = []
    params: list[Any] = []
    if comedian_ids:
        filters.append("AND c.id = ANY(%s::int[])")
        params.append(comedian_ids)
    if comedian_names:
        filters.append("AND c.name = ANY(%s::text[])")
        params.append(comedian_names)

    sql = _GET_DISCOVERY_COMEDIANS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        sql += "\n    LIMIT %s"
        params.append(int(limit))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            return [
                PodcastDiscoveryComedian(int(row[0]), str(row[1]), list(row[2] or []))
                for row in cur.fetchall()
            ]


def _podcast_evidence(candidate: PodcastCandidate) -> dict[str, Any]:
    return {
        "provider": _SOURCE,
        "discovered_by": "discover_comedian_podcast_candidates",
        "matched_name": candidate.matched_name,
        "normalized_match": candidate.normalized_match,
        "confidence": candidate.confidence,
        "confidence_band": candidate.evidence.get("confidence_band"),
    }


def _review_evidence(candidate: PodcastCandidate) -> dict[str, Any]:
    evidence = dict(candidate.evidence)
    evidence["matched_name"] = candidate.matched_name
    evidence["normalized_match"] = candidate.normalized_match
    evidence["confidence"] = candidate.confidence
    return evidence


def persist_candidates(candidates: list[PodcastCandidate], dry_run: bool) -> int:
    if dry_run:
        for candidate in candidates:
            print(
                f"  candidate comedian_id={candidate.comedian_id} podcast={candidate.title!r} "
                f"author={candidate.author_name!r} confidence={candidate.confidence:.2f} "
                f"band={candidate.evidence.get('confidence_band')} feed_id={candidate.source_podcast_id}"
            )
        return len(candidates)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for candidate in candidates:
                cur.execute(
                    _UPSERT_PODCAST_SQL,
                    (
                        candidate.source,
                        candidate.source_podcast_id,
                        build_podcast_slug(candidate.title, candidate.source_podcast_id),
                        candidate.feed_url,
                        candidate.title,
                        candidate.author_name,
                        candidate.website_url,
                        candidate.image_url,
                        candidate.description,
                        json.dumps(_podcast_evidence(candidate), sort_keys=True),
                        json.dumps(candidate.evidence.get("source_fields", {}), sort_keys=True),
                    ),
                )
                podcast_row = cur.fetchone()
                podcast_id = int(podcast_row[0]) if podcast_row else None
                cur.execute(
                    _UPSERT_REVIEW_SQL,
                    (
                        candidate.comedian_id,
                        podcast_id,
                        candidate.source,
                        candidate.source_podcast_id,
                        "pending",
                        "host",
                        candidate.confidence,
                        json.dumps(_review_evidence(candidate), sort_keys=True),
                    ),
                )
        conn.commit()
    return len(candidates)


def _build_search_params(search_term: str, max_results: int) -> dict[str, Any]:
    return {"q": search_term, "max": max_results, "fulltext": ""}


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
    credentials: PodcastIndexCredentials,
    params: dict[str, Any],
    comedian: PodcastDiscoveryComedian,
    search_term: str,
) -> tuple[bool, dict[str, Any]]:
    for attempt in range(_MAX_RETRIES):
        try:
            response = await session.get(
                _PODCAST_INDEX_SEARCH_URL,
                headers=_build_podcast_index_headers(credentials),
                params=params,
                timeout=_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            if attempt + 1 >= _MAX_RETRIES:
                Logger.warn(
                    f"[podcast-index] podcast search failed for comedian {comedian.comedian_id} "
                    f"'{comedian.name}' term '{search_term}': {exc}"
                )
                return False, {}
            await asyncio.sleep(_BASE_RETRY_DELAY_S * (2**attempt))
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt + 1 >= _MAX_RETRIES:
                Logger.warn(
                    f"[podcast-index] HTTP {response.status_code} for comedian {comedian.comedian_id} "
                    f"'{comedian.name}' term '{search_term}' after {_MAX_RETRIES} attempts"
                )
                return False, {}
            await asyncio.sleep(_retry_after_seconds(response.headers, attempt))
            continue
        if response.status_code >= 400:
            Logger.warn(
                f"[podcast-index] HTTP {response.status_code} for comedian {comedian.comedian_id} "
                f"'{comedian.name}' term '{search_term}'"
            )
            return False, {}
        try:
            data = response.json()
        except Exception as exc:
            Logger.warn(
                f"[podcast-index] non-JSON podcast search response for comedian {comedian.comedian_id} "
                f"'{comedian.name}' term '{search_term}': {exc}"
            )
            return False, {}
        if data.get("status") not in (None, True, "true"):
            Logger.warn(
                f"[podcast-index] unsuccessful podcast search for comedian {comedian.comedian_id} "
                f"'{comedian.name}' term '{search_term}': {data}"
            )
            return False, {}
        return True, data
    return False, {}


async def _discover_async(
    comedians: list[PodcastDiscoveryComedian],
    credentials: PodcastIndexCredentials,
    max_results: int,
    request_delay: float,
) -> tuple[list[PodcastCandidate], int]:
    candidates: list[PodcastCandidate] = []
    failed = 0
    async with AsyncSession() as session:
        for comedian_index, comedian in enumerate(comedians, start=1):
            if comedian_index > 1:
                await asyncio.sleep(request_delay)
            seen_feed_ids: set[str] = set()
            for term_index, search_term in enumerate(build_search_terms(comedian), start=1):
                if term_index > 1:
                    await asyncio.sleep(request_delay)
                succeeded, payload = await _fetch_json_with_retries(
                    session=session,
                    credentials=credentials,
                    params=_build_search_params(search_term, max_results),
                    comedian=comedian,
                    search_term=search_term,
                )
                if not succeeded:
                    failed += 1
                    continue
                for candidate in parse_search_payload(comedian, search_term, payload):
                    if candidate.source_podcast_id in seen_feed_ids:
                        continue
                    seen_feed_ids.add(candidate.source_podcast_id)
                    candidates.append(candidate)
    return candidates, failed


def discover_podcast_candidates(
    limit: Optional[int],
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    max_results: int,
    dry_run: bool,
) -> dict[str, int]:
    _load_env_defaults()
    credentials = _load_podcast_index_credentials()
    comedians = load_target_comedians(comedian_ids, comedian_names, limit)
    if not comedians:
        print("No comedians matched.")
        return {"processed": 0, "candidates": 0, "written": 0, "failed": 0}

    candidates, failed = asyncio.run(
        _discover_async(
            comedians=comedians,
            credentials=credentials,
            max_results=max_results,
            request_delay=_DEFAULT_REQUEST_DELAY_S,
        )
    )
    written = persist_candidates(candidates, dry_run=dry_run)
    return {
        "processed": len(comedians),
        "candidates": len(candidates),
        "written": written,
        "failed": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover comedian podcast candidates from Podcast Index feed search",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max canonical comedians to process")
    parser.add_argument("--comedian-ids", type=int, nargs="*", default=None)
    parser.add_argument("--comedian-names", nargs="*", default=None)
    parser.add_argument("--max-results", type=int, default=_DEFAULT_MAX_RESULTS, help="Max feeds per search term")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = discover_podcast_candidates(
        limit=args.limit,
        comedian_ids=args.comedian_ids,
        comedian_names=args.comedian_names,
        max_results=args.max_results,
        dry_run=args.dry_run,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
