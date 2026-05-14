#!/usr/bin/env python3
"""Backfill comedian podcast appearances from the Podchaser GraphQL API.

The script queries top canonical comedians by popularity, searches Podchaser
episodes by comedian name, and replaces each processed comedian's appearance
rows with the current API result. Re-running is safe.

Usage:
    python -m scripts.core.populate_comedian_podcast_appearances --limit 100 --dry-run
    python -m scripts.core.populate_comedian_podcast_appearances --limit 100
    python -m scripts.core.populate_comedian_podcast_appearances --comedian-ids 12 34
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from curl_cffi.requests import AsyncSession
from dotenv import dotenv_values
from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger

_PODCHASER_GRAPHQL_URL = "https://api.podchaser.com/graphql"
_DEFAULT_FIRST = 25
_MAX_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0
_REQUEST_DELAY_S = float(os.environ.get("PODCHASER_REQUEST_DELAY_S", "1.0"))
_MIN_POINTS_REMAINING = int(os.environ.get("PODCHASER_MIN_POINTS_REMAINING", "100"))
_TIMEOUT_SECONDS = 30


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


def _load_env_defaults(path: Path = Path(".env")) -> None:
    for key, value in dotenv_values(path).items():
        if value:
            os.environ.setdefault(key, value)


def _podchaser_token() -> str:
    token = os.environ.get("PODCHASER_ACCESS_TOKEN") or os.environ.get("PODCHASER_API_TOKEN")
    if not token:
        print(
            "Error: set PODCHASER_ACCESS_TOKEN (or PODCHASER_API_TOKEN) before running this script.",
            file=sys.stderr,
        )
        sys.exit(2)
    return token


def _build_episode_search_payload(search_term: str, first: int = _DEFAULT_FIRST) -> dict[str, Any]:
    return {
        "query": """
            query ComedianEpisodeSearch($searchTerm: String!, $first: Int!) {
              episodes(searchTerm: $searchTerm, first: $first) {
                data {
                  id
                  title
                  airDate
                  url
                  webUrl
                  podcast {
                    title
                  }
                }
              }
            }
        """,
        "variables": {"searchTerm": search_term, "first": first},
    }


def _extract_episode_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    episodes = (payload.get("data") or {}).get("episodes") or {}
    items = episodes.get("data") or episodes.get("nodes") or []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _normalized_terms(value: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 1]


def _match_evidence(comedian_name: str, episode_title: str, podcast_name: str) -> dict[str, Any]:
    terms = _normalized_terms(comedian_name)
    haystack = set(_normalized_terms(f"{episode_title} {podcast_name}"))
    matched_terms = [term for term in terms if term in haystack]
    return {
        "search_term": comedian_name,
        "matched_terms": matched_terms,
        "episode_title": episode_title,
        "podcast_name": podcast_name,
    }


def _match_confidence(evidence: dict[str, Any]) -> float:
    matched_terms = evidence.get("matched_terms")
    search_terms = _normalized_terms(str(evidence.get("search_term") or ""))
    if not isinstance(matched_terms, list) or not search_terms:
        return 0.0
    return round(len(matched_terms) / len(search_terms), 2)


def _parse_episode_rows(
    comedian_id: int,
    comedian_name: str,
    payload: dict[str, Any],
) -> list[PodcastAppearanceRow]:
    rows: list[PodcastAppearanceRow] = []
    for episode in _extract_episode_items(payload):
        episode_id = episode.get("id")
        title = episode.get("title")
        podcast = episode.get("podcast") or {}
        podcast_name = podcast.get("title") if isinstance(podcast, dict) else None
        episode_url = episode.get("url") or episode.get("webUrl")
        if not episode_id or not title or not podcast_name or not episode_url:
            continue
        evidence = _match_evidence(
            comedian_name=comedian_name,
            episode_title=str(title),
            podcast_name=str(podcast_name),
        )
        rows.append(
            PodcastAppearanceRow(
                comedian_id=comedian_id,
                source="podchaser",
                source_episode_id=str(episode_id),
                podcast_name=str(podcast_name),
                episode_title=str(title),
                release_date=episode.get("airDate") or episode.get("releaseDate"),
                episode_url=str(episode_url),
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
    return _BASE_RETRY_DELAY_S * (2 ** attempt)


def _points_remaining(headers: dict[str, str] | None) -> Optional[int]:
    for name in ("X-Podchaser-Points-Remaining", "x-podchaser-points-remaining"):
        value = (headers or {}).get(name)
        if value is None:
            continue
        try:
            return int(value)
        except ValueError:
            return None
    return None


async def _fetch_podchaser_episodes(
    session: AsyncSession,
    comedian_id: int,
    comedian_name: str,
    token: str,
    first: int = _DEFAULT_FIRST,
) -> list[PodcastAppearanceRow]:
    result = await _fetch_podchaser_episode_result(
        session=session,
        comedian_id=comedian_id,
        comedian_name=comedian_name,
        token=token,
        first=first,
    )
    return result.rows


async def _fetch_podchaser_episode_result(
    session: AsyncSession,
    comedian_id: int,
    comedian_name: str,
    token: str,
    first: int = _DEFAULT_FIRST,
) -> PodcastAppearanceFetchResult:
    payload = _build_episode_search_payload(comedian_name, first=first)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for attempt in range(_MAX_RETRIES):
        try:
            response = await session.post(
                _PODCHASER_GRAPHQL_URL,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            if attempt + 1 >= _MAX_RETRIES:
                Logger.warn(
                    f"[podchaser] fetch failed for comedian {comedian_id} '{comedian_name}': {exc}"
                )
                return PodcastAppearanceFetchResult(succeeded=False, rows=[])
            await asyncio.sleep(_BASE_RETRY_DELAY_S * (2 ** attempt))
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt + 1 >= _MAX_RETRIES:
                Logger.warn(
                    f"[podchaser] HTTP {response.status_code} for comedian {comedian_id} '{comedian_name}' after {_MAX_RETRIES} attempts"
                )
                return PodcastAppearanceFetchResult(succeeded=False, rows=[])
            delay = _retry_after_seconds(response.headers, attempt)
            Logger.warn(
                f"[podchaser] HTTP {response.status_code} for comedian {comedian_id} '{comedian_name}' — retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            continue

        if response.status_code >= 400:
            Logger.warn(
                f"[podchaser] HTTP {response.status_code} for comedian {comedian_id} '{comedian_name}'"
            )
            return PodcastAppearanceFetchResult(succeeded=False, rows=[])

        try:
            data = response.json()
        except Exception as exc:
            Logger.warn(
                f"[podchaser] non-JSON response for comedian {comedian_id} '{comedian_name}': {exc}"
            )
            return PodcastAppearanceFetchResult(succeeded=False, rows=[])

        if data.get("errors"):
            Logger.warn(
                f"[podchaser] GraphQL errors for comedian {comedian_id} '{comedian_name}': {data.get('errors')}"
            )
            return PodcastAppearanceFetchResult(succeeded=False, rows=[])

        remaining = _points_remaining(response.headers)
        if remaining is not None and remaining <= _MIN_POINTS_REMAINING:
            Logger.warn(
                f"[podchaser] quota nearly exhausted after comedian {comedian_id} '{comedian_name}': remaining_points={remaining}"
            )
        return PodcastAppearanceFetchResult(
            succeeded=True,
            rows=_parse_episode_rows(
                comedian_id=comedian_id,
                comedian_name=comedian_name,
                payload=data,
            ),
        )

    return PodcastAppearanceFetchResult(succeeded=False, rows=[])


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
            """,
            (comedian_ids,),
        )
        values = _row_values(rows)
        if values:
            execute_values(cur, _INSERT_SQL, values, template=_VALUES_TEMPLATE)
    return len(rows)


