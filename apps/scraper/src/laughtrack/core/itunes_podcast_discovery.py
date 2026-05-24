"""Reusable iTunes podcast search and candidate persistence helpers."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Optional

from curl_cffi import requests

from laughtrack.foundation.infrastructure.logger.logger import Logger

_SOURCE = "itunes"
_ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
_ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"
_DEFAULT_MAX_RESULTS = 10
_DEFAULT_REQUEST_DELAY_S = 0.25
_MAX_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0
_TIMEOUT_SECONDS = 30

_FALSE_POSITIVE_TITLE_RE = re.compile(
    r"\b(best|top|roundup|calendar|tickets?|shows?|events?|open mic|stand[- ]?up)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PodcastDiscoveryComedian:
    comedian_id: int
    name: str
    aliases: list[str]


@dataclass(frozen=True)
class ItunesPodcastCandidate:
    comedian_id: int
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

    @property
    def source(self) -> str:
        return _SOURCE


@dataclass(frozen=True)
class UpsertResult:
    podcast_id: int
    action: str


_FIND_PODCAST_BY_FEED_URL_SQL = """
    SELECT id, external_ids
    FROM podcasts
    WHERE feed_url = %s
    ORDER BY
        CASE WHEN source = %s AND source_podcast_id = %s THEN 0 ELSE 1 END,
        id
    LIMIT 1
"""

_INSERT_OR_UPDATE_ITUNES_PODCAST_SQL = """
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
        external_ids,
        evidence,
        source_payload,
        last_synced_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, NOW())
    ON CONFLICT (source, source_podcast_id) DO UPDATE SET
        feed_url = EXCLUDED.feed_url,
        title = EXCLUDED.title,
        author_name = EXCLUDED.author_name,
        website_url = EXCLUDED.website_url,
        image_url = EXCLUDED.image_url,
        description = EXCLUDED.description,
        external_ids = podcasts.external_ids || EXCLUDED.external_ids,
        evidence = EXCLUDED.evidence,
        source_payload = EXCLUDED.source_payload,
        last_synced_at = NOW(),
        updated_at = NOW()
    RETURNING id
"""

_MERGE_ITUNES_ID_BY_FEED_URL_SQL = """
    UPDATE podcasts
    SET external_ids = %s::jsonb,
        updated_at = NOW()
    WHERE id = %s
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

_GET_ACTIVE_DENY_LIST_SQL = """
    SELECT source, source_podcast_id, feed_url
    FROM podcast_deny_list
    WHERE restored_at IS NULL
"""


def normalize_match_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    normalized = unicodedata.normalize("NFKD", unescaped).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"(?i)\b([a-z0-9]+)'s\b", r"\1", normalized)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def build_podcast_slug(title: str, source: str, source_podcast_id: str) -> str:
    raw = f"{title or 'podcast'} {source or ''} {source_podcast_id or ''}"
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


