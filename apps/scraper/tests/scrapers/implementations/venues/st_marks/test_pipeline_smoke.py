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

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrPublicCardScraper, TixrScraper
from laughtrack.scrapers.implementations.venues.st_marks.scraper import StMarksScraper
from laughtrack.scrapers.implementations.venues.st_marks.data import StMarksPageData


SCRAPING_URL = "https://www.stmarkscomedyclub.com/calendar"
TIXR_URL = "https://www.tixr.com/groups/stmarks/events/comedy-night-12345"


def _club() -> Club:
    _c = Club(id=99, name='St. Marks Comedy', address='', website='https://www.stmarkscomedy.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _venue_html() -> str:
    """Minimal HTML containing one Tixr event URL."""
    return f"""<html><body>
<a href="{TIXR_URL}">Buy Tickets</a>
</body></html>"""


def _venue_card_html() -> str:
    """Minimal venue-owned Webflow card with complete public event data."""
    return f"""<html><body>
<div class="event-item w-dyn-item" role="listitem">
  <a class="ticket-links grid w-inline-block" href="{TIXR_URL}">
    <div class="text-block-35">St. Marks Comedy Night</div>
    <div class="event-card grid">
      <div class="date-info grid">
        <div class="month grid date">Wed</div>
        <div class="month grid">Jun</div>
        <div class="month grid custom-filter">Jun</div>
        <div class="month day grid">10</div>
        <div class="month day time">7:30 pm</div>
      </div>
    </div>
  </a>
</div>
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


@pytest.mark.asyncio
async def test_tixr_detail_scraper_enriches_public_card_urls(monkeypatch):
    """The detail scraper still resolves extracted Tixr URLs through event pages."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _venue_card_html()

    detail_fetch = AsyncMock(return_value=_fake_tixr_event())
    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.tixr_client, "get_event_detail_from_url", detail_fetch)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    detail_fetch.assert_awaited_once_with(TIXR_URL)


@pytest.mark.asyncio
async def test_public_card_scraper_avoids_blocked_detail_fetch(monkeypatch):
    """
    St. Marks' venue-owned calendar carries title, date/time, and ticket URL, so
    the public-card scraper should build shows without fetching Tixr detail pages.
    """
    scraper = TixrPublicCardScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _venue_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "St. Marks Comedy Night"
    assert event.source_url == TIXR_URL
    assert event.show.show_page_url == TIXR_URL
    assert event.show.tickets[0].purchase_url == TIXR_URL
    assert event.show.date.hour == 19
    assert event.show.date.minute == 30
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()
