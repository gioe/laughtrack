"""
Pipeline smoke test for The Stand NYC scraper.

Exercises discover_urls() → get_data() using HTML fixtures with Tixr event links.
The Stand uses discover_urls() (not collect_scraping_targets) for URL discovery.
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
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrPublicCardScraper
from laughtrack.scrapers.implementations.venues.the_stand.scraper import TheStandNYCScraper
from laughtrack.scrapers.implementations.venues.the_stand.data import TheStandPageData


SCRAPING_URL = "thestandnyc.com"
PUBLIC_SHOWS_URL = "https://thestandnyc.com/shows"
TIXR_URL = "https://www.tixr.com/groups/thestand/events/comedy-showcase-67890"
STAND_TIXR_URL = "https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376"


def _club() -> Club:
    _c = Club(id=99, name='The Stand', address='', website='https://thestandnyc.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _page_html_no_pagination() -> str:
    """Minimal HTML with one Tixr URL and no 'More Shows' / next-month pagination link."""
    return f"""<html><body>
<a href="{TIXR_URL}">Buy Tickets</a>
</body></html>"""


def _fake_tixr_event() -> TixrEvent:
    show = Show(
        name="The Stand Comedy Showcase",
        club_id=99,
        date=datetime(2026, 4, 20, 20, 0, tzinfo=timezone.utc),
        show_page_url=TIXR_URL,
    )
    return TixrEvent(show=show, source_url=TIXR_URL, event_id="67890")


@pytest.mark.asyncio
async def test_discover_urls_returns_start_url(monkeypatch):
    """discover_urls() returns the starting URL when no pagination links are found."""
    scraper = TheStandNYCScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _page_html_no_pagination()

    monkeypatch.setattr(TheStandNYCScraper, "fetch_html", fake_fetch_html)

    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in discovered URLs, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_tixr_urls(monkeypatch):
    """get_data() extracts Tixr URLs from HTML page and fetches event details."""
    scraper = TheStandNYCScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _page_html_no_pagination()

    monkeypatch.setattr(TheStandNYCScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_fake_tixr_event()),
    )

    result = await scraper.get_data(f"https://{SCRAPING_URL}")

    assert isinstance(result, TheStandPageData), "get_data() did not return TheStandPageData"
    assert len(result.event_list) > 0, (
        "get_data() returned 0 events — check extract_tixr_urls() and TixrClient integration"
    )
    assert result.event_list[0].show.name == "The Stand Comedy Showcase"


def _stand_public_card_html() -> str:
    """Minimal Bootstrap-style show row matching thestandnyc.com/shows.

    The h2.showtitle href encodes the full ISO datetime in its slug; the
    a.btn-stand href carries the Tixr ticket URL. Sold-out shows replace
    the buy link with a span.btn-outline-danger and should be skipped.
    """
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="https://thestandnyc.com//shows/show/12964/2026-05-08-190000-the-stand-presents-josh-ocean-thomas">The Stand Presents: Josh Ocean Thomas</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">7:00 PM</span> <span class="list-show-room">Upstairs</span></h3>
  <div class="text-uppercase">
    <a href="https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376" class="btn btn-stand">Buy Tickets</a>
  </div>
</div>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12965/2026-05-08-200000-the-stand-presents-kyle-dunnigan">The Stand Presents: Kyle Dunnigan</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">8:00 PM</span> <span class="list-show-room">Main Room</span></h3>
  <div class="text-uppercase">
    <span class="btn btn-outline-danger">Sold Out</span>
  </div>
</div>
</body></html>"""


@pytest.mark.asyncio
async def test_public_card_scraper_avoids_blocked_detail_fetch(monkeypatch):
    """
    The Stand's /shows page exposes title, ISO datetime in the title-link
    slug, and a Tixr ticket URL — so the public-card scraper builds Show
    objects from the page instead of calling the DataDome-blocked Tixr
    detail endpoint. Sold-out cards have no Tixr URL and are skipped.
    """
    scraper = TixrPublicCardScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(PUBLIC_SHOWS_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "The Stand Presents: Josh Ocean Thomas"
    assert event.source_url == STAND_TIXR_URL
    assert event.show.show_page_url == STAND_TIXR_URL
    assert event.show.tickets[0].purchase_url == STAND_TIXR_URL
    assert event.show.tickets[0].sold_out is False
    assert event.show.room == "Upstairs"
    # Title slug "2026-05-08-190000" → 2026-05-08 19:00 in venue timezone (America/New_York).
    assert event.show.date.year == 2026
    assert event.show.date.month == 5
    assert event.show.date.day == 8
    assert event.show.date.hour == 19
    assert event.show.date.minute == 0
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: discover_urls() feeds into get_data()."""
    scraper = TheStandNYCScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _page_html_no_pagination()

    monkeypatch.setattr(TheStandNYCScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_fake_tixr_event()),
    )

    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
