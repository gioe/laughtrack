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

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

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

# Wikipedia's standard disambiguation suffix for performers. When the exact-name
# lookup hits a non-comedian page, disambiguation page, or 404, retrying with
# "<name> (comedian)" often resolves to the correct article (e.g. a stand-up
# named "Mike Johnson" whose dedicated page is titled "Mike Johnson (comedian)").
_DISAMBIGUATION_QUALIFIER = "(comedian)"

# Statuses where a qualifier retry has a plausible chance of finding the right
# page. fetch_failed / HTTP errors indicate transient issues, not name collisions,
# so retrying with a different title wastes requests without useful signal.
_RETRY_ELIGIBLE_STATUSES = frozenset({"not_found", "disambiguation", "not_comedian"})


def _has_parenthetical_qualifier(name: str) -> bool:
    """True when ``name`` already carries a Wikipedia-style disambiguator.

    DB names like ``"Bo Burnham (musician)"`` or ``"Paula Poundstone (comedian)"``
    would produce invalid double-qualifier titles (``"Bo Burnham (musician) (comedian)"``)
    that always 404 — skipping the retry avoids the wasted request.
    """
    stripped = name.rstrip()
    return stripped.endswith(")") and "(" in stripped


@dataclass
class _BioFetchResult:
    """Outcome of a single Wikipedia summary lookup.

    ``status`` distinguishes successful extraction from disambiguation pages,
    missing pages (404), non-comedian pages (heuristic rejection), and fetch
    failures so the nightly summary can surface each mode independently.
    ``title_used`` records which Wikipedia title produced the outcome so nightly
    logs can distinguish exact-name lookups from qualifier-retry lookups.
    """

    comedian_id: int
    status: str  # "extracted" | "not_found" | "disambiguation" | "not_comedian" | "fetch_failed"
    bio: Optional[str] = None
    title_used: Optional[str] = None
    qualifier_retry_used: bool = False


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


async def _fetch_by_title(
    session: AsyncSession,
    comedian_id: int,
    comedian_name: str,
    title_text: str,
) -> _BioFetchResult:
    """Fetch + parse a single Wikipedia summary for a specific title.

    Wikipedia's URL format uses underscores in place of spaces; ``quote``
    handles the rest of the path segment including unicode characters.
    ``comedian_name`` is the DB name used for log context; ``title_text`` is
    the actual Wikipedia title we're querying (may be the bare name or a
    qualifier-retry variant like ``"Mike Johnson (comedian)"``).
    """
    title = quote(title_text.replace(" ", "_"), safe="")
    url = f"{_WIKIPEDIA_SUMMARY_BASE}{title}"
    context = {
        "comedian_id": comedian_id,
        "comedian_name": comedian_name,
        "title": title_text,
    }

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
                f"[comedian-bio] fetch failed for comedian {comedian_id} '{comedian_name}' (title='{title_text}'): {exc}",
                context,
            )
            return _BioFetchResult(
                comedian_id=comedian_id, status="fetch_failed", title_used=title_text
            )

        # Only 429 is retried — 404 is deterministic and 5xx errors are rare
        # enough that an immediate fail keeps the nightly summary honest.
        if resp.status_code != 429:
            break
        if attempt + 1 < _MAX_RETRIES:
            await asyncio.sleep(_RETRY_BASE_DELAY_S * (2 ** attempt))

    assert resp is not None  # loop always assigns or returns
    if resp.status_code == 404:
        return _BioFetchResult(
            comedian_id=comedian_id, status="not_found", title_used=title_text
        )
    if resp.status_code >= 400:
        Logger.warn(
            f"[comedian-bio] HTTP {resp.status_code} for comedian {comedian_id} '{comedian_name}' (title='{title_text}')",
            context,
        )
        return _BioFetchResult(
            comedian_id=comedian_id, status="fetch_failed", title_used=title_text
        )

    try:
        payload = resp.json()
    except Exception as exc:
        Logger.warn(
            f"[comedian-bio] non-JSON response for comedian {comedian_id} '{comedian_name}' (title='{title_text}'): {exc}",
            context,
        )
        return _BioFetchResult(
            comedian_id=comedian_id, status="fetch_failed", title_used=title_text
        )

    if isinstance(payload, dict) and payload.get("type") == "disambiguation":
        return _BioFetchResult(
            comedian_id=comedian_id, status="disambiguation", title_used=title_text
        )

    bio = extract_bio(payload)
    if bio is None:
        return _BioFetchResult(
            comedian_id=comedian_id, status="not_comedian", title_used=title_text
        )
    return _BioFetchResult(
        comedian_id=comedian_id, status="extracted", bio=bio, title_used=title_text
    )


