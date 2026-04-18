#!/usr/bin/env python3
"""Backfill ``clubs.description`` and ``clubs.hours`` by fetching each club's website.

Fetches the stored ``website`` for every visible, active club that is still
missing either ``description`` or ``hours``, extracts both fields via
``laughtrack.utilities.domain.club.enrichment``, and persists anything that
was parsed.  Existing non-null values are left alone so manual admin edits
are preserved; pass ``--force`` to overwrite them.

Usage:
    python -m scripts.core.update_club_enrichment
    python -m scripts.core.update_club_enrichment --limit 50
    python -m scripts.core.update_club_enrichment --dry-run
    python -m scripts.core.update_club_enrichment --force --club-ids 12 34
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from curl_cffi.requests import AsyncSession
from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_connection
from laughtrack.foundation.infrastructure.http.client import (
    HttpClient,
    _bot_block_reason,
    _get_js_browser,
    close_js_browser,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.club.enrichment import (
    extract_description,
    extract_hours,
)

_CONCURRENCY = 8
_TIMEOUT_SECONDS = 25


@dataclass
class _ClubFetchResult:
    """Outcome of a single club fetch + extraction attempt.

    ``status`` distinguishes bot-blocked pages from plain "nothing
    extractable" so the nightly summary can surface each failure mode
    independently (a rising bot_blocked count signals a platform move,
    not a content-quality issue).
    """

    club_id: int
    status: str  # "extracted" | "bot_blocked" | "no_data" | "fetch_failed"
    description: Optional[str] = None
    hours: Optional[Dict[str, str]] = None


_GET_CLUBS_SQL = """
    SELECT id, name, website
    FROM clubs
    WHERE visible = TRUE
      AND status = 'active'
      AND website IS NOT NULL
      AND website <> ''
      {extra_filter}
    ORDER BY popularity DESC NULLS LAST, id
"""

_UPDATE_SQL_FILL_NULLS = """
    UPDATE clubs AS c
    SET description = COALESCE(c.description, v.description),
        hours       = COALESCE(c.hours,       v.hours)
    FROM (VALUES %s) AS v(id, description, hours)
    WHERE c.id = v.id
"""

_UPDATE_SQL_FORCE = """
    UPDATE clubs AS c
    SET description = COALESCE(v.description, c.description),
        hours       = COALESCE(v.hours,       c.hours)
    FROM (VALUES %s) AS v(id, description, hours)
    WHERE c.id = v.id
