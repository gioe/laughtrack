#!/usr/bin/env python3
"""Backfill ``comedians.bio`` from Wikipedia page summaries.

Fetches the Wikipedia REST summary (``/api/rest_v1/page/summary/{title}``)
for every comedian whose ``bio`` column is still NULL, validates the response
as a real comedian page (not disambiguation, mentions comedy), and writes the
extracted text back to the DB. Existing non-null bios are preserved; pass
``--force`` to overwrite them.

Usage:
    python -m scripts.core.update_comedian_bios
    python -m scripts.core.update_comedian_bios --limit 50
    python -m scripts.core.update_comedian_bios --dry-run
    python -m scripts.core.update_comedian_bios --force --comedian-ids 12 34
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from curl_cffi.requests import AsyncSession
from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.comedian.bio_enrichment import extract_bio

# Wikipedia's REST API throttles unauthenticated clients aggressively by IP —
# a single host sustaining > ~5 req/s rapidly starts getting HTTP 429. Keep
# concurrency low and always retry 429s with exponential backoff.
_CONCURRENCY = 2
_TIMEOUT_SECONDS = 15
_MAX_RETRIES = 3
_RETRY_BASE_DELAY_S = 2.0
_WIKIPEDIA_SUMMARY_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary/"
# Wikipedia's REST API requires an identifying User-Agent per their etiquette
# policy (https://meta.wikimedia.org/wiki/User-Agent_policy). A generic Python
# UA gets silently rate-limited or returns 403 for high-volume callers.
_USER_AGENT = (
    "LaughTrack/1.0 (comedy show aggregator; https://laugh-track.com) "
    "comedian-bio-enrichment"
)


@dataclass
class _BioFetchResult:
    """Outcome of a single Wikipedia summary lookup.

    ``status`` distinguishes successful extraction from disambiguation pages,
    missing pages (404), non-comedian pages (heuristic rejection), and fetch
    failures so the nightly summary can surface each mode independently.
    """

    comedian_id: int
    status: str  # "extracted" | "not_found" | "disambiguation" | "not_comedian" | "fetch_failed"
    bio: Optional[str] = None


_GET_COMEDIANS_SQL = """
    SELECT id, name
    FROM comedians
    WHERE parent_comedian_id IS NULL
      {extra_filter}
    ORDER BY popularity DESC NULLS LAST, total_shows DESC NULLS LAST, id
"""

_UPDATE_SQL_FILL_NULLS = """
    UPDATE comedians AS c
    SET bio = COALESCE(c.bio, v.bio)
    FROM (VALUES %s) AS v(id, bio)
    WHERE c.id = v.id
"""

_UPDATE_SQL_FORCE = """
    UPDATE comedians AS c
    SET bio = v.bio
    FROM (VALUES %s) AS v(id, bio)
    WHERE c.id = v.id
