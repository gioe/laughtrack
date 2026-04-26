"""
Pipeline smoke test for Hyena's Comedy Nightclub scraper.

Hyena's Dallas uses Prekindle for ticketing. The Prekindle events page
(prekindle.com/events/hyenasdallas) is fully server-rendered and embeds all
upcoming events as a JSON array in a single <script type="application/ld+json">
block, where each event has @type=ComedyEvent.

The generic json_ld scraper (key='json_ld') handles this pattern:
  1. collect_scraping_targets() returns the scraping_url (static strategy)
  2. get_data() fetches the page and extracts all JSON-LD ComedyEvent blocks

These tests verify that the pipeline extracts shows correctly from
a minimal Prekindle-style JSON-LD fixture.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.scrapers.implementations.json_ld.data import JsonLdPageData


SCRAPING_URL = "https://www.prekindle.com/events/hyenasdallas"


def _club() -> Club:
    _c = Club(id=649, name="Hyena's Comedy Nightclub", address='5321 East Mockingbird', website='https://www.hyenascomedynightclub.com/dallas', popularity=0, zip_code='75206', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _prekindle_html(events: list[dict] | None = None) -> str:
    """Minimal Prekindle events page with JSON-LD ComedyEvent blocks."""
    if events is None:
        events = [
            {
                "@context": "http://schema.org",
                "@type": "ComedyEvent",
                "name": "Patrick Warburton",
                "startDate": "2026-04-08",
                "endDate": "2026-04-08",
                "url": "http://www.prekindle.com/event/00001-test-show-dallas",
                "description": "Patrick Warburton",
                "image": "https://d1yf68t7nbxlyn.cloudfront.net/image/id/fake001",
                "organizer": {
                    "name": "Hyenas Dallas",
                    "url": "http://hyenascomedynightclub.com/",
                },
                "location": {
                    "@type": "Place",
                    "name": "Hyena's Dallas",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "5321 East Mockingbird",
                        "addressLocality": "Dallas",
                        "addressRegion": "TX",
                        "postalCode": "75206",
                    },
                },
                "performer": [{"name": "Patrick Warburton", "@type": "MusicGroup"}],
                "offers": {
                    "@type": "AggregateOffer",
                    "name": "Ticket",
                    "url": "http://www.prekindle.com/event/00001-test-show-dallas",
                    "price": "25.00",
                    "lowPrice": "25.00",
                    "highPrice": "35.00",
                    "priceCurrency": "USD",
                    "availability": "InStock",
                },
                "eventStatus": "http://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            }
        ]

    # Prekindle embeds all events as a single JSON array in one script tag
    script_tag = f'<script type="application/ld+json">{json.dumps(events)}</script>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head><title>Hyenas Dallas | Dallas</title>
{script_tag}
</head>
<body><h1>Upcoming Shows</h1></body>
</html>"""


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_scraping_url():
    """Static URL discovery returns the club's scraping_url without HTTP calls."""
    scraper = JsonLdScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_json_ld(monkeypatch):
    """get_data() extracts ComedyEvent blocks from the Prekindle page."""
    scraper = JsonLdScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _prekindle_html()

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, JsonLdPageData), "get_data() did not return JsonLdPageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events from Prekindle JSON-LD fixture"
    assert result.event_list[0].name == "Patrick Warburton"


@pytest.mark.asyncio
async def test_get_data_extracts_multiple_shows(monkeypatch):
    """get_data() extracts all events when the page lists multiple shows."""
    scraper = JsonLdScraper(_club())

    events = [
        {
            "@context": "http://schema.org",
            "@type": "ComedyEvent",
            "name": "Show A",
            "startDate": "2026-04-10",
            "url": "http://www.prekindle.com/event/11111-show-a-dallas",
            "location": {"@type": "Place", "name": "Hyena's Dallas"},
            "offers": {"@type": "AggregateOffer", "url": "http://www.prekindle.com/event/11111-show-a-dallas", "priceCurrency": "USD", "price": "20.00", "availability": "InStock"},
            "description": "",
        },
        {
            "@context": "http://schema.org",
            "@type": "ComedyEvent",
            "name": "Show B",
            "startDate": "2026-04-11",
            "url": "http://www.prekindle.com/event/22222-show-b-dallas",
            "location": {"@type": "Place", "name": "Hyena's Dallas"},
            "offers": {"@type": "AggregateOffer", "url": "http://www.prekindle.com/event/22222-show-b-dallas", "priceCurrency": "USD", "price": "20.00", "availability": "InStock"},
            "description": "",
        },
    ]

    async def fake_fetch_html(self, url: str) -> str:
        return _prekindle_html(events)

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert result is not None
    assert len(result.event_list) == 2, f"Expected 2 events, got {len(result.event_list)}"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_json_ld(monkeypatch):
    """get_data() returns None when the page has no JSON-LD ComedyEvent blocks."""
    scraper = JsonLdScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return "<html><body><h1>No events yet</h1></body></html>"

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert result is None, "get_data() should return None when the page has no JSON-LD events"


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """transformation_pipeline.transform() returns Shows from JsonLdPageData."""
    from laughtrack.core.entities.show.model import Show

    scraper = JsonLdScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _prekindle_html()

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    page_data = await scraper.get_data(SCRAPING_URL)
    assert page_data is not None

    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) > 0, "transformation_pipeline.transform() returned 0 Shows"
    assert all(isinstance(s, Show) for s in shows)
    assert shows[0].name == "Patrick Warburton"
    # Verify Prekindle's date-only startDate ("2026-04-08") is preserved correctly
    assert shows[0].date.year == 2026
    assert shows[0].date.month == 4
    assert shows[0].date.day == 8
