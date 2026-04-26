#!/usr/bin/env python3
"""Backfill ``clubs.description`` and ``clubs.hours`` by fetching each club's website.

Fetches the stored ``website`` for every visible, active club that is still
missing either ``description`` or ``hours``, extracts both fields via
``laughtrack.utilities.domain.club.enrichment``, and persists anything that
was parsed.  Existing non-null values are left alone so manual admin edits
are preserved; pass ``--force`` to overwrite them.

Hours pipeline:
  1. LD-JSON / meta-tag extraction from the club website (free).
  2. Google Places API fallback for clubs still missing hours after step 1 —
     fires only when ``GOOGLE_PLACES_API_KEY`` is set and the club has a
     ``city`` for query disambiguation.  Bounded by ``GOOGLE_PLACES_DAILY_LIMIT``.
     Pass ``--skip-places`` to force-disable it for a run.

Usage:
    python -m scripts.core.update_club_enrichment
    python -m scripts.core.update_club_enrichment --limit 50
    python -m scripts.core.update_club_enrichment --dry-run
    python -m scripts.core.update_club_enrichment --force --club-ids 12 34
    python -m scripts.core.update_club_enrichment --skip-places
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

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from curl_cffi.requests import AsyncSession
from psycopg2.extras import execute_values

from laughtrack.adapters.db import get_connection
from laughtrack.core.clients.google.places import GooglePlacesClient
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

    ``hours_source`` records which pipeline stage populated ``hours`` so
    the summary can split LD-JSON hits from Places fallbacks — useful
    when sanity-checking cost per nightly run.
    """

    club_id: int
    status: str  # "extracted" | "bot_blocked" | "no_data" | "fetch_failed"
    description: Optional[str] = None
    hours: Optional[Dict[str, str]] = None
    hours_source: Optional[str] = None  # "ldjson" | "places" | None