"""

_VALUES_TEMPLATE = "(%s, %s)"


def _load_target_comedians(
    comedian_ids: Optional[List[int]],
    missing_only: bool,
    limit: Optional[int],
) -> List[Tuple[int, str]]:
    filters: List[str] = []
    params: List = []
    if comedian_ids:
        filters.append("AND id = ANY(%s::int[])")
        params.append(comedian_ids)
    if missing_only:
        filters.append("AND bio IS NULL")
    sql = _GET_COMEDIANS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        sql += f"\n    LIMIT {int(limit)}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            rows = cur.fetchall()
    return [(r[0], r[1]) for r in rows]


async def _fetch_summary(
    session: AsyncSession,
    comedian_id: int,
    name: str,
) -> _BioFetchResult:
    """Fetch + parse a single Wikipedia summary, with rejection diagnostics.

    Wikipedia's URL format uses underscores in place of spaces; ``quote``
    handles the rest of the path segment including unicode characters.
    """
    title = quote(name.replace(" ", "_"), safe="")
    url = f"{_WIKIPEDIA_SUMMARY_BASE}{title}"
    context = {"comedian_id": comedian_id, "comedian_name": name}

    resp = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await session.get(
                url,
                headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
                timeout=_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            Logger.warn(
                f"[comedian-bio] fetch failed for comedian {comedian_id} '{name}': {exc}",
                context,
            )
            return _BioFetchResult(comedian_id=comedian_id, status="fetch_failed")

        # Only 429 is retried — 404 is deterministic and 5xx errors are rare
        # enough that an immediate fail keeps the nightly summary honest.
        if resp.status_code != 429:
            break
        if attempt + 1 < _MAX_RETRIES:
            await asyncio.sleep(_RETRY_BASE_DELAY_S * (2 ** attempt))

    assert resp is not None  # loop always assigns or returns
    if resp.status_code == 404:
        return _BioFetchResult(comedian_id=comedian_id, status="not_found")
    if resp.status_code >= 400:
        Logger.warn(
            f"[comedian-bio] HTTP {resp.status_code} for comedian {comedian_id} '{name}'",
            context,
        )
        return _BioFetchResult(comedian_id=comedian_id, status="fetch_failed")

    try:
        payload = resp.json()
    except Exception as exc:
        Logger.warn(
            f"[comedian-bio] non-JSON response for comedian {comedian_id} '{name}': {exc}",
            context,
        )
        return _BioFetchResult(comedian_id=comedian_id, status="fetch_failed")

    if isinstance(payload, dict) and payload.get("type") == "disambiguation":
        return _BioFetchResult(comedian_id=comedian_id, status="disambiguation")

    bio = extract_bio(payload)
    if bio is None:
        return _BioFetchResult(comedian_id=comedian_id, status="not_comedian")
    return _BioFetchResult(comedian_id=comedian_id, status="extracted", bio=bio)


async def _process(
    session: AsyncSession,
    semaphore: asyncio.Semaphore,
    comedian_id: int,
    name: str,
) -> _BioFetchResult:
    async with semaphore:
        return await _fetch_summary(session, comedian_id, name)


async def _enrich(
    targets: List[Tuple[int, str]],
    *,
    force: bool,
    dry_run: bool,
) -> Dict[str, int]:
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    async with AsyncSession(timeout=_TIMEOUT_SECONDS) as session:
        results = await asyncio.gather(
            *(_process(session, semaphore, cid, name) for cid, name in targets)
        )

    rows: List[Tuple[int, str]] = []
    not_found = 0
    disambiguation = 0
    not_comedian = 0
    fetch_failed = 0
    for result in results:
        if result.status == "extracted" and result.bio:
            rows.append((result.comedian_id, result.bio))
        elif result.status == "not_found":
            not_found += 1
        elif result.status == "disambiguation":
            disambiguation += 1
        elif result.status == "not_comedian":
            not_comedian += 1
        elif result.status == "fetch_failed":
            fetch_failed += 1

    Logger.info(
        f"[comedian-bio] extracted for {len(rows)}/{len(targets)} comedians — "
        f"not_found={not_found}, disambiguation={disambiguation}, "
        f"not_comedian={not_comedian}, fetch_failed={fetch_failed}"
    )

    if dry_run:
        Logger.info("[comedian-bio] --dry-run: skipping DB write")
        return {
            "fetched": len(targets),
            "extracted": len(rows),
            "written": 0,
            "not_found": not_found,
            "disambiguation": disambiguation,
            "not_comedian": not_comedian,
            "fetch_failed": fetch_failed,
        }

    written = 0
    if rows:
        sql = _UPDATE_SQL_FORCE if force else _UPDATE_SQL_FILL_NULLS
        with get_connection() as conn:
            with conn.cursor() as cur:
                # page_size = len(rows) keeps all updates in one execute_values
                # batch so cur.rowcount reflects the entire run.
                execute_values(
                    cur,
                    sql,
                    rows,
                    template=_VALUES_TEMPLATE,
                    page_size=max(len(rows), 1),
                )
                written = cur.rowcount
        Logger.info(f"[comedian-bio] wrote bios for {written} comedians")

    return {
        "fetched": len(targets),
        "extracted": len(rows),
        "written": written,
        "not_found": not_found,
        "disambiguation": disambiguation,
        "not_comedian": not_comedian,
        "fetch_failed": fetch_failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill comedians.bio by fetching each comedian's Wikipedia summary "
            "and extracting the intro prose."
        ),
    )
    parser.add_argument(
        "--comedian-ids",
        nargs="+",
        type=int,
        default=None,
        help="Limit run to specific comedian IDs (otherwise every bio-less comedian is eligible).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Re-scan comedians that already have a bio (default skips them).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-null bios when a new one is extracted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + extract, but do not write to the database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N comedians (useful for smoke-testing or nightly caps).",
    )

    args = parser.parse_args()
    missing_only = not (args.all or args.force or args.comedian_ids)

    targets = _load_target_comedians(
        comedian_ids=args.comedian_ids,
        missing_only=missing_only,
        limit=args.limit,
    )
    Logger.info(
        f"[comedian-bio] {len(targets)} comedians eligible "
        f"(missing_only={missing_only}, force={args.force}, dry_run={args.dry_run})"
    )
    if not targets:
        print(json.dumps({
            "fetched": 0,
            "extracted": 0,
            "written": 0,
            "not_found": 0,
            "disambiguation": 0,
            "not_comedian": 0,
            "fetch_failed": 0,
        }))
        return

    try:
        summary = asyncio.run(
            _enrich(targets, force=args.force, dry_run=args.dry_run)
        )
    except KeyboardInterrupt:
        Logger.info("[comedian-bio] cancelled by user")
        sys.exit(130)
    except Exception as exc:
        Logger.error(f"[comedian-bio] failed: {exc}")
        sys.exit(1)

    print(json.dumps(summary))


if __name__ == "__main__":
    main()
