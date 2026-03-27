"""
Pipeline smoke test for Uncle Vinnie's Comedy Club scraper.

Uncle Vinnies uses discover_urls() (returns club.scraping_url) → get_data()
which loops over 6 months of calendar HTML and calls the OvationTix API per event.

get_data() calls session.get() directly (not fetch_json), so we provide a fake
AsyncSession via a mock of get_session().
"""

import importlib.util
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.uncle_vinnies.scraper import UncleVinniesScraper
from laughtrack.scrapers.implementations.venues.uncle_vinnies.data import UncleVinniesPageData


SCRAPING_URL = "https://unclevinniescomedyclub.com"
PRODUCTION_ID = "1234567"
PERFORMANCE_ID = "9876543"
EVENT_URL = f"https://ci.ovationtix.com/35774/production/{PRODUCTION_ID}"


def _club() -> Club:
    return Club(
        id=99,
        name="Uncle Vinnie's Comedy Club",
        address="",
        website=SCRAPING_URL,
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _calendar_html() -> str:
    """Minimal calendar HTML with one OvationTix event link."""
    return f"""<html><body>
<a class="tickets-button" href="{EVENT_URL}">Buy Tickets</a>
</body></html>"""


def _make_fake_session() -> MagicMock:
    """
    Return a MagicMock session whose .get() returns appropriate OvationTix responses.

    Three endpoints are called by get_data():
    1. Production summary: .../Production({id})/performance? → next performance id + start_date
    2. Performance detail: .../Performance({perf_id}) → performance data for event creation
    """
    session = MagicMock()

    production_response = MagicMock()
    production_response.status_code = 200
    production_response.json.return_value = {
        "performanceSummary": {
            "nextPerformance": {
                "id": PERFORMANCE_ID,
                "startDate": "2030-04-15 20:00",  # Far future avoids is_past_event filter
            }
        }
    }
    production_response.raise_for_status = MagicMock()

    performance_response = MagicMock()
    performance_response.status_code = 200
    performance_response.json.return_value = {
        "id": PERFORMANCE_ID,
        "startDate": "2030-04-15 20:00",
        "production": {
            "productionName": "Uncle Vinnie's Comedy Night",
            "description": "Stand-up comedy night",
        },
        "sections": [],
        "ticketsAvailable": True,
    }
    performance_response.raise_for_status = MagicMock()

    async def fake_get(url: str, headers: Dict = None) -> MagicMock:
        if "Performance(" in url and "performance?" not in url:
            return performance_response
        return production_response

    session.get = fake_get
    return session


@pytest.mark.asyncio
async def test_discover_urls_returns_scraping_url():
    """discover_urls() returns the club's scraping_url without any HTTP calls."""
    scraper = UncleVinniesScraper(_club())
    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_calendar_and_api(monkeypatch):
    """get_data() finds events from calendar HTML and OvationTix API responses."""
    scraper = UncleVinniesScraper(_club())

    async def fake_fetch_html(self, url: str, headers: Dict = None) -> str:
        return _calendar_html()

    monkeypatch.setattr(UncleVinniesScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "get_session", AsyncMock(return_value=_make_fake_session()))

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, UncleVinniesPageData), "get_data() did not return UncleVinniesPageData"
    assert len(result.event_list) > 0, (
        "get_data() returned 0 events — check extract_event_urls_from_calendar_html() "
        "and OvationTix API mock responses"
    )
    assert result.event_list[0].name == "Uncle Vinnie's Comedy Night"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: discover_urls() feeds into get_data()."""
    scraper = UncleVinniesScraper(_club())

    async def fake_fetch_html(self, url: str, headers: Dict = None) -> str:
        return _calendar_html()

    monkeypatch.setattr(UncleVinniesScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "get_session", AsyncMock(return_value=_make_fake_session()))

    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
