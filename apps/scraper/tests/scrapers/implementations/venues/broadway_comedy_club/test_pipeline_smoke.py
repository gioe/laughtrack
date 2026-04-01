"""
Pipeline smoke test for Broadway Comedy Club scraper.

Exercises collect_scraping_targets() → get_data() against a fixture HTML page
embedding a single eventObjects.push(...) call in the Broadway format.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.scraper import (
    BroadwayComedyClubScraper,
)
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.data import BroadwayEventData


SCRAPING_URL = "broadwaycomedyclub.com/shows"


def _club() -> Club:
    return Club(
        id=99,
        name="Broadway Comedy Club",
        address="",
        website="https://broadwaycomedyclub.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _shows_html() -> str:
    """Minimal HTML with one Broadway eventObjects.push() entry."""
    return """<html><body>
<script>
var eventObjects = [];
eventObjects.push({"id": "12345", "eventDate": "04/15/2026 08:00 PM", "mainArtist": ["Test Comedian"], "isTesseraProduct": false, "externalLink": "https://broadwaycomedyclub.com/shows/12345"});
</script>
<div class="tessera-show-card" id="12345">
  <a href="/shows/12345"><h3 class="card-title my-1">Test Comedian</h3></a>
  <div class="tessera-venue fw-bold">Main Room</div>
</div>
</body></html>"""


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_url(monkeypatch):
    """Default static URL discovery returns the club's scraping_url."""
    scraper = BroadwayComedyClubScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_fixture_html(monkeypatch):
    """get_data() extracts at least one event from the eventObjects.push() fixture."""
    scraper = BroadwayComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _shows_html()

    # Bypass Tessera API enrichment — return events unchanged
    async def fake_enrich(self, events):
        return events

    async def fake_refresh_session_id(self) -> bool:
        return True

    monkeypatch.setattr(BroadwayComedyClubScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(BroadwayComedyClubScraper, "_enrich_events_with_tickets", fake_enrich)
    from laughtrack.core.clients.tessera.client import TesseraClient
    monkeypatch.setattr(TesseraClient, "refresh_session_id", fake_refresh_session_id)

    result = await scraper.get_data(f"https://{SCRAPING_URL}")

    assert isinstance(result, BroadwayEventData), "get_data() did not return BroadwayEventData"
    assert len(result.event_list) > 0, (
        "get_data() returned 0 events from fixture HTML — check eventObjects.push() extraction"
    )
    assert result.event_list[0].mainArtist[0] == "Test Comedian"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data() with at least one event."""
    scraper = BroadwayComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _shows_html()

    async def fake_enrich(self, events):
        return events

    async def fake_refresh_session_id(self) -> bool:
        return True

    monkeypatch.setattr(BroadwayComedyClubScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(BroadwayComedyClubScraper, "_enrich_events_with_tickets", fake_enrich)
    from laughtrack.core.clients.tessera.client import TesseraClient
    monkeypatch.setattr(TesseraClient, "refresh_session_id", fake_refresh_session_id)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
