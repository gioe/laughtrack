"""
Pipeline smoke test for Stomping Ground Comedy Theater scraper.

Stomping Ground uses Humanitix for ticketing. The Humanitix host page
(events.humanitix.com/host/stomping-ground-comedy) serves all upcoming
events as JSON-LD @type=Event blocks in the server-rendered HTML.

The generic json_ld scraper (key='json_ld') handles this pattern:
  1. collect_scraping_targets() returns the scraping_url (static strategy)
  2. get_data() fetches the page and extracts all JSON-LD Event blocks

These tests verify that the pipeline extracts shows correctly from
a minimal Humanitix-style JSON-LD fixture.
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


SCRAPING_URL = "https://events.humanitix.com/host/stomping-ground-comedy"


def _club() -> Club:
    _c = Club(id=99, name='Stomping Ground Comedy Theater', address='1350 Manufacturing St #109', website='https://stompinggroundcomedy.org', popularity=0, zip_code='75207', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _humanitix_host_html(events: list[dict] | None = None) -> str:
    """Minimal Humanitix host page with JSON-LD Event blocks per upcoming show."""
    if events is None:
        events = [
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Thunderdome - An Improv Show",
                "url": "https://events.humanitix.com/thunderdome-35tyngf3",
                "startDate": "2026-04-03T20:00:00-05:00",
                "endDate": "2026-04-03T22:15:00-05:00",
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "location": {
                    "@type": "Place",
                    "name": "Stomping Ground Comedy Theater & Training Center",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "1350 Manufacturing St #109",
                        "addressLocality": "Dallas",
                        "addressRegion": "TX",
                        "postalCode": "75207",
                        "addressCountry": "US",
                    },
                },
                "offers": [
                    {
                        "@type": "Offer",
                        "name": "General Admission",
                        "price": "10",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock",
                        "url": "https://events.humanitix.com/thunderdome-35tyngf3/tickets",
                    }
                ],
                "description": "An evening of short-form and long-form improv comedy.",
            },
        ]

    script_tags = "\n".join(
        f'<script type="application/ld+json">{json.dumps(e)}</script>' for e in events
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head><title>Stomping Ground Comedy - Upcoming Events</title>
{script_tags}
</head>
<body><h1>Upcoming Events</h1></body>
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
    """get_data() extracts events from Humanitix JSON-LD Event blocks."""
    scraper = JsonLdScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _humanitix_host_html()

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, JsonLdPageData), "get_data() did not return JsonLdPageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events from Humanitix JSON-LD fixture"
    assert result.event_list[0].name == "Thunderdome - An Improv Show"


@pytest.mark.asyncio
async def test_get_data_extracts_multiple_shows(monkeypatch):
    """get_data() extracts all events when the host page lists multiple shows."""
    scraper = JsonLdScraper(_club())

    events = [
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Show A",
            "url": "https://events.humanitix.com/show-a",
            "startDate": "2026-04-10T19:00:00-05:00",
            "location": {"@type": "Place", "name": "Stomping Ground"},
            "offers": [],
            "description": "",
        },
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Show B",
            "url": "https://events.humanitix.com/show-b",
            "startDate": "2026-04-17T19:00:00-05:00",
            "location": {"@type": "Place", "name": "Stomping Ground"},
            "offers": [],
            "description": "",
        },
    ]

    async def fake_fetch_html(self, url: str) -> str:
        return _humanitix_host_html(events)

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert result is not None
    assert len(result.event_list) == 2, f"Expected 2 events, got {len(result.event_list)}"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_json_ld(monkeypatch):
    """get_data() returns None when the page has no JSON-LD Event blocks."""
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
        return _humanitix_host_html()

    monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html)

    page_data = await scraper.get_data(SCRAPING_URL)
    assert page_data is not None

    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) > 0, "transformation_pipeline.transform() returned 0 Shows"
    assert all(isinstance(s, Show) for s in shows)
    assert shows[0].name == "Thunderdome - An Improv Show"