"""

_VALUES_TEMPLATE = "(%s, %s, %s::jsonb)"


def _load_target_clubs(
    club_ids: Optional[List[int]],
    missing_only: bool,
    limit: Optional[int],
) -> List[Tuple[int, str, str]]:
    filters: List[str] = []
    params: List = []
    if club_ids:
        filters.append("AND id = ANY(%s::int[])")
        params.append(club_ids)
    if missing_only:
        filters.append("AND (description IS NULL OR hours IS NULL)")
    sql = _GET_CLUBS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        sql += f"\n    LIMIT {int(limit)}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            rows = cur.fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


async def _fetch_with_playwright(url: str, context: dict) -> Optional[str]:
    """Manual Playwright fallback for curl network-level errors.

    ``HttpClient.fetch_html`` only falls back on 4xx/5xx responses and
    bot-block bodies — plain TLS or DNS errors raise before the fallback
    hook runs, so we catch them here and retry through the shared browser.

    Reuses the shared ``HttpClient`` Playwright singleton (same one the
    built-in bot-block fallback uses) so a nightly run with several TLS
    failures doesn't pay a fresh Chromium-launch cost per miss.  Teardown
    is handled by ``close_js_browser`` in ``_enrich``'s ``finally``.
    """
    browser = _get_js_browser()
    if browser is None:
        return None
    try:
        return await browser.fetch_html(url)
    except Exception as exc:
        Logger.warn(
            f"[club-enrichment] Playwright retry failed for {url}: {exc}",
            context,
        )
        return None


async def _process_club(
    session: AsyncSession,
    semaphore: asyncio.Semaphore,
    club_id: int,
    name: str,
    website: str,
) -> _ClubFetchResult:
    """Fetch + extract for a single club.

    Always returns a ``_ClubFetchResult``; callers inspect ``status`` to
    distinguish extracted data, bot-block interstitials, pages with no
    structured content, and outright fetch failures.
    """
    context = {"club_id": club_id, "club_name": name}
    async with semaphore:
        html: Optional[str] = None
        try:
            html = await HttpClient.fetch_html(session, website, logger_context=context)
        except Exception as exc:
            Logger.warn(
                f"[club-enrichment] curl fetch failed for club {club_id} '{name}' "
                f"({website}): {exc} — retrying with Playwright",
                context,
            )
            html = await _fetch_with_playwright(website, context)

        if not html:
            return _ClubFetchResult(club_id=club_id, status="fetch_failed")

        bot_sig = _bot_block_reason(html)
        if bot_sig is not None:
            host = urlparse(website).hostname or website
            Logger.warn(
                f"[club-enrichment] bot-blocked: {host} (club {club_id} "
                f"'{name}', signature {bot_sig!r})",
                context,
            )
            return _ClubFetchResult(club_id=club_id, status="bot_blocked")

        description = extract_description(html)
        hours = extract_hours(html)
        if description is None and hours is None:
            return _ClubFetchResult(club_id=club_id, status="no_data")
        return _ClubFetchResult(
            club_id=club_id,
            status="extracted",
            description=description,
            hours=hours,
        )


async def _enrich(
    targets: List[Tuple[int, str, str]],
    *,
    force: bool,
    dry_run: bool,
) -> Dict[str, int]:
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    async with AsyncSession(impersonate="chrome124", timeout=_TIMEOUT_SECONDS) as session:
        try:
            extracted = await asyncio.gather(
                *(
                    _process_club(session, semaphore, cid, name, website)
                    for cid, name, website in targets
                )
            )
        finally:
            # Release the shared Playwright singleton on the same loop that
            # created it — mirrors the scraper fleet's teardown pattern.
            await close_js_browser()

    rows: List[Tuple[int, Optional[str], Optional[str]]] = []
    desc_hits = 0
    hours_hits = 0
    bot_blocked = 0
    for result in extracted:
        if result.status == "bot_blocked":
            bot_blocked += 1
            continue
        if result.status != "extracted":
            continue
        if result.description:
            desc_hits += 1
        if result.hours:
            hours_hits += 1
        rows.append(
            (
                result.club_id,
                result.description,
                json.dumps(result.hours) if result.hours else None,
            )
        )

    Logger.info(
        f"[club-enrichment] extracted from {len(rows)}/{len(targets)} clubs — "
        f"description={desc_hits}, hours={hours_hits}, bot_blocked={bot_blocked}"
    )

    if dry_run:
        Logger.info("[club-enrichment] --dry-run: skipping DB write")
        return {
            "fetched": len(targets),
            "extracted": len(rows),
            "description_hits": desc_hits,
            "hours_hits": hours_hits,
            "bot_blocked": bot_blocked,
            "written": 0,
        }

    written = 0
    if rows:
        sql = _UPDATE_SQL_FORCE if force else _UPDATE_SQL_FILL_NULLS
        with get_connection() as conn:
            with conn.cursor() as cur:
                # page_size = len(rows) keeps all updates in one execute_values
                # batch so cur.rowcount reflects the entire run — with the
                # default 100-row pages, rowcount only captures the last batch.
                execute_values(
                    cur, sql, rows, template=_VALUES_TEMPLATE, page_size=max(len(rows), 1)
                )
                written = cur.rowcount
        Logger.info(f"[club-enrichment] wrote updates for {written} clubs")

    return {
        "fetched": len(targets),
        "extracted": len(rows),
        "description_hits": desc_hits,
        "hours_hits": hours_hits,
        "bot_blocked": bot_blocked,
        "written": written,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill clubs.description and clubs.hours by fetching each club's "
            "website and extracting schema.org / meta tags."
        ),
    )
    parser.add_argument(
        "--club-ids",
        nargs="+",
        type=int,
        default=None,
        help="Limit run to specific club IDs (otherwise every visible club is eligible).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Re-scan clubs that already have description/hours (default skips them).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-null description/hours when extraction succeeds.",
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
        help="Process at most N clubs (useful for smoke-testing).",
    )

    args = parser.parse_args()
    missing_only = not (args.all or args.force or args.club_ids)

    targets = _load_target_clubs(
        club_ids=args.club_ids,
        missing_only=missing_only,
        limit=args.limit,
    )
    Logger.info(
        f"[club-enrichment] {len(targets)} clubs eligible "
        f"(missing_only={missing_only}, force={args.force}, dry_run={args.dry_run})"
    )
    if not targets:
        return

    try:
        summary = asyncio.run(
            _enrich(targets, force=args.force, dry_run=args.dry_run)
        )
    except KeyboardInterrupt:
        Logger.info("[club-enrichment] cancelled by user")
        sys.exit(130)
    except Exception as exc:
        Logger.error(f"[club-enrichment] failed: {exc}")
        sys.exit(1)

    # Short JSON summary on stdout for programmatic callers (nightly workflow).
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
