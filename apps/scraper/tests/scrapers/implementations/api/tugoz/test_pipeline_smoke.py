"""Pipeline smoke tests for the generic Tugoz scraper (TASK-3194)."""

from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tugoz.data import TugozPageData
from laughtrack.scrapers.implementations.api.tugoz.extractor import TugozExtractor
from laughtrack.scrapers.implementations.api.tugoz.scraper import TugozScraper

CONFIG_JS = """
const SITE_CONFIG = {
  LIVE_EVENTS: {
    lt10: 110095,
    openmic: 112933,
  }
};
"""


def _club(metadata=None) -> Club:
    club = Club(
        id=901,
        name="Masala Comedy Club",
        address="Sunnyvale Theatre, Sunnyvale, CA 94087, USA",
        website="https://masalacc.org/",
        popularity=0,
        zip_code="94087",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="tugoz",
        source_url="https://masalacc.org/config.js?v=2",
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _payload(event_id=112933, name="Open Mic", date="2099-08-27 20:00:00") -> dict:
    return {
        "einfo": {
            "eventid": event_id,
            "name": name,
            "date": date,
            "tziso": "America/Los_Angeles",
            "eventurl": "https://www.masalacc.org/open-mic/",
            "about": "<p>Come join us for a fun-filled evening of laughs.</p>",
            "venue": "India Community Center",
            "status": "Draft",
            "live": 0,
            "etp": "Ticket",
        }
    }


def test_extract_live_event_ids_from_config():
    assert TugozExtractor.extract_live_event_ids(CONFIG_JS) == [110095, 112933]
    assert TugozExtractor.extract_live_event_ids(CONFIG_JS, allowed_keys=["openmic"]) == [112933]


@pytest.mark.asyncio
async def test_collect_scraping_targets_reads_config_and_filters_keys():
    scraper = TugozScraper(_club(metadata={"event_keys": ["openmic"]}))
    scraper.fetch_html = AsyncMock(return_value=CONFIG_JS)

    targets = await scraper.collect_scraping_targets()

    assert targets == ["https://static.tugoz.com/api/json/www/v4/e-112933"]


@pytest.mark.asyncio
async def test_get_data_returns_future_event_page_data():
    scraper = TugozScraper(_club())
    scraper.fetch_json = AsyncMock(return_value=_payload())

    result = await scraper.get_data("https://static.tugoz.com/api/json/www/v4/e-112933")

    assert isinstance(result, TugozPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Open Mic"
    assert result.event_list[0].date.tzinfo == ZoneInfo("America/Los_Angeles")


@pytest.mark.asyncio
async def test_get_data_skips_stale_event():
    scraper = TugozScraper(_club())
    scraper.fetch_json = AsyncMock(return_value=_payload(event_id=110095, name="Laugh Ticket 9", date="2026-05-21 20:00:00"))

    assert await scraper.get_data("https://static.tugoz.com/api/json/www/v4/e-110095") is None


def test_event_to_show_builds_fallback_ticket():
    event = TugozExtractor.event_from_payload(_payload())
    assert event is not None

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Open Mic"
    assert show.show_page_url == "https://www.masalacc.org/open-mic"
    assert show.room == "India Community Center"
    assert show.description == "Come join us for a fun-filled evening of laughs."
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://www.masalacc.org/open-mic/"
    assert show.tickets[0].price is None
    assert isinstance(show.date, datetime)
