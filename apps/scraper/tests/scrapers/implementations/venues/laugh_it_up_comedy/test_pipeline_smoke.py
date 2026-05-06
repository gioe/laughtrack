"""
Pipeline smoke test for LAUGH IT UP COMEDY CLUB scraper.

Exercises collect_scraping_targets() -> get_data() against Punchup hydration HTML.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.laugh_it_up_comedy.data import (
    LaughItUpComedyPageData,
)
from laughtrack.scrapers.implementations.venues.laugh_it_up_comedy.scraper import (
    LaughItUpComedyScraper,
)

SCRAPING_URL = "https://www.laughitupcomedy.com/calendar"


def _club() -> Club:
    _c = Club(
        id=485,
        name="LAUGH IT UP COMEDY CLUB",
        address="",
        website="https://www.laughitupcomedy.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    _c.active_scraping_source = ScrapingSource(
        id=313,
        club_id=_c.id,
        platform="custom",
        scraper_key="laugh_it_up_comedy",
        source_url=SCRAPING_URL,
        external_id=None,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _punchup_html() -> str:
    """Return minimal Punchup hydration HTML with one upcoming show."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "laugh-it-up-venue-uuid"],
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
                                    "title": "Laughing Stock",
                                    "datetime": "2026-05-08T19:00:00",
                                    "ticket_link": "https://www.laughitupcomedy.com/shows/show-uuid-1",
                                    "tixologi_event_id": None,
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
async def test_collect_scraping_targets_returns_calendar_url():
    """Static URL discovery returns the club's active scraping source URL."""
    scraper = LaughItUpComedyScraper(_club())

    urls = await scraper.collect_scraping_targets()

    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert SCRAPING_URL in urls


@pytest.mark.asyncio
async def test_get_data_returns_events_from_punchup_html(monkeypatch):
    """get_data() extracts at least one show from Punchup hydration HTML."""
    scraper = LaughItUpComedyScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(LaughItUpComedyScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, LaughItUpComedyPageData)
    assert len(result.event_list) > 0
    assert result.event_list[0].title == "Laughing Stock"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = LaughItUpComedyScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(LaughItUpComedyScraper, "fetch_html_bare", fake_fetch_html_bare)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
