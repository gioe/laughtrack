"""
Unit tests for RodneysComedyClubScraper.get_data().

Verifies that get_data(url) fetches the passed-in show page URL rather than
the calendar listing URL (self.club.scraping_url).
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


def _show_page_html() -> str:
    """Minimal HTML with a JSON-LD Event block."""
    return """<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "Test Comic Night",
  "startDate": "2026-04-10T20:00:00",
  "location": {"name": "Rodney's Comedy Club"},
  "url": "https://rodneysnewyorkcomedyclub.com/shows/test-comic-night"
}
</script>
</head><body></body></html>"""


# ---------------------------------------------------------------------------
# get_data() fetches the passed-in url, not self.club.scraping_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_fetches_passed_in_url_not_calendar(monkeypatch):
    """get_data(url) must fetch url, not self.club.scraping_url."""
    scraper = RodneysComedyClubScraper(_club())
    fetched_urls = []

    async def fake_fetch_html(self, url: str):
        fetched_urls.append(url)
        return _show_page_html()

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    show_url = "https://rodneysnewyorkcomedyclub.com/shows/test-comic-night"
    await scraper.get_data(show_url)

    assert len(fetched_urls) == 1
    assert fetched_urls[0] == show_url, (
        f"get_data() fetched {fetched_urls[0]!r} instead of the show page URL"
    )


@pytest.mark.asyncio
async def test_get_data_does_not_fetch_calendar_url(monkeypatch):
    """get_data(url) must not fetch self.club.scraping_url (the calendar listing)."""
    scraper = RodneysComedyClubScraper(_club())
    fetched_urls = []

    async def fake_fetch_html(self, url: str):
        fetched_urls.append(url)
        return _show_page_html()

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    show_url = "https://rodneysnewyorkcomedyclub.com/shows/another-show"
    await scraper.get_data(show_url)

    calendar_url = scraper.club.scraping_url
    assert calendar_url not in fetched_urls, (
        "get_data() incorrectly fetched the calendar URL instead of the show page"
    )


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() returns RodneyPageData when HTML contains JSON-LD event data."""
    scraper = RodneysComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str):
        return _show_page_html()

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data("https://rodneysnewyorkcomedyclub.com/shows/test-comic-night")
    assert isinstance(result, RodneyPageData)


@pytest.mark.asyncio
async def test_get_data_exception_returns_none(monkeypatch):
    """get_data() returns None when fetch_html raises."""
    scraper = RodneysComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str):
        raise RuntimeError("network error")

    monkeypatch.setattr(RodneysComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data("https://rodneysnewyorkcomedyclub.com/shows/test-comic-night")
    assert result is None
