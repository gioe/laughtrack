"""Read-only live organizer accounting, routing and preservation audit (TASK-4126).

Run from apps/scraper with PYTHONPATH=src:. and --output /absolute/report.json.
The real client and organizer pipeline execute; persistence never does.
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import re
import secrets
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql
from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from laughtrack.core.clients.eventbrite.client import EventbriteClient
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics,
    bind_diagnostics,
    reset_diagnostics,
)
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
from scripts.core.repair_annoyance_identity import CHILDREN


def event_id(url):
    match = re.search(r"(?:-|/)(\d+)$", urlparse(url).path.rstrip("/"))
    if not match:
        raise ValueError("Missing numeric event identifier")
    return match.group(1)


def snapshot(conn, ids, secret):
    """Full rows participate in keyed hashes; private child records never leave memory.

    READ COMMITTED obtains a new snapshot for each statement. A single UNION
    statement keeps the tables internally consistent at each observation.
    """
    tables = ("shows", *CHILDREN)
    queries = [
        sql.SQL("SELECT %s AS table_name, to_jsonb(t) AS row FROM {} t WHERE {} = ANY(%s)").format(
            sql.Identifier(table), sql.Identifier("id" if table == "shows" else "show_id")
        )
        for table in tables
    ]
    params = [value for table in tables for value in (table, ids)]
    with conn.cursor() as cursor:
        cursor.execute(sql.SQL(" UNION ALL ").join(queries), params)
        grouped = {table: [] for table in tables}
        for table, row in cursor.fetchall():
            grouped[table].append(row)
    fingerprints = {}
    for table, rows in grouped.items():
        canonical = "\n".join(sorted(json.dumps(row, sort_keys=True) for row in rows))
        fingerprints[table] = {
            "count": len(rows),
            "all_columns_hmac_sha256": hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest(),
        }
    return {
        "tables": fingerprints,
        "shows": sorted(grouped["shows"], key=lambda row: row["id"]),
    }


def cleanup_simulations(shows, diagnostics, now):
    cap = ScrapingResultProcessor._reconcile_delete_cap()
    rows = []
    for synthetic in (False, True):
        for count in sorted({1, max(1, cap - 1), max(1, cap)}):
            processor = object.__new__(ScrapingResultProcessor)
            processor.show_service = MagicMock()
            processor.organizer_venue_handler = MagicMock()
            processor.show_service.count_stale_future_shows.return_value = count
            processor.show_service.count_stale_future_shows_by_organizer.return_value = count
            result = ClubScrapingResult(
                club_name="Attic",
                club_id=575,
                shows=shows,
                execution_time=0,
                scraper_key="eventbrite",
                fetches_ok=max(1, diagnostics.fetches_ok),
                fetches_failed=0,
                error=None,
                bot_block_detected=False,
                is_synthetic=synthetic,
                production_company_id=42 if synthetic else None,
            )
            processor._reconcile_stale_future_shows(result, now)
            calls = processor.show_service.mock_calls + processor.organizer_venue_handler.mock_calls
            if calls:
                raise AssertionError("Eventbrite absence cleanup reached persistence spies")
            rows.append(
                {
                    "synthetic": synthetic,
                    "candidate_count": count,
                    "configured_cap": cap,
                    "positive_success_counter": result.fetches_ok,
                    "clean_diagnostics_gate": processor._is_clean_for_reconciliation(result),
                    "persistence_calls": 0,
                    "simulation_only": True,
                }
            )
    return rows


async def verify(conn, original_rows):
    ids = [row["id"] for row in original_rows]
    secret = secrets.token_bytes(32)  # Intentionally discarded; prevents guessing private values.
    before = snapshot(conn, ids, secret)
    if len(before["shows"]) != 16:
        raise AssertionError("Original unresolved cohort no longer has 16 rows")
    handler = ClubHandler()
    original_execute = handler.execute_with_cursor
    refused = []
    selects = []

    def reject(*args, **kwargs):
        refused.append(True)
        raise AssertionError("Production write fallback or secondary connection refused")

    def execute(operation, params=None, return_results=False, **kwargs):
        if not operation.lstrip().upper().startswith("SELECT"):
            return reject()
        selects.append(True)
        return original_execute(operation, params, return_results, conn=conn)

    handler.execute_with_cursor = execute
    handler.create_connection = reject
    handler.upsert_for_eventbrite_venue = reject
    attic, walrus = handler.get_club_by_id(575), handler.get_club_by_id(29044)
    if not attic or not walrus or attic.id == walrus.id:
        raise AssertionError("Attic and Walrus must remain distinct existing venues")
    if attic.eventbrite_id != "113948356841" or "/o/" not in attic.scraping_url:
        raise AssertionError("Organizer configuration changed")
    scraper = object.__new__(EventbriteScraper)
    scraper._club, scraper._club_handler = attic, handler
    scraper.logger_context = attic.as_context()
    client = EventbriteClient(attic)
    scraper.eventbrite_client = client
    original_fetch = client.fetch_organizer_event_list
    passes = []
    try:
        for iteration in (1, 2):
            source_rows, pages = [], []

            async def observe_page(*args, **kwargs):
                response = await original_fetch(*args, **kwargs)
                if response is None:
                    raise AssertionError("Live page fetch failed; no completeness claim possible")
                pages.append({"events": len(response.events), "has_more_items": response.pagination.has_more_items})
                for api_event in response.events:
                    event = EventbriteEvent.from_api_model(api_event)
                    source_rows.append(
                        {"event_id": str(api_event.id), "venue_id": str(event.venue_id), "utc_start": event.start_date}
                    )
                return response

            client.fetch_organizer_event_list = observe_page
            diagnostics = ScrapeDiagnostics()
            token = bind_diagnostics(diagnostics)
            try:
                with patch("psycopg2.connect", side_effect=reject):
                    shows = await scraper._scrape_organizer_async()
            finally:
                reset_diagnostics(token)
            if refused or not pages or pages[-1]["has_more_items"]:
                raise AssertionError("Read-only complete source refresh not established")
            if diagnostics.fetches_ok != len(pages) or diagnostics.fetches_failed or diagnostics.scrape_errors:
                raise AssertionError("Actual bound diagnostics do not account for every successful page")
            source = {row["event_id"]: row for row in source_rows}
            if len(source) != len(source_rows):
                raise AssertionError("Duplicate source event IDs")
            routed = []
            for show in shows:
                identifier = event_id(show.show_page_url)
                row = source[identifier]
                actual = show.date.astimezone(timezone.utc)
                if actual != datetime.fromisoformat(row["utc_start"].replace("Z", "+00:00")):
                    raise AssertionError("Source instant changed during routing")
                routed.append(
                    {
                        "event_id": identifier,
                        "venue_id": row["venue_id"],
                        "club_id": show.club_id,
                        "utc_start": actual.isoformat(),
                    }
                )
            if len(routed) != len(source_rows):
                raise AssertionError("Unexpected filtering during source routing")
            passes.append(
                {
                    "iteration": iteration,
                    "pages": pages,
                    "source_event_count": len(source_rows),
                    "diagnostics": {
                        key: getattr(diagnostics, key)
                        for key in (
                            "fetches_ok",
                            "fetches_failed",
                            "http_status",
                            "bot_block_detected",
                            "scrape_errors",
                        )
                    },
                    "routed_club_counts": dict(Counter(str(row["club_id"]) for row in routed)),
                    "routed_events": sorted(routed, key=lambda row: row["event_id"]),
                    "original_rows": [
                        {
                            "show_id": row["id"],
                            "event_id": event_id(row["show_page_url"]),
                            "source_status": (
                                "present" if event_id(row["show_page_url"]) in source else "absent_unconfirmed"
                            ),
                        }
                        for row in original_rows
                    ],
                    "cleanup_simulations": cleanup_simulations(shows, diagnostics, datetime.now(timezone.utc)),
                }
            )
    finally:
        await client.cleanup()
    after = snapshot(conn, ids, secret)
    return {
        "passes": passes,
        "before": before,
        "after": after,
        "all_show_fields_and_children_unchanged": before == after,
        "repeated_inventory_and_routing_equal": passes[0]["routed_events"] == passes[1]["routed_events"],
        "handler_select_calls": len(selects),
        "production_writes": 0,
        "show_persistence_calls": 0,
        "refused_write_attempts": len(refused),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    env = dotenv_values(ROOT / ".env")
    evidence = json.loads((ROOT / "docs/audits/2026-09-24-same-city/source-evidence.json").read_text())
    rows = evidence["attic_unresolved"]["unresolved_rows"]
    if len(rows) != 16 or len({event_id(row["show_page_url"]) for row in rows}) != 11:
        raise AssertionError("Original unresolved cohort changed")
    conn = psycopg2.connect(
        host=env["DATABASE_HOST"],
        user=env["DATABASE_USER"],
        password=env["DATABASE_PASSWORD"],
        dbname=env["DATABASE_NAME"],
        port=env.get("DATABASE_PORT", "5432"),
        sslmode="require",
    )
    conn.set_session(readonly=True, isolation_level="READ COMMITTED")
    try:
        result = asyncio.run(verify(conn, rows))
    finally:
        conn.rollback()
        conn.close()
    result.update(
        {
            "task_id": 4126,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "transaction": "READ COMMITTED, read only, rolled back and closed",
            "fingerprints": "Full-row HMAC-SHA256 with ephemeral key discarded after run; compare only within this artifact. Child rows contain private data and are not exported.",
            "limitations": [
                "Live/public source absence does not establish cancellation or safe deletion.",
                "Read-only routing verification does not prove production persistence idempotence.",
                "Snapshots detect net visible changes between observations, not transient changes reversed between them.",
            ],
        }
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({key: value for key, value in result.items() if key not in ("passes", "before", "after")}, indent=2)
    )
    if not result["all_show_fields_and_children_unchanged"]:
        raise SystemExit("External inventory/reference changes detected; inspect report")


if __name__ == "__main__":
    main()
