"""
Pipeline smoke tests for SeatEngineScraper.

Verifies the shared-client wiring introduced in TASK-709: the SeatEngineClient
instance created in SeatEngineScraper.__init__ is passed to
SeatEngineEventTransformer so that venue_website (fetched during fetch_events)
is available when create_show builds show_page_url.

Key assertion: show_page_url must be a public venue URL
(e.g. https://example.com/shows/42) — NOT an internal API URL
(services.seatengine.com/api/v1/...) — when venue_website is populated.
"""

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine.scraper import SeatEngineScraper
from laughtrack.scrapers.implementations.api.seatengine.data import SeatEnginePageData


VENUE_ID = "42"
VENUE_WEBSITE = "https://joes-comedy.com"


def _club(seatengine_id: str = VENUE_ID) -> Club:
    _c = Club(id=999, name="Joe's Comedy Club", address='123 Laugh Lane', website=VENUE_WEBSITE, popularity=0, zip_code='10001', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine', scraper_key='', source_url='https://joes-comedy.com/shows', external_id=seatengine_id)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _show_dict(show_id: int = 101, comedian_name: str = "Alice Smith") -> dict:
    """Minimal SeatEngine API show payload."""
    return {
        "id": show_id,
        "start_date_time": "2026-04-15T20:00:00-04:00",
        "sold_out": False,
        "inventories": [{"price": 2500}],
        "event": {
            "name": "Wednesday Night Comedy",
            "description": "A great show",
            "talents": [{"name": comedian_name}],
            "labels": [],
        },
    }


# ---------------------------------------------------------------------------
# collect_scraping_targets()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_venue_id():
    """collect_scraping_targets() returns the club's seatengine_id as the sole target."""
    scraper = SeatEngineScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == [VENUE_ID]


# ---------------------------------------------------------------------------
# get_data() — wraps fetch_events in SeatEnginePageData
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() wraps API results in SeatEnginePageData with the raw event dicts."""
    scraper = SeatEngineScraper(_club())
    shows = [_show_dict(101), _show_dict(102, comedian_name="Bob Jones")]

    scraper.seatengine_client.fetch_events = AsyncMock(return_value=shows)

    result = await scraper.get_data(VENUE_ID)

    assert isinstance(result, SeatEnginePageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_empty_page_data_when_no_events(monkeypatch):
    """get_data() returns SeatEnginePageData with empty list when API returns []."""
    scraper = SeatEngineScraper(_club())
    scraper.seatengine_client.fetch_events = AsyncMock(return_value=[])

    result = await scraper.get_data(VENUE_ID)

    assert isinstance(result, SeatEnginePageData)
    assert result.event_list == []
    assert not result.is_transformable()


# ---------------------------------------------------------------------------
# Shared-client wiring: venue_website flows from fetch_events → create_show
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_page_url_is_public_venue_url_when_website_known(monkeypatch):
    """
    show_page_url must use the venue's public website — not the internal API URL —
    when venue_website is populated by fetch_events.

    This is the core regression guard for the shared-client wiring: if the
    transformer creates its own SeatEngineClient instead of reusing the scraper's,
    venue_website will be None and the show URL falls back to services.seatengine.com.
    """
    scraper = SeatEngineScraper(_club())
    show = _show_dict(show_id=42)

    # Simulate fetch_events populating venue_website on the shared client
    async def fake_fetch_events(venue_id):
        scraper.seatengine_client.venue_website = VENUE_WEBSITE
        return [show]

    scraper.seatengine_client.fetch_events = fake_fetch_events

    page_data = await scraper.get_data(VENUE_ID)
    assert isinstance(page_data, SeatEnginePageData)
    assert len(page_data.event_list) == 1

    # Transform: the transformer must use the same client instance
    shows = scraper.transform_data(page_data, source_url=VENUE_ID)

    assert len(shows) == 1
    show_obj = shows[0]
    assert show_obj.show_page_url == f"{VENUE_WEBSITE}/shows/42", (
        f"Expected public venue URL but got: {show_obj.show_page_url!r}. "
        "The transformer may not be reusing the scraper's SeatEngineClient."
    )
    assert "services.seatengine.com" not in show_obj.show_page_url


@pytest.mark.asyncio
async def test_show_page_url_falls_back_to_api_url_when_no_website(monkeypatch):
    """
    show_page_url falls back to services.seatengine.com/... when the venue
    has no website configured (venue_website remains empty string after fetch).
    """
    scraper = SeatEngineScraper(_club())
    show = _show_dict(show_id=99)

    async def fake_fetch_events(venue_id):
        scraper.seatengine_client.venue_website = ""
        return [show]

    scraper.seatengine_client.fetch_events = fake_fetch_events

    page_data = await scraper.get_data(VENUE_ID)
    shows = scraper.transform_data(page_data, source_url=VENUE_ID)

    assert len(shows) == 1
    assert "services.seatengine.com" in shows[0].show_page_url


# ---------------------------------------------------------------------------
# Transformer: lineup and ticket extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_extracts_lineup_and_tickets(monkeypatch):
    """transform_data() populates comedian lineup and ticket price from API data."""
    scraper = SeatEngineScraper(_club())
    show = _show_dict(show_id=55, comedian_name="Carol Lee")

    async def fake_fetch_events(venue_id):
        scraper.seatengine_client.venue_website = VENUE_WEBSITE
        return [show]

    scraper.seatengine_client.fetch_events = fake_fetch_events

    page_data = await scraper.get_data(VENUE_ID)
    shows = scraper.transform_data(page_data, source_url=VENUE_ID)

    assert len(shows) == 1
    show_obj = shows[0]

    # Lineup
    assert len(show_obj.lineup) == 1
    assert show_obj.lineup[0].name == "Carol Lee"

    # Tickets: 2500 cents → $25.00
    assert len(show_obj.tickets) == 1
    assert show_obj.tickets[0].price == 25.0
    assert not show_obj.tickets[0].sold_out
