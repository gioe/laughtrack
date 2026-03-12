"""Unit tests for TicketmasterNationalScraper."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from unittest.mock import AsyncMock, MagicMock, patch

from laughtrack.scrapers.implementations.api.ticketmaster_national.scraper import (
    TicketmasterNationalScraper,
)
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the national scraper."""
    return Club(
        id=999,
        name="Ticketmaster National",
        address="",
        website="",
        scraping_url="www.ticketmaster.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        scraper="ticketmaster_national",
    )


def _make_api_event(
    venue_id="KovZpZAEAaEA",
    venue_name="The Comedy Store",
    event_id="vvG1zZ4M8d8kBJ",
    event_url="https://www.ticketmaster.com/event/vvG1zZ4M8d8kBJ",
):
    """Build a minimal Ticketmaster Discovery API event dict."""
    return {
        "id": event_id,
        "name": "Comedy Night",
        "url": event_url,
        "dates": {
            "start": {"localDate": "2026-06-01", "localTime": "20:00:00"},
            "status": {"code": "onsale"},
        },
        "sales": {"public": {"startDateTime": "2026-01-01T00:00:00Z"}},
        "priceRanges": [{"type": "standard", "min": 25.0, "max": 35.0}],
        "_embedded": {
            "venues": [
                {
                    "id": venue_id,
                    "name": venue_name,
                    "timezone": "America/Los_Angeles",
                    "postalCode": "90069",
                    "address": {"line1": "8433 Sunset Blvd"},
                    "city": {"name": "West Hollywood"},
                    "state": {"stateCode": "CA"},
                }
            ],
            "attractions": [{"id": "K8vZ917KNeV", "name": "Dave Chappelle"}],
        },
    }


def _make_club(
    club_id=42,
    name="The Comedy Store",
    ticketmaster_id="KovZpZAEAaEA",
    timezone="America/Los_Angeles",
):
    return Club(
        id=club_id,
        name=name,
        address="8433 Sunset Blvd, West Hollywood, CA",
        website="",
        scraping_url="www.ticketmaster.com",
        popularity=0,
        zip_code="90069",
        phone_number="",
        visible=True,
        scraper="live_nation",
        ticketmaster_id=ticketmaster_id,
        timezone=timezone,
    )


_CONFIG_PATCH = "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.ConfigManager.get_config"


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_collect_targets_returns_national(platform_club):
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        s = TicketmasterNationalScraper(platform_club)
    targets = await s.collect_scraping_targets()
    assert targets == ["national"]


# ------------------------------------------------------------------ #
# scrape_async — empty API response                                    #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_scrape_async_empty_response(platform_club):
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=[])):
        shows = await scraper.scrape_async()

    assert shows == []


# ------------------------------------------------------------------ #
# scrape_async — happy path                                            #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_scrape_async_returns_shows_for_each_event(platform_club):
    """
    Two events from the same venue should upsert the club once and return
    a Show for each event.
    """
    event1 = _make_api_event(event_id="ev1", event_url="https://tm.com/ev1")
    event2 = _make_api_event(event_id="ev2", event_url="https://tm.com/ev2")
    api_events = [event1, event2]
    upserted_club = _make_club()

    mock_show = MagicMock(spec=Show)
    mock_show.club_id = 42

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(
        scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=api_events)
    ):
        with patch.object(
            scraper._club_handler,
            "upsert_for_ticketmaster_venue",
            return_value=upserted_club,
        ):
            with patch(
                "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.TicketmasterClient"
            ) as MockClient:
                MockClient.return_value.create_show.return_value = mock_show
                shows = await scraper.scrape_async()

    assert len(shows) == 2
    assert all(s.club_id == 42 for s in shows)


# ------------------------------------------------------------------ #
# scrape_async — club upsert failure is isolated per venue            #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_scrape_async_skips_venue_on_upsert_failure(platform_club):
    """
    A DB error upserting one venue should not prevent other venues from
    being processed.
    """
    event_ok = _make_api_event(venue_id="V1", venue_name="Good Club", event_id="ev1")
    event_bad = _make_api_event(venue_id="V2", venue_name="Bad Club", event_id="ev2")
    api_events = [event_ok, event_bad]

    good_club = _make_club(club_id=1, ticketmaster_id="V1")
    mock_show = MagicMock(spec=Show)
    mock_show.club_id = 1

    def _upsert(venue):
        if venue.get("id") == "V2":
            raise RuntimeError("DB error")
        return good_club

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)

    with patch.object(
        scraper, "_fetch_national_comedy_events", new=AsyncMock(return_value=api_events)
    ):
        with patch.object(
            scraper._club_handler, "upsert_for_ticketmaster_venue", side_effect=_upsert
        ):
            with patch(
                "laughtrack.scrapers.implementations.api.ticketmaster_national.scraper.TicketmasterClient"
            ) as MockClient:
                MockClient.return_value.create_show.return_value = mock_show
                shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].club_id == 1


# ------------------------------------------------------------------ #
# _fetch_national_comedy_events — pagination                          #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_fetch_events_paginates_until_last_page(platform_club, monkeypatch):
    """Paginator follows totalPages from the API and accumulates events."""
    page0_event = _make_api_event(venue_id="V1", event_id="ev1")
    page1_event = _make_api_event(venue_id="V2", venue_name="Venue 2", event_id="ev2")

    page0_data = {
        "_embedded": {"events": [page0_event]},
        "page": {"number": 0, "size": 200, "totalPages": 2, "totalElements": 2},
    }
    page1_data = {
        "_embedded": {"events": [page1_event]},
        "page": {"number": 1, "size": 200, "totalPages": 2, "totalElements": 2},
    }

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        return page0_data if call_count["n"] == 1 else page1_data

    monkeypatch.setattr(
        "laughtrack.infrastructure.config.config_manager.ConfigManager.get_config",
        lambda *a, **kw: "fake_api_key",
    )

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    events = await scraper._fetch_national_comedy_events()

    assert len(events) == 2
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_fetch_events_stops_on_empty_embedded(platform_club):
    """Paginator stops when _embedded.events is empty."""
    page0_data = {
        "_embedded": {"events": [_make_api_event()]},
        "page": {"number": 0, "size": 200, "totalPages": 5, "totalElements": 1},
    }
    page1_data = {
        "_embedded": {"events": []},
        "page": {"number": 1, "size": 200, "totalPages": 5, "totalElements": 1},
    }

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        return page0_data if call_count["n"] == 1 else page1_data

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    events = await scraper._fetch_national_comedy_events()

    assert len(events) == 1
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_fetch_events_stops_on_null_response(platform_club):
    """Paginator stops when fetch_json returns None."""
    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=None)

    events = await scraper._fetch_national_comedy_events()

    assert events == []


@pytest.mark.asyncio
async def test_fetch_events_skips_events_without_venues(platform_club):
    """Events with no embedded venue are excluded from results."""
    event_with_venue = _make_api_event()
    event_without_venue = {
        "id": "ev_no_venue",
        "name": "Mystery Show",
        "_embedded": {},
    }

    page_data = {
        "_embedded": {"events": [event_with_venue, event_without_venue]},
        "page": {"number": 0, "size": 200, "totalPages": 1, "totalElements": 2},
    }

    with patch(_CONFIG_PATCH, return_value="fake_api_key"):
        scraper = TicketmasterNationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=page_data)

    events = await scraper._fetch_national_comedy_events()

    assert len(events) == 1
    assert events[0]["id"] == "vvG1zZ4M8d8kBJ"