def _string_or_none(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _retry_after_seconds(headers: dict[str, str] | None, attempt: int) -> float:
    retry_after = (headers or {}).get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    return _BASE_RETRY_DELAY_S * (2**attempt)


def _request_json_with_retries(
    url: str,
    *,
    params: dict[str, Any],
    session: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    client = session or requests
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.get(url, params=params, timeout=_TIMEOUT_SECONDS)
        except Exception as exc:
            if attempt + 1 >= _MAX_RETRIES:
                raise RuntimeError(f"iTunes request failed for {url}: {exc}") from exc
            sleep(_BASE_RETRY_DELAY_S * (2**attempt))
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt + 1 >= _MAX_RETRIES:
                raise RuntimeError(f"iTunes HTTP {response.status_code} for {url} after {_MAX_RETRIES} attempts")
            sleep(_retry_after_seconds(response.headers, attempt))
            continue
        if response.status_code >= 400:
            raise RuntimeError(f"iTunes HTTP {response.status_code} for {url}")
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"iTunes returned non-JSON response for {url}: {exc}") from exc
    return {}


def search_itunes_podcasts(
    term: str,
    *,
    limit: int = _DEFAULT_MAX_RESULTS,
    country: str = "US",
    session: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    payload = _request_json_with_retries(
        _ITUNES_SEARCH_URL,
        params={
            "media": "podcast",
            "entity": "podcast",
            "term": term,
            "limit": limit,
            "country": country,
        },
        session=session,
        sleep=sleep,
    )
    results = payload.get("results") or []
    return [result for result in results if isinstance(result, dict)]


def lookup_itunes_podcast(
    collection_id: str,
    *,
    session: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[dict[str, Any]]:
    payload = _request_json_with_retries(
        _ITUNES_LOOKUP_URL,
        params={"id": collection_id, "entity": "podcast"},
        session=session,
        sleep=sleep,
    )
    results = payload.get("results") or []
    for result in results:
        if isinstance(result, dict):
            return result
    return None


def _score_result(
    comedian: PodcastDiscoveryComedian,
    result: dict[str, Any],
    search_term: str,
) -> tuple[float, str, str]:
    title = normalize_match_text(str(result.get("collectionName") or ""))
    author = normalize_match_text(str(result.get("artistName") or ""))
    description = normalize_match_text(str(result.get("description") or ""))
    canonical = normalize_match_text(comedian.name)
    search = normalize_match_text(search_term)
    alias_terms = {normalize_match_text(alias) for alias in comedian.aliases if normalize_match_text(alias)}

    if title == canonical or title == f"{canonical} podcast":
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
    if _FALSE_POSITIVE_TITLE_RE.search(str(result.get("collectionName") or "")):
        return 0.12, "false_positive_pattern", "title"
    return 0.22, "weak_search_result", "search_result"


def candidate_from_itunes_result(
    comedian: PodcastDiscoveryComedian,
    result: dict[str, Any],
    *,
    search_term: str,
    rank: int,
) -> Optional[ItunesPodcastCandidate]:
    collection_id = result.get("collectionId")
    title = _string_or_none(result.get("collectionName"))
    if collection_id in (None, "") or not title:
        return None

    source_podcast_id = str(collection_id)
    author_name = _string_or_none(result.get("artistName"))
    feed_url = _string_or_none(result.get("feedUrl"))
    website_url = _string_or_none(result.get("collectionViewUrl"))
    image_url = _string_or_none(
        result.get("artworkUrl600") or result.get("artworkUrl100") or result.get("artworkUrl60")
    )
    description = _string_or_none(result.get("description"))
    confidence, band, match_field = _score_result(comedian, result, search_term)
    normalized_match = normalize_match_text(search_term)
    evidence = {
        "search_term": search_term,
        "matched_name": search_term,
        "normalized_match": normalized_match,
        "rank": rank,
        "confidence_band": band,
        "match_field": match_field,
        "source_fields": {
            "collection_id": collection_id,
            "track_id": result.get("trackId"),
            "collection_name": title,
            "artist_name": author_name,
            "feed_url": feed_url,
            "collection_view_url": website_url,
            "image_url": image_url,
            "primary_genre_name": result.get("primaryGenreName"),
            "genre_ids": result.get("genreIds"),
            "genres": result.get("genres"),
        },
    }
    return ItunesPodcastCandidate(
        comedian_id=comedian.comedian_id,
        source_podcast_id=source_podcast_id,
        matched_name=search_term,
        normalized_match=normalized_match,
        confidence=confidence,
        title=title,
        author_name=author_name,
        feed_url=feed_url,
        website_url=website_url,
        image_url=image_url,
        description=description,
        evidence=evidence,
    )


def discover_candidates_for_comedians(
    comedians: list[PodcastDiscoveryComedian],
    *,
    max_results: int,
    country: str,
    request_delay: float = _DEFAULT_REQUEST_DELAY_S,
    session: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[ItunesPodcastCandidate], int]:
    candidates: list[ItunesPodcastCandidate] = []
    failed = 0
    for comedian_index, comedian in enumerate(comedians, start=1):
        if comedian_index > 1 and request_delay > 0:
            sleep(request_delay)
        seen_ids: set[str] = set()
        for term_index, search_term in enumerate(build_search_terms(comedian), start=1):
            if term_index > 1 and request_delay > 0:
                sleep(request_delay)
            try:
                results = search_itunes_podcasts(
                    search_term,
                    limit=max_results,
                    country=country,
                    session=session,
                    sleep=sleep,
                )
            except Exception as exc:
                failed += 1
                Logger.warn(
                    f"[itunes-podcasts] search failed for comedian {comedian.comedian_id} "
                    f"'{comedian.name}' term '{search_term}': {exc}"
                )
                continue
            for rank, result in enumerate(results, start=1):
                candidate = candidate_from_itunes_result(comedian, result, search_term=search_term, rank=rank)
                if candidate is None or candidate.source_podcast_id in seen_ids:
                    continue
                seen_ids.add(candidate.source_podcast_id)
                candidates.append(candidate)
    return candidates, failed


def _json_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def load_active_deny_list(cur: Any) -> tuple[set[tuple[str, str]], set[str]]:
    cur.execute(_GET_ACTIVE_DENY_LIST_SQL)
    deny_keys: set[tuple[str, str]] = set()
    deny_urls: set[str] = set()
    for row in cur.fetchall():
        source, source_podcast_id, feed_url = row
        if source and source_podcast_id:
            deny_keys.add((str(source), str(source_podcast_id)))
        if feed_url:
            deny_urls.add(str(feed_url))
    return deny_keys, deny_urls


def candidate_is_denied(
    candidate: ItunesPodcastCandidate,
    deny_keys: set[tuple[str, str]],
    deny_urls: set[str],
) -> bool:
    if (candidate.source, candidate.source_podcast_id) in deny_keys:
        return True
    if candidate.feed_url and candidate.feed_url in deny_urls:
        return True
    return False


def _podcast_evidence(candidate: ItunesPodcastCandidate) -> dict[str, Any]:
    return {
        "provider": _SOURCE,
        "discovered_by": "search_itunes_podcasts",
        "matched_name": candidate.matched_name,
        "normalized_match": candidate.normalized_match,
        "confidence": candidate.confidence,
        "confidence_band": candidate.evidence.get("confidence_band"),
    }


def _review_evidence(candidate: ItunesPodcastCandidate) -> dict[str, Any]:
    evidence = dict(candidate.evidence)
    evidence["matched_name"] = candidate.matched_name
    evidence["normalized_match"] = candidate.normalized_match
    evidence["confidence"] = candidate.confidence
    return evidence


def _source_payload(candidate: ItunesPodcastCandidate) -> dict[str, Any]:
    fields = candidate.evidence.get("source_fields")
    return fields if isinstance(fields, dict) else {}


def _itunes_external_ids(candidate: ItunesPodcastCandidate) -> dict[str, Any]:
    return {"itunes_collection_id": candidate.source_podcast_id}


def _find_existing_podcast_by_feed_url(
    conn: Any, candidate: ItunesPodcastCandidate
) -> Optional[tuple[int, dict[str, Any]]]:
    if not candidate.feed_url:
        return None
    with conn.cursor() as cur:
        cur.execute(
            _FIND_PODCAST_BY_FEED_URL_SQL,
            (candidate.feed_url, candidate.source, candidate.source_podcast_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return int(row[0]), _json_mapping(row[1])


def _upsert_itunes_podcast(conn: Any, candidate: ItunesPodcastCandidate) -> int:
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_OR_UPDATE_ITUNES_PODCAST_SQL,
            (
                candidate.source,
                candidate.source_podcast_id,
                build_podcast_slug(candidate.title, candidate.source, candidate.source_podcast_id),
                candidate.feed_url,
                candidate.title,
                candidate.author_name,
                candidate.website_url,
                candidate.image_url,
                candidate.description,
                json.dumps(_itunes_external_ids(candidate), sort_keys=True),
                json.dumps(_podcast_evidence(candidate), sort_keys=True),
                json.dumps(_source_payload(candidate), sort_keys=True),
            ),
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f"upsert returned no podcast id for iTunes collection {candidate.source_podcast_id}")
    return int(row[0])


def _merge_itunes_id_into_existing_podcast(
    conn: Any, podcast_id: int, external_ids: dict[str, Any], candidate: ItunesPodcastCandidate
) -> int:
    merged = dict(external_ids)
    merged.update(_itunes_external_ids(candidate))
    with conn.cursor() as cur:
        cur.execute(
            _MERGE_ITUNES_ID_BY_FEED_URL_SQL,
            (json.dumps(merged, sort_keys=True), podcast_id),
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f"feed URL merge returned no podcast id for podcast {podcast_id}")
    return int(row[0])


def _upsert_candidate_review(conn: Any, podcast_id: int, candidate: ItunesPodcastCandidate) -> None:
    with conn.cursor() as cur:
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


def upsert_candidate_with_conn(conn: Any, candidate: ItunesPodcastCandidate) -> UpsertResult:
    existing = _find_existing_podcast_by_feed_url(conn, candidate)
    if existing:
        podcast_id = _merge_itunes_id_into_existing_podcast(conn, existing[0], existing[1], candidate)
        action = "merged_feed_url"
    else:
        podcast_id = _upsert_itunes_podcast(conn, candidate)
        action = "upserted_source"
    _upsert_candidate_review(conn, podcast_id, candidate)
    return UpsertResult(podcast_id=podcast_id, action=action)


def stable_feed_url_id(feed_url: str) -> str:
    return f"feed_url:{hashlib.sha1(feed_url.encode('utf-8')).hexdigest()}"
