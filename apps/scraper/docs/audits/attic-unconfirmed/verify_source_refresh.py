"""Read-only live Eventbrite refresh and venue-routing verification for TASK-4079.

From apps/scraper:
  PYTHONPATH=src:. .venv/bin/python docs/audits/attic-unconfirmed/verify_source_refresh.py

Fetches the complete public/live organizer inventory twice, then exercises the
real organizer routing with SELECT-only venue lookups in a read-only transaction.
Every upsert fallback is refused. This does not persist shows or prove production
persistence idempotence. Missing events remain unconfirmed, never canceled.
Only public event/venue identifiers and aggregate database facts are exported.
"""

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlparse

import psycopg2
from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from laughtrack.core.clients.eventbrite.client import EventbriteClient
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics, bind_diagnostics, reset_diagnostics,
)
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor


def event_id(url):
    match = re.search(r"(?:-|/)(\d+)$", urlparse(url).path.rstrip("/"))
    if not match:
        raise ValueError("An Eventbrite event URL lacked its numeric identifier")
    return match.group(1)


async def fetch_inventory(client):
    """Fail closed on incomplete pagination instead of treating failure as absence."""
    events, source_rows, seen_continuations = [], [], set()
    continuation = None
    pages = 0
    while True:
        response = await client.fetch_organizer_event_list(
            organizer_id="113948356841", continuation=continuation
        )
        if response is None:
            raise RuntimeError("Organizer refresh failed; absence cannot be assessed")
        pages += 1
        for api_event in response.events:
            event = EventbriteEvent.from_api_model(api_event)
            events.append(event)
            source_rows.append({
                "event_id": str(api_event.id),
                "venue_id": str(event.venue_id),
                "utc_start": event.start_date,
            })
        if not response.pagination.has_more_items:
            break
        continuation = response.pagination.continuation
        if not continuation or continuation in seen_continuations or not response.events:
            raise RuntimeError("Incomplete or repeating organizer pagination")
        seen_continuations.add(continuation)
    if len({row["event_id"] for row in source_rows}) != len(source_rows):
        raise RuntimeError("Duplicate source event IDs require manual review")
    return events, source_rows, pages


