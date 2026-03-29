"""
Pipeline smoke test for Four Day Weekend Comedy scraper.

Architecture:
  discover_urls() → [scraping_url]
  get_data(url)   → fetches buy-tickets HTML, extracts production IDs,
                    calls OvationTix Production/performance? per ID,
                    returns FourDayWeekendPageData

We mock:
  - fetch_html()   → returns minimal HTML with an OvationTix production link
  - session.get()  → returns fake OvationTix API responses
"""

import importlib.util
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.four_day_weekend.scraper import FourDayWeekendScraper
from laughtrack.scrapers.implementations.venues.four_day_weekend.data import FourDayWeekendPageData

SCRAPING_URL = "https://www.fourdayweekend.com/buy-tickets"
CLIENT_ID = "36367"
PRODUCTION_ID = "1068128"
PERFORMANCE_ID = "11768380"


def _club() -> Club:
    return Club(
        id=99,
        name="Four Day Weekend Comedy",
        address="5601 Sears St",
        website="https://www.fourdayweekend.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="75206",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _buy_tickets_html() -> str:
    """Minimal HTML containing one OvationTix production link."""
    return (
        "<html><body>"
        f'<a href="https://ci.ovationtix.com/{CLIENT_ID}/production/{PRODUCTION_ID}">'
        "Buy Tickets</a>"
        "</body></html>"
    )


def _fake_production_response() -> MagicMock:
    """Fake OvationTix Production/performance? response with two performances."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "id": int(PRODUCTION_ID),
        "productionName": "Four Day Weekend Dallas",
        "description": "Audience-driven improv comedy",
        "performances": [
            {
                "id": int(PERFORMANCE_ID),
                "startDate": "2030-04-03 20:00",
                "ticketsAvailable": True,
                "availableToPurchaseOnWeb": True,
                "availability": {"webAvailable": "A"},
            },
            {
                "id": int(PERFORMANCE_ID) + 1,
                "startDate": "2030-04-04 19:00",
                "ticketsAvailable": True,
                "availableToPurchaseOnWeb": True,
                "availability": {"webAvailable": "A"},
            },
        ],
        "performanceSummary": {
            "count": 2,
            "nextPerformance": {"id": int(PERFORMANCE_ID), "startDate": "2030-04-03 20:00"},
        },
    }
    return resp


def _make_fake_session() -> MagicMock:
    session = MagicMock()

    async def fake_get(url: str, headers: Dict = None) -> MagicMock:
        return _fake_production_response()

    session.get = fake_get
    return session


@pytest.mark.asyncio
async def test_discover_urls_returns_scraping_url():
    scraper = FourDayWeekendScraper(_club())
    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), (
        f"Expected scraping URL in targets, got: {urls}"
    )


@pytest.mark.asyncio
async def test_get_data_returns_events_from_api(monkeypatch):
    """get_data() parses production IDs from HTML and fetches performances from API."""
    scraper = FourDayWeekendScraper(_club())

    async def fake_fetch_html(self, url: str, headers: Dict = None) -> str:
        return _buy_tickets_html()

    monkeypatch.setattr(FourDayWeekendScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "get_session", AsyncMock(return_value=_make_fake_session()))

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, FourDayWeekendPageData), (
        f"get_data() returned {type(result)}, expected FourDayWeekendPageData"
    )
    assert len(result.event_list) == 2, (
        f"Expected 2 events (one per performance), got {len(result.event_list)}"
    )
    event = result.event_list[0]
    assert event.production_name == "Four Day Weekend Dallas"
    assert event.performance_id == PERFORMANCE_ID
    assert event.start_date == "2030-04-03 20:00"
    assert f"production/{PRODUCTION_ID}" in event.event_url
    assert f"performanceId={PERFORMANCE_ID}" in event.event_url


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """Full pipeline: discover → get_data → transformation_pipeline produces Show objects."""
    scraper = FourDayWeekendScraper(_club())

    async def fake_fetch_html(self, url: str, headers: Dict = None) -> str:
        return _buy_tickets_html()

    monkeypatch.setattr(FourDayWeekendScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "get_session", AsyncMock(return_value=_make_fake_session()))

    urls = await scraper.discover_urls()
    all_shows = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            shows = scraper.transformation_pipeline.transform(page_data)
            all_shows.extend(shows)

    assert len(all_shows) > 0, (
        "Full pipeline produced 0 shows — check FourDayWeekendEvent.to_show()"
    )
    show = all_shows[0]
    assert show.name == "Four Day Weekend Dallas"