async def _populate(
    comedians: list[tuple[int, str]],
    token: str,
    first: int,
    dry_run: bool,
) -> dict[str, int]:
    all_rows: list[PodcastAppearanceRow] = []
    processed_ids: list[int] = []
    failed = 0

    async with AsyncSession() as session:
        for index, (comedian_id, name) in enumerate(comedians, start=1):
            if index > 1:
                await asyncio.sleep(_REQUEST_DELAY_S)
            result = await _fetch_podchaser_episode_result(
                session,
                comedian_id=comedian_id,
                comedian_name=name,
                token=token,
                first=first,
            )
            if not result.succeeded:
                failed += 1
                print(f"{name}: lookup failed; preserving existing rows")
                continue
            rows = result.rows
            processed_ids.append(comedian_id)
            all_rows.extend(rows)
            print(f"{name}: {len(rows)} episode(s)")

    if dry_run:
        for row in all_rows:
            print(
                f"  comedian_id={row.comedian_id} podcast={row.podcast_name!r} "
                f"title={row.episode_title!r} confidence={row.match_confidence:.2f} "
                f"url={row.episode_url}"
            )
        written = 0
    else:
        if processed_ids:
            with get_connection() as conn:
                written = _replace_appearances(conn, processed_ids, all_rows)
                conn.commit()
        else:
            written = 0

    return {
        "processed": len(comedians),
        "failed": failed,
        "matched_episodes": len(all_rows),
        "written": written,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate comedian podcast appearances from Podchaser",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max comedians to process")
    parser.add_argument("--comedian-ids", type=int, nargs="*", default=None)
    parser.add_argument("--comedian-name", default=None, help="Case-insensitive exact SQL pattern")
    parser.add_argument("--first", type=int, default=_DEFAULT_FIRST, help="Episodes per comedian search")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _load_env_defaults()
    token = _podchaser_token()
    comedians = _load_target_comedians(args.comedian_ids, args.comedian_name, args.limit)
    if not comedians:
        print("No comedians matched.")
        return

    print(f"Processing {len(comedians)} comedian(s)")
    summary = asyncio.run(
        _populate(
            comedians=comedians,
            token=token,
            first=args.first,
            dry_run=args.dry_run,
        )
    )
    print(summary)


if __name__ == "__main__":
    main()
