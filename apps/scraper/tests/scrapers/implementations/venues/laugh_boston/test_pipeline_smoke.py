"""
Smoke tests for the Laugh Boston scraper pipeline.

Verifies that get_data() returns LaughBostonPageData with at least one event
when the Pixl Calendar API returns events.

The scraper now parses TixrEvent objects directly from the Pixl API response
without fetching individual Tixr pages (no tixr_client attribute).
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.venues.laugh_boston.scraper import LaughBostonScraper
from laughtrack.scrapers.implementations.venues.laugh_boston.page_data import LaughBostonPageData

GROUP_URL = "https://laughboston.com"
EVENT_URL = "https://www.tixr.com/groups/laughboston/events/comedy-night-12345"


def _club() -> Club:
    return Club(
        id=999,
        name="Laugh Boston",
        address="425 Summer St",
        website="https://laughboston.com",
        scraping_url=GROUP_URL,
        popularity=0,
        zip_code="02210",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _tixr_event() -> TixrEvent:
    show = Show(
        name="Comedy Night at Laugh Boston",
        club_id=999,
        date=datetime(2026, 4, 4, 19, 0, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
        lineup=[],
        tickets=[Ticket(price=30.0, purchase_url=EVENT_URL, sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone="America/New_York",
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=EVENT_URL, event_id="12345")


def _pixl_response() -> dict:
    """Pixl Calendar API response with a complete event record."""
    return {
        "events": [
            {
                "id": "abc-123",
                "title": "Comedy Night",
                "start": "2026-04-04T23:00:00.000Z",
                "timezone": "America/New_York",
                "ticketUrl": EVENT_URL,
                "status": "available",
                "sales": [{"name": "General Admission", "currentPrice": 30, "state": "OPEN"}],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns LaughBostonPageData with at least one TixrEvent
    when the Pixl Calendar API returns events with complete event data.
    Events are built directly from the Pixl response — no Tixr page fetches.
    """
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_json",
        AsyncMock(return_value=_pixl_response()),
    )

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, LaughBostonPageData), (
        "get_data() did not return LaughBostonPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid Pixl Calendar response — "
        "check parse_events_from_pixl() in extractor"
    )
    assert result.tixr_urls == [EVENT_URL]


@pytest.mark.asyncio
async def test_get_data_returns_none_when_api_fails(monkeypatch):
    """get_data() returns None when the Pixl Calendar API fetch fails (returns None)."""
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_json",
        AsyncMock(return_value=None),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_urls(monkeypatch):
    """get_data() returns None when the Pixl Calendar response contains no events."""
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_json",
        AsyncMock(return_value={"events": []}),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_events_malformed(monkeypatch):
    """get_data() returns None when all Pixl events are missing required fields."""
    scraper = LaughBostonScraper(_club())

    # Events with no 'start' field cannot be parsed into TixrEvents
    monkeypatch.setattr(
        scraper,
        "fetch_json",
        AsyncMock(return_value={"events": [{"id": "x", "title": "Bad Event", "ticketUrl": EVENT_URL}]}),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_fetch_exception_gracefully(monkeypatch):
    """get_data() returns None when the Pixl Calendar API raises an exception."""
    scraper = LaughBostonScraper(_club())

    async def raise_error(*_args, **_kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(scraper, "fetch_json", raise_error)

    result = await scraper.get_data(GROUP_URL)
    assert result is None


def test_can_transform_accepts_tixr_event():
    """
    Transformation pipeline accepts TixrEvent — catches type-mismatch regressions
    where the transformer's can_transform() silently rejects all events.
    """
    scraper = LaughBostonScraper(_club())
    event = _tixr_event()
    page_data = LaughBostonPageData(event_list=[event], tixr_urls=[EVENT_URL])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert shows is not None and len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 shows for a valid TixrEvent — "
        "check LaughBostonEventTransformer.can_transform()"
    )
