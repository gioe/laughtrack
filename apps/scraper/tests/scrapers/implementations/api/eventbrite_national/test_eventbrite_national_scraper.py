"""Unit tests for EventbriteNationalScraper."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from unittest.mock import AsyncMock, MagicMock, patch

from laughtrack.scrapers.implementations.api.eventbrite_national.scraper import (
    EventbriteNationalScraper,
)
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the national scraper."""
    _c = Club(id=999, name='Eventbrite National', address='', website='', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='eventbrite_national', scraper_key='eventbrite_national', source_url='www.eventbrite.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_api_event(venue_id="V1", venue_name="Test Club", event_url="https://eb.com/e/1"):
    """Build a minimal duck-typed Eventbrite API event."""
    venue = MagicMock()
    venue.id = venue_id
    venue.name = venue_name
    venue.address = MagicMock()
    venue.address.address_1 = "123 Main St"
    venue.address.city = "New York"
    venue.address.region = "NY"
    venue.address.postal_code = "10001"

    event = MagicMock()
    event.venue = venue
    event.url = event_url
    event.name = MagicMock()
    event.name.text = "Comedy Night"
    event.name.html = None
    event.start = MagicMock()
    event.start.utc = "2026-06-01T20:00:00Z"
    event.description = None
    return event


def _make_club(club_id=42, name="Test Club", eventbrite_id="V1"):
    _c = Club(id=club_id, name=name, address='123 Main St, New York, NY', website='', popularity=0, zip_code='10001', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='eventbrite', scraper_key='eventbrite', source_url='www.eventbrite.com', external_id=eventbrite_id)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_collect_targets_returns_national(platform_club):
    s = EventbriteNationalScraper(platform_club)
    targets = await s.collect_scraping_targets()
    assert targets == ["national"]


# ------------------------------------------------------------------ #
# scrape_async — happy path                                            #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_returns_shows_for_each_event(platform_club):
    """
    Given two events from the same venue, _scrape_async_impl should upsert the club
    once and return a Show for each event.

    Note: scrape_async() is retired and raises RuntimeError; tests use
    _scrape_async_impl() directly to exercise the underlying logic.
    """
    api_events = [
        _make_api_event(venue_id="V1", event_url="https://eb.com/e/1"),
        _make_api_event(venue_id="V1", event_url="https://eb.com/e/2"),
    ]
    upserted_club = _make_club()

    scraper = EventbriteNationalScraper(platform_club)

    with patch.object(
        scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=api_events)
    ):
        with patch.object(
            scraper._club_handler,
            "upsert_for_eventbrite_venue",
            return_value=upserted_club,
        ):
            shows = await scraper._scrape_async_impl()

    assert len(shows) == 2
    assert all(isinstance(s, Show) for s in shows)
    assert all(s.club_id == 42 for s in shows)


# ------------------------------------------------------------------ #
# scrape_async — empty API response                                    #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_empty_response(platform_club):
    scraper = EventbriteNationalScraper(platform_club)

    with patch.object(
        scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=[])
    ):
        shows = await scraper._scrape_async_impl()

    assert shows == []


# ------------------------------------------------------------------ #
# scrape_async — club upsert failure is isolated per venue            #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_skips_venue_on_upsert_failure(platform_club):
    """
    A DB error on upsert for one venue should not prevent other venues
    from being processed.
    """
    event_ok = _make_api_event(venue_id="V1", event_url="https://eb.com/e/1")
    event_bad = _make_api_event(venue_id="V2", venue_name="Bad Venue", event_url="https://eb.com/e/2")
    api_events = [event_ok, event_bad]

    good_club = _make_club(club_id=1, name="Test Club", eventbrite_id="V1")

    def _upsert(venue):
        if venue.id == "V2":
            raise RuntimeError("DB error")
        return good_club

    scraper = EventbriteNationalScraper(platform_club)

    with patch.object(
        scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=api_events)
    ):
        with patch.object(scraper._club_handler, "upsert_for_eventbrite_venue", side_effect=_upsert):
            shows = await scraper._scrape_async_impl()

    # Only the good venue's show should be returned
    assert len(shows) == 1
    assert shows[0].club_id == 1


# ------------------------------------------------------------------ #
# _fetch_national_comedy_events — pagination                          #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fetch_national_comedy_events_paginates(platform_club, monkeypatch):
    """
    The scraper should follow pagination until has_more_items is False,
    accumulating events from all pages.
    """
    page1_event = _make_api_event(venue_id="V1", event_url="https://eb.com/e/1")
    page2_event = _make_api_event(venue_id="V2", venue_name="Venue 2", event_url="https://eb.com/e/2")

    page1_data = {
        "events": [
            {
                "id": "1", "name": {"text": "Comedy Night"}, "url": "https://eb.com/e/1",
                "status": "live", "created": "", "changed": "", "published": "",
                "currency": "USD", "online_event": False, "organization_id": "1",
                "organizer_id": "1", "resource_uri": "", "source": "",
                "start": {"timezone": "UTC", "utc": "2026-06-01T20:00:00Z", "local": "2026-06-01T20:00:00"},
                "venue": {
                    "id": "V1", "name": "Test Club", "resource_uri": "",
                    "address": {"address_1": "123 Main", "city": "NY", "region": "NY", "postal_code": "10001"},
                },
            }
        ],
        "pagination": {
            "object_count": 2, "page_number": 1, "page_size": 1,
            "page_count": 2, "continuation": "tok123", "has_more_items": True,
        },
    }
    page2_data = {
        "events": [
            {
                "id": "2", "name": {"text": "Improv Night"}, "url": "https://eb.com/e/2",
                "status": "live", "created": "", "changed": "", "published": "",
                "currency": "USD", "online_event": False, "organization_id": "1",
                "organizer_id": "1", "resource_uri": "", "source": "",
                "start": {"timezone": "UTC", "utc": "2026-06-02T20:00:00Z", "local": "2026-06-02T20:00:00"},
                "venue": {
                    "id": "V2", "name": "Venue 2", "resource_uri": "",
                    "address": {"address_1": "456 Elm", "city": "LA", "region": "CA", "postal_code": "90001"},
                },
            }
        ],
        "pagination": {
            "object_count": 2, "page_number": 2, "page_size": 1,
            "page_count": 2, "continuation": None, "has_more_items": False,
        },
    }

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return page1_data
        return page2_data

    monkeypatch.setattr(
        "laughtrack.infrastructure.config.config_manager.ConfigManager.get_config",
        lambda *a, **kw: "fake_token",
    )

    scraper = EventbriteNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    events = await scraper._fetch_national_comedy_events()

    assert len(events) == 2
    assert call_count["n"] == 2
    venue_ids = {e.venue.id for e in events}
    assert venue_ids == {"V1", "V2"}
