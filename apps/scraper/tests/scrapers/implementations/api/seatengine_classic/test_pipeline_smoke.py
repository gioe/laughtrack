"""
Pipeline smoke tests for SeatEngineClassicScraper.

Verifies that collect_scraping_targets(), get_data(), and transform_data()
wire together correctly for the classic (HTML-based) SeatEngine platform.

Classic SeatEngine venues serve server-rendered HTML rather than the REST API
used by the newer platform — shows are extracted from event-list-item divs.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.seatengine_classic.scraper import SeatEngineClassicScraper
from laughtrack.scrapers.implementations.api.seatengine_classic.page_data import SeatEngineClassicPageData


SCRAPING_URL = "https://newbrunswick.stressfactory.com/events"
BASE_URL = "https://newbrunswick.stressfactory.com"


def _club() -> Club:
    return Club(
        id=999,
        name="Stress Factory Comedy Club",
        address="23 Livingston Ave",
        website="https://stressfactory.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="08901",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _classic_html(
    event_name: str = "Comedy Night",
    show_href: str = "/shows/363997",
    date_str: str = "Thu Mar 26 2026, 7:30 PM",
) -> str:
    return f"""
    <html><body>
    <div class="event-list-item">
      <h3 class="el-header"><a href="/events/128084">{event_name}</a></h3>
      <h6 class="event-date">{date_str}</h6>
      <a class="btn btn-primary" href="{show_href}">Buy Tickets</a>
    </div>
    </body></html>
    """


# ---------------------------------------------------------------------------
# collect_scraping_targets()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_scraping_url():
    """collect_scraping_targets() returns the club's scraping_url as the sole target."""
    scraper = SeatEngineClassicScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == [SCRAPING_URL]


# ---------------------------------------------------------------------------
# get_data() — fetches HTML and returns SeatEngineClassicPageData
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events():
    """get_data() wraps extracted shows in SeatEngineClassicPageData."""
    scraper = SeatEngineClassicScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_classic_html())

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SeatEngineClassicPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0]["name"] == "Comedy Night"
    assert result.is_transformable()


@pytest.mark.asyncio
async def test_get_data_returns_empty_page_data_when_no_html():
    """get_data() returns empty SeatEngineClassicPageData when fetch_html returns None."""
    scraper = SeatEngineClassicScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=None)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SeatEngineClassicPageData)
    assert result.event_list == []
    assert not result.is_transformable()


# ---------------------------------------------------------------------------
# transform_data() — wires get_data → Show objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_data_extracts_show_name_and_ticket():
    """transform_data() produces Show objects with name and ticket from extracted HTML."""
    scraper = SeatEngineClassicScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_classic_html())

    page_data = await scraper.get_data(SCRAPING_URL)
    shows = scraper.transform_data(page_data, source_url=SCRAPING_URL)

    assert len(shows) == 1
    show = shows[0]
    assert show.name == "Comedy Night"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == f"{BASE_URL}/shows/363997"
    assert not show.tickets[0].sold_out


@pytest.mark.asyncio
async def test_transform_data_returns_empty_for_empty_page_data():
    """transform_data() returns [] when page_data has no events."""
    scraper = SeatEngineClassicScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=None)

    page_data = await scraper.get_data(SCRAPING_URL)
    shows = scraper.transform_data(page_data, source_url=SCRAPING_URL)

    assert shows == []
