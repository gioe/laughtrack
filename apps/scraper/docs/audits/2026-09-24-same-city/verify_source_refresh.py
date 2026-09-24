"""Read-only replay of captured routing fields, not a network scrape or persistence test.

Run from apps/scraper:
 PYTHONPATH=src:. .venv/bin/python docs/audits/2026-09-24-same-city/verify_source_refresh.py
Uses docs/audits/2026-09-24-same-city/source-evidence.json and writes refresh-verification.json.
The PostgreSQL transaction is explicitly read-only; all upsert fallbacks raise.
"""

import asyncio, json, sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import psycopg2
from dotenv import dotenv_values

root = Path.cwd()
sys.path[:0] = [str(root / "src"), str(root)]
from laughtrack.core.clients.eventbrite.models import EventbriteEvent as ApiEvent
from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.clients.ticketmaster.client import TicketmasterClient
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper

folder = root / "docs/audits/2026-09-24-same-city"
evidence = json.loads((folder / "source-evidence.json").read_text())
prior_path = folder / "refresh-verification.json"
prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
tm_inputs = prior["captured_ticketmaster_inputs"]
v = dotenv_values(root / ".env")
conn = psycopg2.connect(
    host=v["DATABASE_HOST"],
    user=v["DATABASE_USER"],
    password=v["DATABASE_PASSWORD"],
    dbname=v["DATABASE_NAME"],
    sslmode="require",
)
conn.set_session(readonly=True)
handler = ClubHandler()
original = handler.execute_with_cursor
queries = []


def execute(operation, params=None, return_results=False, **kwargs):
    if not operation.lstrip().upper().startswith("SELECT"):
        raise AssertionError("Replay permits SELECT SQL only")
    queries.append({"parameters": params})
    return original(operation, params, return_results, conn=conn)


def reject(*args, **kwargs):
    raise AssertionError("A write or secondary database connection was attempted")


handler.execute_with_cursor = execute
handler.create_connection = reject
handler.upsert_for_eventbrite_venue = reject
out = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "scope": "Repeated captured source-field replay through Eventbrite API/domain parsers and real organizer routing with real read-only ClubHandler lookup; Ticketmaster real stable-ID lookup and create_show conversion. No show persistence, migration, live fetch, or full pipeline.",
    "limitations": [
        "Captured Eventbrite evidence contains routing/date/name/status fields, not complete API pricing/classification payloads. This verifies identity/time routing, not admission or pricing.",
        "AsyncMock substitutes fetch_all_events with captured parsed events; actual organizer pagination/network behavior is not exercised.",
        "TM create_show is exercised after real stable-ID resolution; national upsert/write paths are not invoked.",
        "Repeated outputs show deterministic correct routing, not production persistence idempotence.",
    ],
    "passes": [],
    "captured_ticketmaster_inputs": tm_inputs,
}
try:
    attic = handler.get_club_by_id(575)
    assert attic and attic.scraping_url == "https://www.eventbrite.com/o/the-attic-comedy-club-113948356841"
    scraper = object.__new__(EventbriteScraper)
    scraper._club = attic
    scraper._club_handler = handler
    scraper.logger_context = attic.as_context()
    assert scraper._is_organizer_mode

    async def run():
        for iteration in (1, 2):
            parsed = [EventbriteEvent.from_api_model(ApiEvent.from_json_dict(e)) for e in evidence["eventbrite_events"]]
            scraper.eventbrite_client = SimpleNamespace(fetch_all_events=AsyncMock(return_value=parsed))
            shows = await scraper._scrape_organizer_async()
            assert len(shows) == 41, len(shows)
            source_by_url = {e["url"]: e for e in evidence["eventbrite_events"]}
            eb = []
            for s in shows:
                source = source_by_url[s.show_page_url]
                actual = s.date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                assert s.club_id == 29044, (s.name, s.club_id)
                assert actual == source["start"]["utc"], (actual, source["start"])
                eb.append({"event_id": source["id"], "club_id": s.club_id, "utc_start": actual})
            tm = []
            for e in tm_inputs:
                if e["id"] not in ("Z7r9jZ1A70taU", "Z7r9jZ1A7Opvx"):
                    continue
                venue = e["_embedded"]["venues"][0]
                club = handler._find_ticketmaster_id_match(venue["id"])
                assert club and club.id == 9650
                show = TicketmasterClient(club, api_key="unused-offline-replay").create_show(e)
                assert show and show.club_id == 9650
                actual = show.date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                assert actual == e["dates"]["start"]["dateTime"]
                tm.append({"event_id": e["id"], "venue_id": venue["id"], "club_id": show.club_id, "utc_start": actual})
            assert len(tm) == 2
            out["passes"].append({"iteration": iteration, "eventbrite": eb, "ticketmaster": tm})

    asyncio.run(run())
    assert out["passes"][0]["eventbrite"] == out["passes"][1]["eventbrite"]
    assert out["passes"][0]["ticketmaster"] == out["passes"][1]["ticketmaster"]
    out["passed"] = True
    out["sql_select_calls"] = len(queries)
    out["upsert_calls"] = 0
    out["show_persistence_calls"] = 0
finally:
    conn.rollback()
    conn.close()
    out["read_only_transaction_closed"] = True
    (folder / "refresh-verification.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({k: val for k, val in out.items() if k not in ("passes", "captured_ticketmaster_inputs")}, indent=2))
