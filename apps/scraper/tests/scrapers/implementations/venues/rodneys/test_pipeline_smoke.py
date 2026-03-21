"""
Integration smoke test for the Rodneys scraper pipeline.

Exercises discover_urls() -> get_data() -> events together against HTML fixtures
matching the actual rodneysnewyorkcomedyclub.com structure (no JSON-LD).

This catches regressions where URL discovery is intact but the data extraction
path silently returns empty (the failure mode from TASK-405/TASK-523).
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.rodneys.scraper import (
    RodneysComedyClubScraper,
)
from laughtrack.scrapers.implementations.venues.rodneys.data import RodneyPageData


CALENDAR_URL = "https://rodneysnewyorkcomedyclub.com/shows"
SHOW_URL_1 = "https://rodneysnewyorkcomedyclub.com/shows/dan-naturman-and-friends"
SHOW_URL_2 = "https://rodneysnewyorkcomedyclub.com/shows/friday-night-stand-up"


def _club() -> Club:
    return Club(
        id=99,
        name="Rodney's Comedy Club",
        address="",
        website="https://rodneysnewyorkcomedyclub.com",
        scraping_url="rodneysnewyorkcomedyclub.com/shows",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _calendar_html() -> str:
    """
    Minimal HTML for the main shows listing page.
    Contains two show page links whose href contains 'rodneysnewyorkcomedyclub.com/shows'.
    """
    return f"""<html><body>
<div class="show-list">
  <a href="{SHOW_URL_1}">
    <div>Dan Naturman and Friends</div>
  </a>
  <a href="{SHOW_URL_2}">
    <div>Friday Night Stand-Up</div>
  </a>
  <!-- nav links that should NOT be picked up -->
  <a href="https://rodneysnewyorkcomedyclub.com/about">About</a>
</div>
</body></html>"""


def _show_page_html(title: str, date_str: str) -> str:
    """
    Minimal HTML for a show detail page matching the actual site structure.
    No JSON-LD — uses h4.uppercase for title and h4.mb-5 for date.
    """
    return f"""<html><body>
<h4 class="padding10 align-center no-margin uppercase">{title}</h4>
<h4 class="fg-red text-bold">Ticket Price</h4>
<h4 class="no-margin-bottom">GENERAL: $20</h4>
<a href="https://parde.app/attending/events/abc123"><button>CHECKOUT</button></a>
<h4 class="no-margin text-bold mb-5">{date_str}</h4>
</body></html>"""


def _make_fetch_html(calendar_html: str, show_pages: dict) -> object:
    """
    Return an async fake for fetch_html that routes by URL:
      - calendar URL   → calendar_html
      - show page URLs → show_pages[url]
    """
    async def fake_fetch_html(self, url: str) -> str:
        if "rodneysnewyorkcomedyclub.com/shows" == url.rstrip("/") or url == CALENDAR_URL:
            return calendar_html
        return show_pages.get(url, "")

    return fake_fetch_html


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_urls_returns_show_links(monkeypatch):
    """discover_urls() must find at least one show-page URL from the calendar HTML."""
    scraper = RodneysComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _calendar_html()

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    urls = await scraper.discover_urls()

    assert len(urls) > 0, (
        "discover_urls() returned 0 URLs — check extract_show_links() against calendar HTML"
    )
    assert all("rodneysnewyorkcomedyclub.com/shows/" in u for u in urls), (
        f"Unexpected URLs returned: {urls}"
    )


@pytest.mark.asyncio
async def test_get_data_returns_events_from_html_fixture(monkeypatch):
    """
    get_data() must return at least one event from HTML-only show pages.

    This is the critical regression path: the site embeds event data in
    h4.uppercase / h4.mb-5 elements (no JSON-LD). If extract_events_from_html()
    silently falls through both code paths, event_list will be empty.
    """
    scraper = RodneysComedyClubScraper(_club())
    show_html = _show_page_html("Dan Naturman and Friends", "Sat | March 21, 2026 - 8:30PM")

    async def fake_fetch_html(self, url: str) -> str:
        return show_html

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SHOW_URL_1)

    assert isinstance(result, RodneyPageData), "get_data() did not return RodneyPageData"
    assert len(result.event_list) > 0, (
        "get_data() returned 0 events from valid show page HTML — "
        "check extract_events_from_html() HTML fallback path"
    )
    event = result.event_list[0]
    assert event.title == "Dan Naturman and Friends"
    assert event.source_url == SHOW_URL_1


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """
    Full pipeline smoke test: discover_urls() feeds into get_data().

    Mocks fetch_html to serve different HTML per URL — calendar page for URL
    discovery, show-page HTML for each discovered URL. Asserts the end-to-end
    pipeline produces at least one event.
    """
    scraper = RodneysComedyClubScraper(_club())

    show_pages = {
        SHOW_URL_1: _show_page_html("Dan Naturman and Friends", "Sat | March 21, 2026 - 8:30PM"),
        SHOW_URL_2: _show_page_html("Friday Night Stand-Up", "Fri | March 27, 2026 - 9:00PM"),
    }

    async def fake_fetch_html(self, url: str) -> str:
        # The scraper normalizes the calendar URL before fetching
        if "rodneysnewyorkcomedyclub.com/shows" in url and url not in show_pages:
            return _calendar_html()
        return show_pages.get(url, "")

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    # Step 1: discover
    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"

    # Step 2: get_data for each discovered URL
    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, (
        "Full pipeline produced 0 events — "
        "discover_urls() found URLs but get_data() extracted nothing from any of them"
    )