async def _fetch_summary(
    session: AsyncSession,
    comedian_id: int,
    name: str,
) -> _BioFetchResult:
    """Fetch a bio by name, retrying once with a ``(comedian)`` qualifier on rejection.

    Common-name collisions (e.g. "John Smith", "Mike Johnson") can resolve to
    an unrelated person's page whose prose happens to mention comedy-adjacent
    language, or to a disambiguation stub, or to 404 when Wikipedia's canonical
    title carries a ``(comedian)`` suffix. A single retry with the standard
    disambiguator catches most of these without materially increasing request
    volume. Transient fetch failures are not retried with a new title — the
    issue is network-level, not a naming collision.

    Accept/reject decisions are logged at INFO so the nightly run surfaces
    anomalies without requiring a separate audit pass.
    """
    result = await _fetch_by_title(session, comedian_id, name, name)

    if result.status == "extracted":
        Logger.info(
            f"[comedian-bio] accepted: comedian_id={comedian_id} '{name}' (title='{result.title_used}')"
        )
        return result

    if result.status in _RETRY_ELIGIBLE_STATUSES and not _has_parenthetical_qualifier(name):
        qualifier_title = f"{name} {_DISAMBIGUATION_QUALIFIER}"
        retry = await _fetch_by_title(session, comedian_id, name, qualifier_title)
        if retry.status == "extracted":
            retry.qualifier_retry_used = True
            Logger.info(
                f"[comedian-bio] accepted via qualifier retry: comedian_id={comedian_id} "
                f"'{name}' original={result.status} -> title='{qualifier_title}'"
            )
            return retry
        Logger.info(
            f"[comedian-bio] rejected: comedian_id={comedian_id} '{name}' "
            f"original={result.status} retry('{qualifier_title}')={retry.status}"
        )
        return result

    # fetch_failed / other non-retryable statuses: log and return as-is.
    Logger.info(
        f"[comedian-bio] rejected: comedian_id={comedian_id} '{name}' status={result.status}"
    )
    return result


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
    qualifier_retry_saves = 0
    for result in results:
        if result.status == "extracted" and result.bio:
            rows.append((result.comedian_id, result.bio))
            if result.qualifier_retry_used:
                qualifier_retry_saves += 1
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
        f"not_comedian={not_comedian}, fetch_failed={fetch_failed}, "
        f"qualifier_retry_saves={qualifier_retry_saves}"
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
            "qualifier_retry_saves": qualifier_retry_saves,
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
        "qualifier_retry_saves": qualifier_retry_saves,
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
    parser.add_argument(
        "--summary-out",
        type=str,
        default=None,
        help=(
            "Write the final summary JSON to this path (in addition to stdout). "
            "Used by the nightly workflow to avoid fragile 'tail -n1' parsing of "
            "tee'd stdout — any trailing Logger line would otherwise break the "
            "downstream Discord post."
        ),
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
        empty_summary = {
            "fetched": 0,
            "extracted": 0,
            "written": 0,
            "not_found": 0,
            "disambiguation": 0,
            "not_comedian": 0,
            "fetch_failed": 0,
            "qualifier_retry_saves": 0,
        }
        print(json.dumps(empty_summary))
        if args.summary_out:
            Path(args.summary_out).write_text(json.dumps(empty_summary), encoding="utf-8")
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
    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
