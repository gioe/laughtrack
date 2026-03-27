"""
Pipeline smoke test for Uptown Theater scraper.

Exercises collect_scraping_targets() → get_data() using JSON-LD fixtures:
 1. A CollectionPage listing page containing event URLs
 2. Individual event pages containing ComedyEvent JSON-LD
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.uptown_theater.scraper import UptownTheaterScraper
from laughtrack.scrapers.implementations.venues.uptown_theater.data import UptownTheaterPageData


LISTING_URL = "https://uptownpvd.com/events"
EVENT_URL = "https://uptownpvd.com/events/comedy-showcase"
SCRAPING_URL = "uptownpvd.com/events"


def _club() -> Club:
    return Club(
        id=99,
        name="Uptown Theater",
        address="",
        website="https://uptownpvd.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _listing_html() -> str:
    """HTML with a CollectionPage JSON-LD containing one event URL."""
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "url": EVENT_URL},
            ],
        },
    })
    return f"""<html><head>
<script type="application/ld+json">{ld}</script>
</head><body></body></html>"""


def _event_html(name: str = "Comedy Showcase", start_date: str = "2026-04-20T20:00:00") -> str:
    """HTML with a ComedyEvent JSON-LD block."""
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "ComedyEvent",
        "name": name,
        "startDate": start_date,
        "url": EVENT_URL,
        "location": {"@type": "Place", "name": "Uptown Theater"},
        "offers": {"@type": "Offer", "url": EVENT_URL, "price": "20", "priceCurrency": "USD"},
    })
    return f"""<html><head>
<script type="application/ld+json">{ld}</script>
</head><body><h1>{name}</h1></body></html>"""


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_url(monkeypatch):
    """Static URL discovery returns the club's scraping_url without HTTP calls."""
    scraper = UptownTheaterScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_json_ld(monkeypatch):
    """get_data() discovers event URLs from CollectionPage JSON-LD and extracts events."""
    scraper = UptownTheaterScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        if url == EVENT_URL or "comedy-showcase" in url:
            return _event_html()
        return _listing_html()

    monkeypatch.setattr(UptownTheaterScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)

    assert isinstance(result, UptownTheaterPageData), "get_data() did not return UptownTheaterPageData"
    assert len(result.event_list) > 0, (
        "get_data() returned 0 events — check CollectionPage JSON-LD extraction and ComedyEvent parsing"
    )
    assert result.event_list[0].name == "Comedy Showcase"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = UptownTheaterScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        if "comedy-showcase" in url:
            return _event_html()
        return _listing_html()

    monkeypatch.setattr(UptownTheaterScraper, "fetch_html", fake_fetch_html)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
