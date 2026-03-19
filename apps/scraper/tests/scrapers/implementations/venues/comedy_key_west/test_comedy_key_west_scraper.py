"""
Unit tests for ComedyKeyWestScraper.get_data() async method.

These tests verify the four key paths in get_data():
 1. Empty HTML from fetch_html → returns None
 2. Non-empty HTML with no shows found → returns None with a warning
 3. Successful extraction → returns ComedyKeyWestPageData with expected shows
 4. Exception raised by fetch_html → returns None

Also verifies that the scraper is registered under the "comedy_key_west" key.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.comedy_key_west.scraper import ComedyKeyWestScraper
from laughtrack.scrapers.implementations.venues.comedy_key_west.data import ComedyKeyWestPageData


def _club() -> Club:
    return Club(
        id=98,
        name="Comedy Key West",
        address="",
        website="https://comedykeywest.com",
        scraping_url="comedykeywest.com/shows",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _build_show_html() -> str:
    """Return minimal HTML that PunchupExtractor will parse into one show."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "some-venue-uuid"],
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
                                    "title": "Key West Comedy Night",
                                    "datetime": "2026-04-15T20:00:00",
                                    "ticket_link": "https://event.tixologi.com/event/42/tickets",
                                    "tixologi_event_id": "42",
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
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "some-venue-uuid"],
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
# Registry key
# ---------------------------------------------------------------------------


def test_scraper_key_in_registry():
    from laughtrack.app.registry import SCRAPERS

    assert SCRAPERS.get("comedy_key_west") is ComedyKeyWestScraper


# ---------------------------------------------------------------------------
# ComedyKeyWestScraper.get_data — four paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_empty_html_returns_none(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html(self, url: str):
        return ""

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_no_shows_returns_none(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html(self, url: str):
        return _build_no_shows_html()

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_successful_extraction_returns_page_data(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html(self, url: str):
        return _build_show_html()

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert isinstance(result, ComedyKeyWestPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Key West Comedy Night"


@pytest.mark.asyncio
async def test_get_data_fetch_exception_returns_none(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html(self, url: str):
        raise RuntimeError("network error")

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert result is None