async def verify(conn, original_rows):
    handler = ClubHandler()
    original_execute = handler.execute_with_cursor
    select_calls = []
    refused_writes = []

    def execute(operation, params=None, return_results=False, **kwargs):
        if not operation.lstrip().upper().startswith("SELECT"):
            raise AssertionError("Verification permits SELECT statements only")
        select_calls.append(1)
        return original_execute(operation, params, return_results, conn=conn)

    def reject(*args, **kwargs):
        refused_writes.append(1)
        raise AssertionError("Write fallback or secondary database connection refused")

    handler.execute_with_cursor = execute
    handler.create_connection = reject
    handler.upsert_for_eventbrite_venue = reject
    def snapshot():
        # Export only show identity/status; never user-reference rows.
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, club_id, date, is_cancelled, last_scraped_date "
                "FROM shows WHERE id = ANY(%s) ORDER BY id",
                ([row["id"] for row in original_rows],),
            )
            return [{
                "show_id": row[0], "club_id": row[1], "utc_start": row[2].isoformat(),
                "is_cancelled": row[3],
                "last_scraped_date": row[4].isoformat() if row[4] else None,
            } for row in cursor.fetchall()]

    before = snapshot()
    now = datetime.now(timezone.utc)
    future_count = sum(
        datetime.fromisoformat(row["utc_start"]) > now and not row["is_cancelled"]
        for row in before
    )
    attic = handler.get_club_by_id(575)
    walrus = handler.get_club_by_id(29044)
    if not attic or not walrus or attic.id == walrus.id:
        raise AssertionError("The distinct Attic and Walrus venue identities must exist")
    if attic.eventbrite_id != "113948356841" or "/o/" not in attic.scraping_url:
        raise AssertionError("Attic organizer configuration changed; review before replay")
    scraper = object.__new__(EventbriteScraper)
    scraper._club = attic
    scraper._club_handler = handler
    scraper.logger_context = attic.as_context()
    client = EventbriteClient(attic)
    passes = []
    try:
        for iteration in (1, 2):
            diagnostics = ScrapeDiagnostics()
            token = bind_diagnostics(diagnostics)
            try:
                events, source_rows, pages = await fetch_inventory(client)
                scraper.eventbrite_client = SimpleNamespace(
                    fetch_all_events=AsyncMock(return_value=events)
                )
                shows = await scraper._scrape_organizer_async()
            finally:
                reset_diagnostics(token)
            if refused_writes:
                raise AssertionError("Unresolved venue required forbidden write fallback")
            source_by_id = {row["event_id"]: row for row in source_rows}
            routed = []
            for show in shows:
                identifier = event_id(show.show_page_url)
                source = source_by_id[identifier]
                actual_date = show.date.astimezone(timezone.utc)
                source_date = datetime.fromisoformat(source["utc_start"].replace("Z", "+00:00"))
                if actual_date != source_date:
                    raise AssertionError("Source start time changed during conversion")
                routed.append({
                    "event_id": identifier,
                    "venue_id": source["venue_id"],
                    "club_id": show.club_id,
                    "utc_start": actual_date.isoformat(),
                })
            # Unexpected filtering must be reviewed rather than hidden in counts.
            if len(routed) != len(events):
                raise AssertionError("Source events were omitted during venue routing")
            # Exercise the real guard with fake persistence methods only. This
            # is deliberately not a production cleanup or ShowService call.
            processor = object.__new__(ScrapingResultProcessor)
            processor.show_service = MagicMock()
            processor.show_service.count_stale_future_shows.return_value = future_count
            result = ClubScrapingResult(
                club_name=attic.name, club_id=attic.id, shows=shows,
                execution_time=0, scraper_key="eventbrite",
                fetches_ok=diagnostics.fetches_ok, fetches_failed=diagnostics.fetches_failed,
                error=None, bot_block_detected=diagnostics.bot_block_detected,
            )
            processor._reconcile_stale_future_shows(result, now)
            cleanup = {
                "simulation_only": True,
                "clean_gate": processor._is_clean_for_reconciliation(result),
                "count_called": processor.show_service.count_stale_future_shows.called,
                "delete_called": processor.show_service.delete_stale_future_shows.called,
                "unresolved_future_rows": future_count,
                "configured_cap": processor._reconcile_delete_cap(),
            }
            passes.append({
                "iteration": iteration,
                "pages": pages,
                "source_event_count": len(events),
                "diagnostics": {
                    "http_status": diagnostics.http_status,
                    "fetches_ok": diagnostics.fetches_ok,
                    "fetches_failed": diagnostics.fetches_failed,
                    "bot_block_detected": diagnostics.bot_block_detected,
                },
                "cleanup_guard_replay": cleanup,
                "routed_club_counts": dict(Counter(str(row["club_id"]) for row in routed)),
                "routed_events": sorted(routed, key=lambda row: row["event_id"]),
                "original_rows": [{
                    "show_id": row["id"],
                    "event_id": event_id(row["show_page_url"]),
                    "current_public_live_inventory": (
                        "present" if event_id(row["show_page_url"]) in source_by_id else "absent_unconfirmed"
                    ),
                } for row in original_rows],
            })
    finally:
        await client.cleanup()
    after = snapshot()
    return {
        "passes": passes,
        "repeated_inventory_and_routing_equal": passes[0]["routed_events"] == passes[1]["routed_events"],
        "handler_select_calls": len(select_calls),
        "production_writes": 0,
        "show_persistence_calls": 0,
        "distinct_venue_ids": [attic.id, walrus.id],
        "unresolved_rows_before": before,
        "unresolved_rows_after": after,
        "unresolved_rows_unchanged": before == after,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify Attic organizer source routing without production writes")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("refresh-verification.json"))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    env = dotenv_values(ROOT / ".env")
    evidence = json.loads((ROOT / "docs/audits/2026-09-24-same-city/source-evidence.json").read_text())
    rows = evidence["attic_unresolved"]["unresolved_rows"]
    if len(rows) != 16 or len({event_id(row["show_page_url"]) for row in rows}) != 11:
        raise AssertionError("Original unresolved cohort changed")
    conn = psycopg2.connect(
        host=env["DATABASE_HOST"], user=env["DATABASE_USER"], password=env["DATABASE_PASSWORD"],
        dbname=env["DATABASE_NAME"], port=env.get("DATABASE_PORT", "5432"), sslmode="require",
    )
    conn.set_session(readonly=True)
    try:
        result = asyncio.run(verify(conn, rows))
    finally:
        conn.rollback()
        conn.close()
    result.update({
        "task_id": 4079,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "read_only_transaction_closed": True,
        "scope": "Two complete live API reads through real API/domain parsers and organizer routing; venue lookups only, no show persistence.",
        "return_policy": "Route by each current source venue; do not permanently remap Attic to Walrus. A future Oak Street venue is resolved independently.",
        "limitations": [
            "Public/live inventory absence does not distinguish cancellation, privacy, rescheduling or unavailability.",
            "This proves source routing, not production persistence idempotence or a future venue-return payload.",
            "A changed inventory between refreshes is reported, not assumed to be a routing defect.",
        ],
    })
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        key: value for key, value in result.items()
        if key not in ("passes", "unresolved_rows_before", "unresolved_rows_after")
    }, indent=2))


if __name__ == "__main__":
    main()
