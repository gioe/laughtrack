"""
Pipeline smoke test for Grove34 scraper.

Exercises collect_scraping_targets() (listing page → show URLs) → get_data()
(show detail page → JSON-LD event) using minimal HTML fixtures.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.event.grove34 import Grove34Event
from laughtrack.scrapers.implementations.venues.grove_34.scraper import Grove34Scraper
from laughtrack.scrapers.implementations.venues.grove_34.data import Grove34PageData


SHOW_URL = "https://grove34.com/shows/comedy-night-april"
LISTING_URL = "https://grove34.com"


def _club() -> Club:
    return Club(
        id=99,
        name="Grove 34",
        address="",
        website="https://grove34.com",
        scraping_url=LISTING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _listing_html() -> str:
    """Minimal listing page HTML containing one /shows/ link."""
    return f"""<html><body>
<a href="{SHOW_URL}">Comedy Night April</a>
<a href="https://grove34.com/about">About</a>
</body></html>"""


def _show_detail_html(title: str = "Comedy Night April", start_date: str = "2026-04-15T20:00:00") -> str:
    """Minimal show detail HTML with a JSON-LD Event block."""
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Event",
        "name": title,
        "startDate": start_date,
        "description": "A great night of comedy",
    })
    return f"""<html><head>
<script type="application/ld+json">{ld}</script>
</head><body><h1>{title}</h1></body></html>"""


def _make_fake_fetch_html_bare(listing_html: str, show_html: str):
    async def fake_fetch(self, url: str) -> str:
        if "/shows/" in url:
            return show_html
        return listing_html
    return fake_fetch


def _make_event(title: str = "Comedy Night") -> Grove34Event:
    return Grove34Event(
        title=title,
        start_date="2099-01-01T20:00:00.000Z",
        show_page_url=SHOW_URL,
        timezone_id="America/New_York",
    )


def test_transformation_pipeline_produces_shows():
    club = _club()
    scraper = Grove34Scraper(club)
    events = [_make_event("Show A"), _make_event("Show B")]
    page_data = Grove34PageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check can_transform() and that the transformer is registered "
        "with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_show_urls(monkeypatch):
    """collect_scraping_targets() finds /shows/ links on the listing page."""
    scraper = Grove34Scraper(_club())

    async def fake_fetch(self, url: str) -> str:
        return _listing_html()

    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert all("/shows/" in u for u in urls), f"Unexpected URLs: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_event_from_json_ld(monkeypatch):
    """get_data() extracts a Grove34Event from a JSON-LD Event block."""
    scraper = Grove34Scraper(_club())

    async def fake_fetch(self, url: str) -> str:
        return _show_detail_html()

    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch)

    result = await scraper.get_data(SHOW_URL)

    assert isinstance(result, Grove34PageData), "get_data() did not return Grove34PageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events from JSON-LD fixture"
    assert result.event_list[0].title == "Comedy Night April"
    assert result.event_list[0].show_page_url == SHOW_URL


@pytest.mark.asyncio
async def test_get_data_skips_past_events(monkeypatch):
    """get_data() returns None for events whose start_date is in the past."""
    scraper = Grove34Scraper(_club())

    async def fake_fetch(self, url: str) -> str:
        return _show_detail_html(start_date="2025-12-12T02:00:00.000Z")

    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch)

    result = await scraper.get_data(SHOW_URL)
    assert result is None, "get_data() should return None for a past event"


@pytest.mark.asyncio
async def test_get_data_includes_future_events(monkeypatch):
    """get_data() returns data for events whose start_date is in the future."""
    scraper = Grove34Scraper(_club())

    async def fake_fetch(self, url: str) -> str:
        return _show_detail_html(start_date="2099-01-01T20:00:00.000Z")

    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch)

    result = await scraper.get_data(SHOW_URL)
    assert result is not None, "get_data() should return data for a future event"
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() → get_data() produces at least one event."""
    scraper = Grove34Scraper(_club())

    monkeypatch.setattr(
        Grove34Scraper,
        "fetch_html_bare",
        _make_fake_fetch_html_bare(_listing_html(), _show_detail_html()),
    )

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
