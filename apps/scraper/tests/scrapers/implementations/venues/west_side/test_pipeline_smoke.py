"""
Pipeline smoke test for West Side Comedy Club scraper.

Exercises collect_scraping_targets() → get_data() against Punchup hydration HTML.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.west_side.scraper import WestSideScraper
from laughtrack.scrapers.implementations.venues.west_side.data import WestSidePageData


SCRAPING_URL = "westsidecomedyclub.com/calendar"


def _club() -> Club:
    _c = Club(id=99, name='West Side Comedy Club', address='', website='https://westsidecomedyclub.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _punchup_html() -> str:
    """Return minimal Punchup hydration HTML with one upcoming show."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "386befdb-9075-4a84-8adc-4e5e5c945fbc"],
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
                                    "title": "West Side Comedy Night",
                                    "datetime": "2026-04-20T20:00:00",
                                    "ticket_link": "https://event.tixologi.com/event/42/tickets",
                                    "tixologi_event_id": "42",
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
    scraper = WestSideScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any(SCRAPING_URL in u for u in urls), f"Expected scraping URL in targets, got: {urls}"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_punchup_html(monkeypatch):
    """get_data() extracts at least one show from Punchup hydration HTML."""
    scraper = WestSideScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(WestSideScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data(f"https://{SCRAPING_URL}")

    assert isinstance(result, WestSidePageData), "get_data() did not return WestSidePageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events from Punchup HTML fixture"
    assert result.event_list[0].title == "West Side Comedy Night"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = WestSideScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(WestSideScraper, "fetch_html_bare", fake_fetch_html_bare)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
