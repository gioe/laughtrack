"""
Pipeline smoke test for St. Marks Comedy scraper.

Exercises collect_scraping_targets() → get_data(): HTML page containing Tixr URLs
→ TixrClient detail fetch → StMarksPageData.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.st_marks.scraper import StMarksScraper
from laughtrack.scrapers.implementations.venues.st_marks.data import StMarksPageData


SCRAPING_URL = "www.stmarkscomedy.com"
TIXR_URL = "https://www.tixr.com/groups/stmarks/events/comedy-night-12345"


def _club() -> Club:
    return Club(
        id=99,
        name="St. Marks Comedy",
        address="",
        website="https://www.stmarkscomedy.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _venue_html() -> str:
    """Minimal HTML containing one Tixr event URL."""
    return f"""<html><body>
<a href="{TIXR_URL}">Buy Tickets</a>
</body></html>"""


def _fake_tixr_event() -> TixrEvent:
    show = Show(
        name="St. Marks Comedy Night",
        club_id=99,
        date=datetime(2026, 4, 15, 20, 0, tzinfo=timezone.utc),
        show_page_url=TIXR_URL,
    )
    return TixrEvent(show=show, source_url=TIXR_URL, event_id="12345")


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_url(monkeypatch):
    """Static URL discovery returns the club's scraping_url without HTTP calls."""
    scraper = StMarksScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_tixr_urls(monkeypatch):
    """get_data() extracts Tixr URLs from HTML and fetches event details."""
    scraper = StMarksScraper(_club())

    async def fake_fetch_page(url: str) -> str:
        return _venue_html()

    monkeypatch.setattr(scraper.tixr_client, "_fetch_tixr_page", fake_fetch_page)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_fake_tixr_event()),
    )

    result = await scraper.get_data(f"https://{SCRAPING_URL}")

    assert isinstance(result, StMarksPageData), "get_data() did not return StMarksPageData"
    assert len(result.event_list) > 0, (
        "get_data() returned 0 events — check extract_tixr_urls() and TixrClient integration"
    )
    assert result.event_list[0].show.name == "St. Marks Comedy Night"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = StMarksScraper(_club())

    async def fake_fetch_page(url: str) -> str:
        return _venue_html()

    monkeypatch.setattr(scraper.tixr_client, "_fetch_tixr_page", fake_fetch_page)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_fake_tixr_event()),
    )

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
