"""Smoke tests for House of Comedy Bloomington's direct Tixr fallback scraper."""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.venues.house_of_comedy_bloomington.scraper import (
    HouseOfComedyBloomingtonScraper,
)

CALENDAR_URL = "https://moa.houseofcomedy.net/"
EVENT_URL = "https://www.tixr.com/groups/houseofcomedymn/events/taylor-baggott-183801"

_ONE_EVENT_HTML = f"""
<div class="event_card">
  <h3>Taylor Baggott</h3>
  <div>Show Starts: May 7, 2026 7:30 PM</div>
  <div>Door Time: May 7, 2026 6:30 PM</div>
  <a href="{EVENT_URL}" class="button-main white w-inline-block">get tickets</a>
</div>
"""

_COMPACT_EVENT_HTML = """
<div class="cal-info-2 w-dyn-item">
  <a href="https://www.tixr.com/groups/houseofcomedymn/events/the-disableds-comedy-show-183793"
     class="day-card w-inline-block">
    The Disableds Comedy Show Sunday East Village May 10, 2026 7:00 pm BUY TICKETS
  </a>
</div>
"""


def _club() -> Club:
    club = Club(
        id=655,
        name="House of Comedy Bloomington",
        address="",
        website="https://moa.houseofcomedy.net",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="house_of_comedy_bloomington",
        source_url=CALENDAR_URL,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


@pytest.mark.asyncio
async def test_get_data_builds_tixr_events_from_calendar_html(monkeypatch):
    """The scraper builds events directly from venue-page title/date/ticket blocks."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_ONE_EVENT_HTML))

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "Taylor Baggott"
    assert event.event_id == "183801"
    assert event.source_url == EVENT_URL
    assert event.show.date.year == 2026
    assert event.show.date.month == 5
    assert event.show.date.day == 7
    assert event.show.date.hour == 19
    assert event.show.date.minute == 30
    assert event.show.tickets[0].purchase_url == EVENT_URL


@pytest.mark.asyncio
async def test_get_data_returns_none_when_calendar_has_no_parseable_events(monkeypatch):
    """The scraper returns None rather than falling back to blocked Tixr event pages."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value="<html>No events</html>"))

    assert await scraper.get_data(CALENDAR_URL) is None


@pytest.mark.asyncio
async def test_get_data_builds_events_from_compact_calendar_cards(monkeypatch):
    """The scraper handles compact calendar cards that omit the Show Starts label."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_COMPACT_EVENT_HTML))

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    event = result.event_list[0]
    assert event.title == "The Disableds Comedy Show"
    assert event.event_id == "183793"
    assert event.show.date.month == 5
    assert event.show.date.day == 10
    assert event.show.date.hour == 19
