"""
Pipeline smoke tests for SeatEngineClassicScraper.

Verifies that collect_scraping_targets(), get_data(), and transform_data()
wire together correctly for the classic (HTML-based) SeatEngine platform.

Classic SeatEngine venues serve server-rendered HTML rather than the REST API
used by the newer platform — shows are extracted from event-list-item divs.

Includes venue-specific tests for The Function SF (seatengine_id=540,
the-function.seatengine-sites.com), which uses Layout 1 HTML (event-times-group
with multiple show times per event).
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine_classic.scraper import SeatEngineClassicScraper
from laughtrack.scrapers.implementations.api.seatengine_classic.data import SeatEngineClassicPageData


SCRAPING_URL = "https://newbrunswick.stressfactory.com/events"
BASE_URL = "https://newbrunswick.stressfactory.com"


def _club() -> Club:
    _c = Club(id=999, name='Stress Factory Comedy Club', address='23 Livingston Ave', website='https://stressfactory.com', popularity=0, zip_code='08901', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


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


def _calendar_json_ld() -> str:
    return """
    <html><body>
    <script type="application/ld+json">
    {
      "@type": "Place",
      "Events": [
        {
          "@type": "Event",
          "name": "Comedy Night",
          "startDate": "2026-03-26T23:30:00Z",
          "url": "https://newbrunswick.stressfactory.com/shows/363997"
        },
        {
          "@type": "Event",
          "name": "Late Show",
          "startDate": "2026-03-27T02:00:00Z",
          "url": "https://newbrunswick.stressfactory.com/shows/363998"
        }
      ]
    }
    </script>
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
    scraper._enrich_with_prices = AsyncMock()

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
    scraper._enrich_with_prices = AsyncMock()

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
    scraper._enrich_with_prices = AsyncMock()

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
    scraper._enrich_with_prices = AsyncMock()

    page_data = await scraper.get_data(SCRAPING_URL)
    shows = scraper.transform_data(page_data, source_url=SCRAPING_URL)

    assert shows == []


@pytest.mark.asyncio
async def test_get_data_merges_additional_calendar_json_ld_shows():
    """get_data() augments /events with sibling /calendar JSON-LD shows."""
    scraper = SeatEngineClassicScraper(_club())
    scraper.fetch_html = AsyncMock(
        side_effect=[_classic_html(), _calendar_json_ld()]
    )
    scraper._enrich_with_prices = AsyncMock()

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SeatEngineClassicPageData)
    assert len(result.event_list) == 2
    assert [show["name"] for show in result.event_list] == [
        "Comedy Night",
        "Late Show",
    ]
    assert scraper.fetch_html.await_args_list[1].args[0] == (
        "https://newbrunswick.stressfactory.com/calendar"
    )


@pytest.mark.asyncio
async def test_get_data_does_not_merge_calendar_when_location_filter_is_set():
    """Location-filtered sources cannot safely use unlabelled calendar JSON-LD."""
    club = _club()
    club.active_scraping_source.source_url = (
        f"{SCRAPING_URL}#location=Bridgeport"
    )
    scraper = SeatEngineClassicScraper(club)
    scraper.fetch_html = AsyncMock(return_value=_classic_html())
    scraper._enrich_with_prices = AsyncMock()

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SeatEngineClassicPageData)
    assert result.event_list == []
    scraper.fetch_html.assert_awaited_once_with(SCRAPING_URL)


# ---------------------------------------------------------------------------
# The Function SF — Layout 1 (event-times-group) venue-specific tests
# ---------------------------------------------------------------------------

THE_FUNCTION_URL = "https://the-function.seatengine-sites.com/events"
THE_FUNCTION_BASE = "https://the-function.seatengine-sites.com"


def _the_function_club() -> Club:
    _c = Club(id=192, name='The Function SF', address='1414 Market Street', website='https://www.thefunctionsf.com', popularity=0, zip_code='94102', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine', scraper_key='seatengine_classic', source_url=THE_FUNCTION_URL, external_id='540')
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _the_function_html() -> str:
    """Layout 1 HTML: event-times-group with two show times under one event."""
    return """
    <html><body>
    <div class="event-list-item">
      <div class="el-content el-column">
        <h3 class="el-header"><a href="/events/101284">HellaDesi Comedy Night</a></h3>
        <div class="event-times-group">
          <h6 class="event-date align-right">Sat, Mar 28, 2026</h6>
          <div class="event-list-button-group">
            <div class="event-divider">
              <a class="event-btn-inline" href="/shows/361339"> 7:00 PM</a>
              <a class="event-btn-inline" href="/shows/361338"> 9:00 PM</a>
            </div>
          </div>
        </div>
      </div>
    </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_the_function_sf_collect_scraping_targets():
    """collect_scraping_targets() returns The Function SF's events URL."""
    scraper = SeatEngineClassicScraper(_the_function_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == [THE_FUNCTION_URL]


@pytest.mark.asyncio
async def test_the_function_sf_get_data_layout1_returns_two_shows():
    """get_data() extracts both show times from a Layout 1 event-times-group block."""
    scraper = SeatEngineClassicScraper(_the_function_club())
    scraper.fetch_html = AsyncMock(return_value=_the_function_html())

    result = await scraper.get_data(THE_FUNCTION_URL)

    assert isinstance(result, SeatEngineClassicPageData)
    assert result.is_transformable()
    assert len(result.event_list) == 2, (
        "Layout 1 event-times-group with two times must yield 2 shows"
    )
    assert result.event_list[0]["name"] == "HellaDesi Comedy Night"
    assert result.event_list[1]["name"] == "HellaDesi Comedy Night"


@pytest.mark.asyncio
async def test_the_function_sf_transform_data_produces_shows_with_ticket_urls():
    """transform_data() produces Show objects with correct ticket URLs for The Function SF."""
    scraper = SeatEngineClassicScraper(_the_function_club())
    scraper.fetch_html = AsyncMock(return_value=_the_function_html())

    page_data = await scraper.get_data(THE_FUNCTION_URL)
    shows = scraper.transform_data(page_data, source_url=THE_FUNCTION_URL)

    assert len(shows) == 2
    urls = {s.tickets[0].purchase_url for s in shows}
    assert f"{THE_FUNCTION_BASE}/shows/361339" in urls
    assert f"{THE_FUNCTION_BASE}/shows/361338" in urls
