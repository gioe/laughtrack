"""
Pipeline smoke tests for EventbriteScraper.

Exercises get_data() -> EventbriteVenueData -> transformation_pipeline.transform()
and the venue-vs-organizer ID fallback path in EventbriteClient.fetch_all_events().

Key assertions:
- transformation_pipeline.transform() returns Shows from EventbriteVenueData
- When the Eventbrite /venues/{id}/events/ endpoint returns None (404),
  get_data() falls back to /organizers/{id}/events/ and still returns events.
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
from laughtrack.scrapers.implementations.api.eventbrite.page_data import EventbriteVenueData
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper


EVENTBRITE_ID = "253402413"


def _club() -> Club:
    return Club(
        id=999,
        name="Comic Strip Live",
        address="1568 2nd Avenue, New York, NY",
        website="https://www.comicstriplive.com",
        scraping_url="comicstriplive.com",
        popularity=0,
        zip_code="10028",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        eventbrite_id=EVENTBRITE_ID,
        scraper="eventbrite",
    )


def _make_domain_event(
    name: str = "Nikki Glaser",
    date: str = "2026-06-15T20:00:00Z",
) -> EventbriteEvent:
    """Minimal domain EventbriteEvent for pipeline tests."""
    return EventbriteEvent(
        name=name,
        event_url=f"https://www.eventbrite.com/e/{name.lower().replace(' ', '-')}-123456",
        start_date=date,
        performers=[name],
    )


# ---------------------------------------------------------------------------
# Transformation pipeline tests
# ---------------------------------------------------------------------------


def test_transformation_pipeline_produces_shows_from_eventbrite_events():
    """
    transformation_pipeline.transform() returns at least one Show
    when given EventbriteVenueData with a valid EventbriteEvent.

    Catches type-mismatch regressions where can_transform() returns False
    for EventbriteEvent objects, silently dropping all events.
    """
    scraper = EventbriteScraper(_club())
    page_data = EventbriteVenueData(event_list=[_make_domain_event()])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from EventbriteVenueData — "
        "check EventbriteEventTransformer.can_transform() and transformer registration"
    )
    assert all(isinstance(s, Show) for s in shows)


def test_transformation_pipeline_preserves_event_name():
    """Show name from the pipeline matches the source event name."""
    scraper = EventbriteScraper(_club())
    page_data = EventbriteVenueData(event_list=[_make_domain_event(name="Gary Gulman")])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].name == "Gary Gulman"


# ---------------------------------------------------------------------------
# Venue-vs-organizer fallback test (criterion 2329)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_uses_organizer_fallback_when_venue_endpoint_fails():
    """
    get_data() returns events via the organizer endpoint when the venue
    endpoint returns None (simulating a 404).

    Covers the venue-vs-organizer ID fallback: EventbriteClient.fetch_all_events()
    tries /venues/{id}/events/ first; if that returns None, it falls back to
    /organizers/{id}/events/ (documented in CLAUDE.md Eventbrite Scraper section).
    """
    scraper = EventbriteScraper(_club())
    organizer_event = _make_domain_event(name="Tom Segura")

    async def fake_fetch_paginated(endpoint_type: str, entity_id: str):
        if endpoint_type == "venues":
            return None  # Simulate venue endpoint 404
        return [organizer_event]  # Organizer endpoint succeeds

    scraper.eventbrite_client._fetch_paginated = fake_fetch_paginated

    result = await scraper.get_data(EVENTBRITE_ID)

    assert result is not None, (
        "get_data() returned None — venue-endpoint fallback to organizer did not yield events"
    )
    assert isinstance(result, EventbriteVenueData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Tom Segura"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_both_endpoints_fail():
    """
    get_data() returns None when both venue and organizer endpoints return None.
    """
    scraper = EventbriteScraper(_club())

    async def fake_fetch_paginated(endpoint_type: str, entity_id: str):
        return None

    scraper.eventbrite_client._fetch_paginated = fake_fetch_paginated

    result = await scraper.get_data(EVENTBRITE_ID)

    assert result is None, (
        "get_data() should return None when all Eventbrite endpoints fail"
    )
