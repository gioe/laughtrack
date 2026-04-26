"""
Unit tests for WestSideScraper.get_data() async method.

These tests verify the four key paths in get_data():
 1. Empty HTML from fetch_html_bare → returns None
 2. Non-empty HTML with no shows found → returns None with a warning
 3. Successful extraction → returns WestSidePageData with expected shows
 4. Exception raised by fetch_html_bare → returns None
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.west_side.scraper import WestSideScraper
from laughtrack.scrapers.implementations.venues.west_side.data import WestSidePageData


def _club() -> Club:
    _c = Club(id=8, name='West Side Comedy Club', address='', website='https://westsidecomedyclub.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='westsidecomedyclub.com/calendar', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _build_show_html() -> str:
    """Return minimal HTML that WestSideExtractor will parse into one show."""
    import json

    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "386befdb-9075-4a84-8adc-4e5e5c945fbc"],
                "state": {
                    "data": {
                        "mode": "custom",
                        "items": [
                            {
                                "type": "show",
                                "id": "item-uuid-1",
                                "order": 1,
                                "show": {
                                    "id": "show-uuid-1",
                                    "title": "Test Comic Night",
                                    "datetime": "2026-04-01T20:00:00",
                                    "ticket_link": "https://event.tixologi.com/event/1/tickets",
                                    "tixologi_event_id": "1",
                                    "is_sold_out": False,
                                    "metadata_text": None,
                                    "show_comedians": [],
                                },
                            }
                        ],
                    },
                    "status": "success",
                },
            }
        ]
    }
    json_str = json.dumps(payload)
    return f"<html><body><script>{json_str}</script></body></html>"


def _build_no_shows_html() -> str:
    """Return HTML with an empty carousel items list — extractor returns []."""
    import json

    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "386befdb-9075-4a84-8adc-4e5e5c945fbc"],
                "state": {
                    "data": {"mode": "custom", "items": []},
                    "status": "success",
                },
            }
        ]
    }
    json_str = json.dumps(payload)
    return f"<html><body><script>{json_str}</script></body></html>"


# ---------------------------------------------------------------------------
# WestSideScraper.get_data — four paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_empty_html_returns_none(monkeypatch):
    scraper = WestSideScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return ""

    monkeypatch.setattr(WestSideScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("westsidecomedyclub.com/calendar")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_no_shows_returns_none(monkeypatch):
    scraper = WestSideScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return _build_no_shows_html()

    monkeypatch.setattr(WestSideScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("westsidecomedyclub.com/calendar")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_successful_extraction_returns_page_data(monkeypatch):
    scraper = WestSideScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return _build_show_html()

    monkeypatch.setattr(WestSideScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("westsidecomedyclub.com/calendar")
    assert isinstance(result, WestSidePageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Test Comic Night"


@pytest.mark.asyncio
async def test_get_data_fetch_exception_returns_none(monkeypatch):
    scraper = WestSideScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        raise RuntimeError("network error")

    monkeypatch.setattr(WestSideScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("westsidecomedyclub.com/calendar")
    assert result is None
