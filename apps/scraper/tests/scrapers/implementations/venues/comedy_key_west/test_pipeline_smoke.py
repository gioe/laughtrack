"""
Pipeline smoke test for Comedy Key West scraper.

Exercises collect_scraping_targets() → get_data() against Punchup hydration HTML.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.comedy_key_west.scraper import ComedyKeyWestScraper
from laughtrack.scrapers.implementations.venues.comedy_key_west.data import ComedyKeyWestPageData


SCRAPING_URL = "comedykeywest.com/shows"


def _club() -> Club:
    return Club(
        id=99,
        name="Comedy Key West",
        address="",
        website="https://comedykeywest.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _punchup_html() -> str:
    """Return minimal Punchup hydration HTML with one upcoming show."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "ckw-venue-uuid"],
                "state": {
                    "data": {
                        "mode": "custom",
                        "items": [
                            {
                                "type": "show",
                                "id": "item-uuid-1",
                                "order": 1,
                                "show": {
                                    "id": "show-uuid-1",
                                    "title": "Key West Comedy Night",
                                    "datetime": "2026-04-15T20:00:00",
                                    "ticket_link": "https://event.tixologi.com/event/99/tickets",
                                    "tixologi_event_id": "99",
                                    "is_sold_out": False,
                                    "metadata_text": None,
                                    "show_comedians": [],
                                },
                            }
                        ],
                    },
                    "status": "success",
                },
            }
        ]
    }
    return f"<html><body><script>{json.dumps(payload)}</script></body></html>"


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_url(monkeypatch):
    """Static URL discovery returns the club's scraping_url without HTTP calls."""
    scraper = ComedyKeyWestScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_punchup_html(monkeypatch):
    """get_data() extracts at least one show from Punchup hydration HTML."""
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data(f"https://{SCRAPING_URL}")

    assert isinstance(result, ComedyKeyWestPageData), "get_data() did not return ComedyKeyWestPageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events from Punchup HTML fixture"
    assert result.event_list[0].title == "Key West Comedy Night"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
