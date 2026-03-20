import asyncio
from types import SimpleNamespace
from typing import Any, List, Dict
import pytest

# Import the real class under test
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.scraper import (
    BroadwayComedyClubScraper,
)
from laughtrack.core.entities.event.broadway import BroadwayEvent


class FakeEnricher:
    """Mimics TesseraTicketBatchEnricher.enrich by enriching select events.

    outcome_map: id -> list (enrich) or missing/None (skip)
    """

    def __init__(self, outcome_map: Dict[str, Any] | None = None):
        self.outcome_map = outcome_map or {}
        self.called = False
        self.last_ids: List[str] = []

    async def enrich(self, events, is_tessera, event_id, show_url):
        self.called = True
        # Track ids of tessera-eligible events passed
        self.last_ids = [event_id(e) for e in events if is_tessera(e) and event_id(e)]
        enriched: List = []
        for e in events:
            if is_tessera(e):
                eid = event_id(e)
                if eid and isinstance(self.outcome_map.get(eid), list):
                    # Attach a simple list to mimic _ticket_data presence
                    setattr(e, "_ticket_data", list(self.outcome_map[eid]))
            enriched.append(e)
        return enriched


class FakeScraper(BroadwayComedyClubScraper):
    def __init__(self, enricher: FakeEnricher | None = None):  # Don't call super(); keep it lean for unit tests
        # Minimal context expected by logging helpers
        self.logger_context = {"scraper": "broadway", "club": "TEST"}
        # Provide the fake enricher used by the scraper's enrichment flow
        self._tickets = enricher or FakeEnricher()


def make_event(
    *,
    id: str | None,
    is_tessera: bool,
    main_artist: List[str] | None = None,
    event_date: str | None = None,
) -> BroadwayEvent:
    # BroadwayEvent.from_dict applies sensible defaults
    data = {
        "id": id,
        "isTesseraProduct": is_tessera,
        "mainArtist": main_artist or [],
        "eventDate": event_date or "2025-08-30 08:00 PM",
    }
    return BroadwayEvent.from_dict(data)


def test_select_tessera_event_ids_filters_and_dedupes():
    s = FakeScraper()
    events = [
        make_event(id="a", is_tessera=True, main_artist=["A"], event_date="2025-08-30"),
        make_event(id="a", is_tessera=True, main_artist=["A"], event_date="2025-08-30"),  # duplicate
        make_event(id="b", is_tessera=False, main_artist=["B"], event_date="2025-08-31"),  # excluded
        make_event(id=None, is_tessera=True, main_artist=["C"], event_date="2025-09-01"),   # missing id
    ]
    ids = s._select_tessera_event_ids(events)
    assert ids == ["a"], "Should return deduped list of accepted IDs only"


@pytest.mark.asyncio
async def test_enricher_used_and_enriches_expected_events():
    # Setup fake enricher that enriches only 'good' ids
    enricher = FakeEnricher({
        "good": [SimpleNamespace(kind="ticket")],
    })
    s = FakeScraper(enricher)

    events = [
        make_event(id="good", is_tessera=True, main_artist=["G"]),
        make_event(id="bad", is_tessera=True, main_artist=["B"]),
    ]

    enriched = await s._enrich_events_with_tickets(events)

    # Enricher should have been called and tracked eligible ids
    assert enricher.called is True
    assert set(enricher.last_ids) == {"good", "bad"}

    # Only 'good' event should survive — 'bad' is a Tessera event with no ticket data and is excluded
    ids_in_output = {e.id for e in enriched}
    assert "good" in ids_in_output
    assert "bad" not in ids_in_output, "Tessera event with failed enrichment must be excluded"
    emap = {e.id: e for e in enriched}
    assert _has_ticket_data(emap["good"]) and len(getattr(emap["good"], "_ticket_data") or []) == 1


def _has_ticket_data(e):
    return hasattr(e, "_ticket_data") and isinstance(e._ticket_data, list)


@pytest.mark.asyncio
async def test_enrich_end_to_end_happy_and_skip_paths():
    # Enricher that enriches only id 'a', skips 'x'
    enricher = FakeEnricher({
        "a": [SimpleNamespace(kind="ticket", note="ok1")],
    })
    s = FakeScraper(enricher)

    # Prepare events: two Tessera candidates (one skipped), one non-tessera, one missing id
    events = [
        make_event(id="a", is_tessera=True, main_artist=["A"]),
        make_event(id="x", is_tessera=True, main_artist=["X"]),
        make_event(id="n", is_tessera=False, main_artist=["N"]),
        make_event(id=None, is_tessera=True, main_artist=["M"]),
    ]

    enriched = await s._enrich_events_with_tickets(events)

    # 'a' enriched — survives filter; 'x' and missing-id tessera events fail enrichment — excluded
    # 'n' is non-tessera — always passes through regardless of ticket data
    ids_in_output = {e.id for e in enriched}
    assert "a" in ids_in_output, "Successfully enriched Tessera event must be included"
    assert "x" not in ids_in_output, "Tessera event with failed enrichment must be excluded"
    assert "n" in ids_in_output, "Non-tessera event must pass through regardless"
    assert "" not in ids_in_output, "Tessera event with missing id and no ticket data must be excluded"

    e_map = {e.id: e for e in enriched}
    assert _has_ticket_data(e_map["a"]) and len(getattr(e_map["a"], "_ticket_data") or []) == 1
    assert not _has_ticket_data(e_map["n"])  # non-tessera, no ticket data expected


@pytest.mark.asyncio
async def test_tessera_event_with_none_ticket_data_not_in_shows():
    """Criterion 1611: event with None ticket data must not appear in the returned shows list."""
    # Enricher returns no data for stale event '20083' — simulates _fetch_ticket_data() → None
    enricher = FakeEnricher({
        "ok": [SimpleNamespace(kind="ticket")],
        # '20083' deliberately absent — enricher leaves _ticket_data as None
    })
    s = FakeScraper(enricher)

    events = [
        make_event(id="ok", is_tessera=True, main_artist=["Good Comic"]),
        make_event(id="20083", is_tessera=True, main_artist=["Stale Event"]),
    ]

    result = await s._enrich_events_with_tickets(events)

    result_ids = [e.id for e in result]
    assert "ok" in result_ids, "Successfully enriched event must be present"
    assert "20083" not in result_ids, "Stale Tessera event with no ticket data must be excluded"
