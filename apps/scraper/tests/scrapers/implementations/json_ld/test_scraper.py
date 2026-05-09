"""Tests for the shared JsonLdScraper.

The scraper itself is a thin wrapper around EventExtractor (covered in
test_event_extractor.py). The behavior unique to the scraper class is the
optional ``location_name_filter`` metadata key, which lets a single
multi-venue calendar page be reused by per-venue clubs without a bespoke
scraper subclass (see TASK-2068).
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.json_ld.data import JsonLdPageData
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper


def _wrap_ldjson(obj) -> str:
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


def _multi_venue_html() -> str:
    """Two events at different venues on a single calendar page."""
    river_event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Friday Headliner",
        "startDate": "2099-06-05T20:00:00-04:00",
        "url": "https://example.com/events/friday",
        "location": {
            "@type": "Place",
            "name": "River: A Waterfront Restaurant and Bar",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "1 Riverside Dr",
                "addressLocality": "Wethersfield",
                "addressRegion": "CT",
                "postalCode": "06109",
                "addressCountry": "US",
            },
        },
    }
    other_venue_event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Saturday Showcase",
        "startDate": "2099-06-06T20:00:00-04:00",
        "url": "https://example.com/events/saturday",
        "location": {
            "@type": "Place",
            "name": "Some Other Venue",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "55 Elm St",
                "addressLocality": "Hartford",
                "addressRegion": "CT",
                "postalCode": "06103",
                "addressCountry": "US",
            },
        },
    }
    return f"<html><head>{_wrap_ldjson([river_event, other_venue_event])}</head></html>"


def _make_club(metadata: dict | None = None) -> Club:
    club = Club(
        id=1350,
        name="Brew HaHa Comedy at River",
        address="1 Riverside Dr",
        website="https://comedycraftbeer.com",
        popularity=0,
        zip_code="06109",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        rate_limit=1.0,
        max_retries=1,
        timeout=5,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="json_ld",
        source_url="https://comedycraftbeer.com/calendar",
        external_id=None,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


class TestLocationNameFilter:
    """Verify the location_name_filter metadata key narrows multi-venue calendar pages."""

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_events(self, monkeypatch):
        scraper = JsonLdScraper(_make_club())

        async def fake_fetch_html(self, url):
            return _multi_venue_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert isinstance(result, JsonLdPageData)
        names = sorted(e.name for e in result.event_list)
        assert names == ["Friday Headliner", "Saturday Showcase"]

    @pytest.mark.asyncio
    async def test_filter_keeps_only_matching_location(self, monkeypatch):
        scraper = JsonLdScraper(_make_club(metadata={
            "location_name_filter": "River: A Waterfront Restaurant and Bar",
        }))

        async def fake_fetch_html(self, url):
            return _multi_venue_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert isinstance(result, JsonLdPageData)
        assert [e.name for e in result.event_list] == ["Friday Headliner"]
        assert result.event_list[0].location.name == "River: A Waterfront Restaurant and Bar"

    @pytest.mark.asyncio
    async def test_filter_with_no_matches_returns_none(self, monkeypatch):
        scraper = JsonLdScraper(_make_club(metadata={
            "location_name_filter": "Venue That Does Not Exist On This Page",
        }))

        async def fake_fetch_html(self, url):
            return _multi_venue_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert result is None
