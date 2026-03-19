import importlib.util
import json
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent, Place, PostalAddress
from laughtrack.scrapers.implementations.venues.uptown_theater import scraper as uptown_module
from laughtrack.scrapers.implementations.venues.uptown_theater.data import UptownTheaterPageData
from laughtrack.scrapers.implementations.venues.uptown_theater.scraper import UptownTheaterScraper


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_club() -> Club:
    return Club(
        id=80,
        name="Uptown Theater",
        address="270 Broadway",
        website="https://www.uptownpvd.com",
        scraping_url="www.uptownpvd.com/events",
        popularity=0,
        zip_code="02903",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        scraper="uptown_theater",
        eventbrite_id=None,
        ticketmaster_id=None,
        seatengine_id=None,
        rate_limit=1.0,
        max_retries=1,
        timeout=5,
    )


def _make_event(label: str) -> JsonLdEvent:
    return JsonLdEvent(
        name=f"Event {label}",
        start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
        location=Place(
            name="Uptown Theater",
            address=PostalAddress(
                street_address="270 Broadway",
                address_locality="Providence",
                address_region="RI",
                postal_code="02903",
                address_country="US",
            ),
        ),
        offers=[],
        url=f"https://www.uptownpvd.com/events/{label}",
        description="",
    )


def _make_collection_page_html(event_urls: list) -> str:
    """Build a minimal HTML page with a CollectionPage JSON-LD listing."""
    items = [{"@type": "ListItem", "position": i + 1, "url": url} for i, url in enumerate(event_urls)]
    payload = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Upcoming Events | Uptown Theater",
        "url": "https://www.uptownpvd.com/events",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": items,
        },
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(payload)}</script></head><body></body></html>'


def _make_event_page_html(name: str) -> str:
    """Build a minimal HTML page with a ComedyEvent JSON-LD."""
    payload = {
        "@context": "https://schema.org",
        "@type": "ComedyEvent",
        "name": name,
        "startDate": "2026-04-01T19:30:00-04:00",
        "url": f"https://www.uptownpvd.com/events/{name.lower().replace(' ', '-')}",
        "location": {
            "@type": "Place",
            "name": "Uptown Theater",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "270 Broadway",
                "addressLocality": "Providence",
                "addressRegion": "RI",
                "postalCode": "02903",
                "addressCountry": "US",
            },
        },
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(payload)}</script></head><body></body></html>'


class FakeBatchScraper:
    """Stub that returns a preset result from process_batch."""

    def __init__(self, result):
        self._result = result

    def __call__(self, logger_context, config=None):
        return self

    async def process_batch(self, items, processor, description=None):
        return self._result


# ---------------------------------------------------------------------------
# _extract_event_urls
# ---------------------------------------------------------------------------

class TestExtractEventUrls:
    def setup_method(self):
        self.scraper = UptownTheaterScraper(_make_club())

    def test_returns_absolute_urls_from_collection_page(self):
        html = _make_collection_page_html([
            "https://www.uptownpvd.com/events/show-a",
            "https://www.uptownpvd.com/events/show-b",
        ])
        result = self.scraper._extract_event_urls(html, "https://www.uptownpvd.com/events")
        assert result == [
            "https://www.uptownpvd.com/events/show-a",
            "https://www.uptownpvd.com/events/show-b",
        ]

    def test_resolves_relative_urls_against_listing_url(self):
        html = _make_collection_page_html(["/events/relative-show"])
        result = self.scraper._extract_event_urls(html, "https://www.uptownpvd.com/events")
        assert result == ["https://www.uptownpvd.com/events/relative-show"]

    def test_returns_empty_list_when_no_json_ld(self):
        result = self.scraper._extract_event_urls("<html></html>", "https://www.uptownpvd.com/events")
        assert result == []

    def test_returns_empty_list_when_no_collection_page(self):
        payload = json.dumps({"@context": "https://schema.org", "@type": "WebPage"})
        html = f'<html><head><script type="application/ld+json">{payload}</script></head></html>'
        result = self.scraper._extract_event_urls(html, "https://www.uptownpvd.com/events")
        assert result == []

    def test_skips_non_dict_main_entity(self):
        """Guard: mainEntity as a non-dict (e.g. array) should not raise."""
        payload = json.dumps({
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "mainEntity": ["not", "a", "dict"],
        })
        html = f'<html><head><script type="application/ld+json">{payload}</script></head></html>'
        result = self.scraper._extract_event_urls(html, "https://www.uptownpvd.com/events")
        assert result == []


# ---------------------------------------------------------------------------
# get_data
# ---------------------------------------------------------------------------

class TestGetData:
    def setup_method(self):
        self.scraper = UptownTheaterScraper(_make_club())

    @pytest.mark.asyncio
    async def test_returns_none_when_listing_fetch_fails(self, monkeypatch):
        async def fake_fetch_html(self, url):
            return None

        monkeypatch.setattr(UptownTheaterScraper, "fetch_html", fake_fetch_html, raising=False)
        result = await self.scraper.get_data("https://www.uptownpvd.com/events")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_event_urls_found(self, monkeypatch):
        async def fake_fetch_html(self, url):
            return "<html></html>"

        monkeypatch.setattr(UptownTheaterScraper, "fetch_html", fake_fetch_html, raising=False)
        result = await self.scraper.get_data("https://www.uptownpvd.com/events")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_page_data_with_flattened_events(self, monkeypatch):
        listing_html = _make_collection_page_html([
            "https://www.uptownpvd.com/events/show-a",
            "https://www.uptownpvd.com/events/show-b",
        ])

        async def fake_fetch_html(self, url):
            return listing_html

        # BatchScraper returns nested lists (one per event URL) — verify flattening
        fake_batch = FakeBatchScraper(result=[
            [_make_event("A")],
            [_make_event("B1"), _make_event("B2")],
        ])
        monkeypatch.setattr(UptownTheaterScraper, "fetch_html", fake_fetch_html, raising=False)
        monkeypatch.setattr(uptown_module, "BatchScraper", fake_batch, raising=True)

        result = await self.scraper.get_data("https://www.uptownpvd.com/events")

        assert isinstance(result, UptownTheaterPageData)
        assert len(result.event_list) == 3
        assert all(isinstance(e, JsonLdEvent) for e in result.event_list)

    @pytest.mark.asyncio
    async def test_returns_none_when_all_event_pages_empty(self, monkeypatch):
        listing_html = _make_collection_page_html(["https://www.uptownpvd.com/events/show-a"])

        async def fake_fetch_html(self, url):
            return listing_html

        fake_batch = FakeBatchScraper(result=[[]])  # no events extracted
        monkeypatch.setattr(UptownTheaterScraper, "fetch_html", fake_fetch_html, raising=False)
        monkeypatch.setattr(uptown_module, "BatchScraper", fake_batch, raising=True)

        result = await self.scraper.get_data("https://www.uptownpvd.com/events")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self, monkeypatch):
        async def raise_error(self, url):
            raise RuntimeError("network error")

        monkeypatch.setattr(UptownTheaterScraper, "fetch_html", raise_error, raising=False)
        result = await self.scraper.get_data("https://www.uptownpvd.com/events")
        assert result is None
