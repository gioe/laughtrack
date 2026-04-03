"""
Smoke tests for The Comedy Inn (Miami, FL) using EventbriteScraper.

Verifies that the EventbriteScraper pipeline works correctly for The Comedy Inn's
organizer ID (3390989926) — a 10-digit Eventbrite organizer ID that the client
automatically routes to the /organizers/{id}/events/ endpoint.

Catches regressions where:
- get_data() silently returns None despite a valid organizer ID
- The transformation pipeline drops events due to can_transform() failures
"""

import importlib.util
import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper
from laughtrack.scrapers.implementations.api.eventbrite.data import EventbriteVenueData


ORGANIZER_ID = "3390989926"
EVENT_URL = "https://www.eventbrite.com/e/comedy-inn-fri-930pm-tickets-1982938107258"


def _club() -> Club:
    return Club(
        id=999,
        name="The Comedy Inn",
        address="14501 S Dixie Hwy",
        website="https://www.comedyinn.com",
        scraping_url=f"https://www.eventbrite.com/o/{ORGANIZER_ID}",
        popularity=0,
        zip_code="33176",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        eventbrite_id=ORGANIZER_ID,
        scraper="eventbrite",
    )


def _make_eventbrite_event(
    name: str = "Comedy Inn (Fri. 9:30pm)",
    start_date: str = "2026-04-10T21:30:00Z",
) -> EventbriteEvent:
    return EventbriteEvent(
        name=name,
        event_url=EVENT_URL,
        start_date=start_date,
        description="Shows are NEVER the same. And after you join inn, neither are you.",
        location_name="The Comedy Inn",
        location_address="14501 S Dixie Hwy, Miami, FL 33176",
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_organizer_id():
    """collect_scraping_targets() returns The Comedy Inn's organizer ID."""
    scraper = EventbriteScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert targets == [ORGANIZER_ID], (
        f"Expected [{ORGANIZER_ID!r}], got {targets} — check EventbriteScraper.collect_scraping_targets()"
    )


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events():
    """
    get_data() returns EventbriteVenueData with at least one event
    when EventbriteClient.fetch_all_events() returns events.
    """
    scraper = EventbriteScraper(_club())

    class _FakeClient:
        async def fetch_all_events(self):
            return [_make_eventbrite_event()]

    scraper.eventbrite_client = _FakeClient()  # type: ignore[assignment]

    result = await scraper.get_data(ORGANIZER_ID)

    assert isinstance(result, EventbriteVenueData), (
        "get_data() did not return EventbriteVenueData — check EventbriteScraper.get_data()"
    )
    assert len(result.event_list) == 1, (
        "get_data() returned EventbriteVenueData with 0 events — "
        "check EventbriteExtractor.to_page_data() or EventbriteClient.fetch_all_events()"
    )


@pytest.mark.asyncio
async def test_get_data_returns_empty_page_data_when_api_returns_empty():
    """get_data() returns empty EventbriteVenueData when EventbriteClient returns an empty event list."""
    scraper = EventbriteScraper(_club())

    class _EmptyClient:
        async def fetch_all_events(self):
            return []

    scraper.eventbrite_client = _EmptyClient()  # type: ignore[assignment]

    result = await scraper.get_data(ORGANIZER_ID)

    assert result is not None, (
        "get_data() should return empty EventbriteVenueData, not None, when API returns 0 events"
    )
    assert result.event_list == []


@pytest.mark.asyncio
async def test_get_data_returns_none_on_client_exception():
    """get_data() returns None when EventbriteClient raises an exception."""
    scraper = EventbriteScraper(_club())

    class _BrokenClient:
        async def fetch_all_events(self):
            raise RuntimeError("API unreachable")

    scraper.eventbrite_client = _BrokenClient()  # type: ignore[assignment]

    result = await scraper.get_data(ORGANIZER_ID)

    assert result is None, (
        "get_data() should catch exceptions and return None — "
        "check exception handling in EventbriteScraper.get_data()"
    )


def test_transformation_pipeline_produces_shows():
    """
    transformation_pipeline.transform() returns at least one Show
    when given EventbriteVenueData with a valid EventbriteEvent.

    Catches can_transform() regressions that silently drop all events.
    """
    scraper = EventbriteScraper(_club())
    event = _make_eventbrite_event()
    page_data = EventbriteVenueData(event_list=[event])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from EventbriteVenueData — "
        "check EventbriteEventTransformer.can_transform() and transformer registration"
    )
    assert all(isinstance(s, Show) for s in shows)


def test_transformation_pipeline_sets_show_date():
    """Shows produced by the pipeline have a timezone-aware date."""
    scraper = EventbriteScraper(_club())
    event = _make_eventbrite_event(start_date="2026-04-10T21:30:00Z")
    page_data = EventbriteVenueData(event_list=[event])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].date is not None
    assert shows[0].date.tzinfo is not None, "Show date must be timezone-aware"
