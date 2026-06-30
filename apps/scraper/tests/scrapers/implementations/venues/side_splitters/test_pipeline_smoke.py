"""
Pipeline smoke test for Side Splitters Comedy Club scraper.

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
from laughtrack.scrapers.implementations.venues.side_splitters.data import (
    SideSplittersPageData,
)
from laughtrack.scrapers.implementations.venues.side_splitters.scraper import (
    SideSplittersScraper,
)

SCRAPING_URL = "https://sidesplitterscomedytampa.punchup.live/"


def _club() -> Club:
    club = Club(
        id=1056,
        name="Side Splitters Comedy Club",
        address="12938 N Dale Mabry Hwy, Tampa, FL 33618",
        website="https://sidesplitterscomedy.com",
        popularity=0,
        zip_code="33618",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="side_splitters",
        source_url=SCRAPING_URL,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _punchup_html(*, include_venue_shows_query: bool = False) -> str:
    """Return minimal Punchup hydration HTML with one upcoming show."""
    queries = [
        {
            "queryKey": ["venuePageCarousel", "side-splitters-venue-uuid"],
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
                                "title": "Side Splitters Comedy Night",
                                "datetime": "2026-07-03T19:30:00",
                                "ticket_link": "https://event.tixologi.com/event/11876/tickets",
                                "tixologi_event_id": "11876",
                                "is_sold_out": False,
                                "metadata_text": "Live stand-up in Tampa.",
                                "show_comedians": [],
                            },
                        }
                    ],
                },
                "status": "success",
            },
        }
    ]
    if include_venue_shows_query:
        queries.append(
            {
                "queryKey": [
                    "venueShows",
                    "ffff9f1c-2b54-473a-a167-80849d68f48a",
                ],
                "state": {
                    "data": [_show_payload(i) for i in range(20)],
                    "status": "success",
                },
            }
        )

    payload = {"queries": queries}
    return f"<html><body><script>{json.dumps(payload)}</script></body></html>"


def _show_payload(index: int) -> dict:
    return {
        "id": f"show-uuid-{index}",
        "title": f"Side Splitters Show {index}",
        "datetime": "2026-07-03T19:30:00",
        "ticket_link": f"https://event.tixologi.com/event/{11876 + index}/tickets",
        "tixologi_event_id": str(11876 + index),
        "is_sold_out": False,
        "metadata_text": None,
        "show_comedians": [],
    }


def _stub_tixologi(monkeypatch):
    """Bypass Tixologi enrichment in tests that do not exercise pricing."""

    async def identity(self, shows):
        return shows

    monkeypatch.setattr(SideSplittersScraper, "_enrich_tixologi_tickets", identity)


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_punchup_url():
    """Static URL discovery returns the active Punchup source URL."""
    scraper = SideSplittersScraper(_club())

    urls = await scraper.collect_scraping_targets()

    assert urls == [SCRAPING_URL]


@pytest.mark.asyncio
async def test_get_data_returns_events_from_punchup_html(monkeypatch):
    """get_data() extracts shows from Punchup hydration HTML."""
    scraper = SideSplittersScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html()

    monkeypatch.setattr(SideSplittersScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SideSplittersPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Side Splitters Comedy Night"
    assert result.event_list[0].tixologi_event_id == "11876"


@pytest.mark.asyncio
async def test_get_data_fetches_all_punchup_pages(monkeypatch):
    """get_data() follows Punchup limit/offset pages beyond the embedded first 20 shows."""
    scraper = SideSplittersScraper(_club())
    calls = []

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _punchup_html(include_venue_shows_query=True)

    async def fake_fetch_json(self, url: str, **kwargs):
        calls.append(url)
        if "offset=20" in url:
            return [_show_payload(i) for i in range(20, 40)]
        if "offset=40" in url:
            return [_show_payload(40), _show_payload(41)]
        return [_show_payload(i) for i in range(20)]

    monkeypatch.setattr(SideSplittersScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(SideSplittersScraper, "fetch_json", fake_fetch_json)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SideSplittersPageData)
    assert len(result.event_list) == 42
    assert any("offset=20" in url for url in calls)
    assert any("offset=40" in url for url in calls)