_GET_CLUBS_SQL = """
    SELECT id, name, website, city, state, hours
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


@dataclass
class _ClubTarget:
    """Row shape yielded to ``_process_club``.

    ``has_hours`` is the DB's current state — used to skip the Places
    fallback for clubs whose hours are already populated (LD-JSON
    extraction will also skip them, but we guard explicitly so a future
    re-run with ``--force`` doesn't also burn Places quota).
    """

    id: int
    name: str
    website: str
    city: Optional[str]
    state: Optional[str]
    has_hours: bool


def _load_target_clubs(
    club_ids: Optional[List[int]],
    missing_only: bool,
    limit: Optional[int],
) -> List[_ClubTarget]:
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
    return [
        _ClubTarget(
            id=r[0],
            name=r[1],
            website=r[2],
            city=r[3],
            state=r[4],
            has_hours=r[5] is not None,
        )
        for r in rows
    ]


def _places_query(name: str, city: Optional[str], state: Optional[str]) -> Optional[str]:
    """Build a text-search query string for Places.

    Requires a city (state alone doesn't disambiguate — "Comedy Club, TX"
    would surface the largest match statewide rather than the intended
    venue).  Returns ``None`` when the club lacks the geo context needed
    for a trustworthy match so the caller can skip the Places call.
    """
    name = (name or "").strip()
    city = (city or "").strip()
    state = (state or "").strip()
    if not name or not city:
        return None
    if state:
        return f"{name}, {city}, {state}"
    return f"{name}, {city}"


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
    target: _ClubTarget,
    places_client: Optional[GooglePlacesClient],
    force: bool,
) -> _ClubFetchResult:
    """Fetch + extract for a single club.

    Always returns a ``_ClubFetchResult``; callers inspect ``status`` to
    distinguish extracted data, bot-block interstitials, pages with no
    structured content, and outright fetch failures.

    When the LD-JSON extractor yields no hours and ``places_client`` is
    configured, falls back to a single Google Places text-search call.
    Places is gated on (a) the club not already having DB hours (unless
    ``--force``), and (b) a usable ``city`` for query disambiguation.
    """
    club_id, name, website = target.id, target.name, target.website
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

        status = "extracted"
        description: Optional[str] = None
        hours: Optional[Dict[str, str]] = None
        hours_source: Optional[str] = None

        if not html:
            status = "fetch_failed"
        else:
            bot_sig = _bot_block_reason(html)
            if bot_sig is not None:
                host = urlparse(website).hostname or website
                Logger.warn(
                    f"[club-enrichment] bot-blocked: {host} (club {club_id} "
                    f"'{name}', signature {bot_sig!r})",
                    context,
                )
                status = "bot_blocked"
            else:
                description = extract_description(html)
                hours = extract_hours(html)
                if hours is not None:
                    hours_source = "ldjson"

        # Places fallback — only when LD-JSON didn't already fill hours.
        # Gated on: client configured, club doesn't already have DB hours
        # (unless --force), and a disambiguating city is available.  Runs
        # even when the website fetch failed or was bot-blocked: that is
        # exactly the case Places exists to cover, and a successful Places
        # call promotes the result back to "extracted" so the recovered
        # hours land in the DB instead of being dropped.
        if (
            hours is None
            and places_client is not None
            and places_client.is_configured
            and (force or not target.has_hours)
        ):
            query = _places_query(name, target.city, target.state)
            if query is not None and places_client.calls_remaining > 0:
                places_result = await asyncio.to_thread(places_client.fetch_hours, query)
                if places_result.hours:
                    hours = places_result.hours
                    hours_source = "places"
                    status = "extracted"

        if status == "extracted" and description is None and hours is None:
            status = "no_data"

        if status in ("fetch_failed", "bot_blocked", "no_data"):
            return _ClubFetchResult(club_id=club_id, status=status)

        return _ClubFetchResult(
            club_id=club_id,
            status="extracted",
            description=description,
            hours=hours,
            hours_source=hours_source,
        )


async def _enrich(
    targets: List[_ClubTarget],
    *,
    force: bool,
    dry_run: bool,
    places_client: Optional[GooglePlacesClient],
) -> Dict[str, int]:
    semaphore = asyncio.Semaphore(_CONCURRENCY)
    async with AsyncSession(impersonate="chrome124", timeout=_TIMEOUT_SECONDS) as session:
        try:
            extracted = await asyncio.gather(
                *(
                    _process_club(session, semaphore, target, places_client, force)
                    for target in targets
                )
            )
        finally:
            # Release the shared Playwright singleton on the same loop that
            # created it — mirrors the scraper fleet's teardown pattern.
            await close_js_browser()

    rows: List[Tuple[int, Optional[str], Optional[str]]] = []
    desc_hits = 0
    hours_hits = 0
    hours_from_ldjson = 0
    hours_from_places = 0
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
            if result.hours_source == "ldjson":
                hours_from_ldjson += 1
            elif result.hours_source == "places":
                hours_from_places += 1
        rows.append(
            (
                result.club_id,
                result.description,
                json.dumps(result.hours) if result.hours else None,
            )
        )

    places_calls = places_client.calls_made if places_client else 0

    Logger.info(
        f"[club-enrichment] extracted from {len(rows)}/{len(targets)} clubs — "
        f"description={desc_hits}, hours={hours_hits} "
        f"(ldjson={hours_from_ldjson}, places={hours_from_places}), "
        f"bot_blocked={bot_blocked}, places_calls={places_calls}"
    )

    summary = {
        "fetched": len(targets),
        "extracted": len(rows),
        "description_hits": desc_hits,
        "hours_hits": hours_hits,
        "hours_from_ldjson": hours_from_ldjson,
        "hours_from_places": hours_from_places,
        "places_calls": places_calls,
        "bot_blocked": bot_blocked,
        "written": 0,
    }

    if dry_run:
        Logger.info("[club-enrichment] --dry-run: skipping DB write")
        return summary

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

    summary["written"] = written
    return summary


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
    parser.add_argument(
        "--skip-places",
        action="store_true",
        help=(
            "Disable the Google Places API fallback for clubs with no LD-JSON hours. "
            "Default behaviour: Places fires when GOOGLE_PLACES_API_KEY is set. "
            "Daily request ceiling is controlled by GOOGLE_PLACES_DAILY_LIMIT."
        ),
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
    missing_only = not (args.all or args.force or args.club_ids)

    targets = _load_target_clubs(
        club_ids=args.club_ids,
        missing_only=missing_only,
        limit=args.limit,
    )

    places_client: Optional[GooglePlacesClient] = None
    if not args.skip_places:
        candidate = GooglePlacesClient()
        if candidate.is_configured:
            places_client = candidate
            Logger.info(
                f"[club-enrichment] Places fallback enabled "
                f"(daily_limit={candidate.calls_remaining})"
            )
        else:
            Logger.info(
                "[club-enrichment] Places fallback disabled — "
                "GOOGLE_PLACES_API_KEY not set"
            )

    Logger.info(
        f"[club-enrichment] {len(targets)} clubs eligible "
        f"(missing_only={missing_only}, force={args.force}, "
        f"dry_run={args.dry_run}, places={'on' if places_client else 'off'})"
    )
    if not targets:
        empty_summary = {
            "fetched": 0,
            "extracted": 0,
            "description_hits": 0,
            "hours_hits": 0,
            "hours_from_ldjson": 0,
            "hours_from_places": 0,
            "places_calls": 0,
            "bot_blocked": 0,
            "written": 0,
        }
        print(json.dumps(empty_summary))
        if args.summary_out:
            Path(args.summary_out).write_text(json.dumps(empty_summary), encoding="utf-8")
        return

    try:
        summary = asyncio.run(
            _enrich(
                targets,
                force=args.force,
                dry_run=args.dry_run,
                places_client=places_client,
            )
        )
    except KeyboardInterrupt:
        Logger.info("[club-enrichment] cancelled by user")
        sys.exit(130)
    except Exception as exc:
        Logger.error(f"[club-enrichment] failed: {exc}")
        sys.exit(1)

    # Short JSON summary on stdout for programmatic callers (nightly workflow).
    print(json.dumps(summary))
    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
