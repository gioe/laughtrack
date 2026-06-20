"""Tests for the BrassTix inline-calendar scraper."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.adapters.config import ScraperMapping
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.brasstix.extractor import (
    extract_brasstix_events,
)
from laughtrack.scrapers.implementations.api.brasstix.scraper import BrassTixScraper


_CALENDAR_URL = "https://brasstix.com/pmt/calendar.php?Show=DrunkChicago"


def _club(metadata=None) -> Club:
    club = Club(
        id=2990,
        name="Drunk Shakespeare Chicago",
        address="182 N Wabash Ave",
        website="https://drunkshakespeare.com/",
        popularity=0,
        zip_code="60601",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Chicago",
        state="IL",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="brasstix",
        source_url=_CALENDAR_URL,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _calendar_html() -> str:
    return """
    <html><head><script>
    eventArray = [{title:'\\nSOLD OUT',subtitle:'',eventid:'4104',start:'2030-03-01 13:00:00',url:''
                ,backgroundColor:'#F2A427',borderColor:'#5c5859'
                ,imageurl:'',ShowName:'Drunk Chicago'}];
    eventArray.push.apply(eventArray,[{title:'\\nDRUNK ROMEO & JULIET\\nSELLING OUT',subtitle:'',eventid:'6925',start:'2026-06-20 17:00:00',url:'payment1.php?Show=RJChicago&EventId=6925&EventTime=2026-06-20 17:00:00&v=5'
                ,backgroundColor:'#F27B2C',borderColor:'#5c5859'
                ,imageurl:'',ShowName:'RJChicago'},{title:'\\nDRUNK ROMEO & JULIET',subtitle:'BEST AVAILABILITY',eventid:'6928',start:'2026-06-21 17:00:00',url:'payment1.php?Show=RJChicago&EventId=6928&EventTime=2026-06-21 17:00:00&v=5'
                ,backgroundColor:'#e60073',borderColor:'#5c5859'
                ,imageurl:'',ShowName:'RJChicago'}]);
    </script></head></html>
    """


def test_extract_brasstix_events_skips_sold_out_without_purchase_url():
    events = extract_brasstix_events(_calendar_html(), _CALENDAR_URL)

    assert [event.event_id for event in events] == ["6925", "6928"]
    assert events[0].title == "DRUNK ROMEO & JULIET"
    assert events[0].availability_label == "SELLING OUT"
    assert events[0].ticket_url == (
        "https://brasstix.com/pmt/payment1.php?Show=RJChicago&EventId=6925"
        "&EventTime=2026-06-20%2017:00:00&v=5"
    )


@pytest.mark.asyncio
async def test_get_data_extracts_calendar_events(monkeypatch):
    scraper = BrassTixScraper(_club())

    async def fake_fetch(url):
        assert url == _CALENDAR_URL
        return _calendar_html()

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    data = await scraper.get_data(_CALENDAR_URL)

    assert data is not None
    assert len(data.event_list) == 2


@pytest.mark.asyncio
async def test_scrape_async_transforms_calendar_events_to_shows(monkeypatch):
    scraper = BrassTixScraper(_club())

    async def fake_fetch(url):
        return _calendar_html()

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    shows = await scraper.scrape_async()

    assert len(shows) == 2
    assert {show.name for show in shows} == {"DRUNK ROMEO & JULIET"}
    assert all(show.club_id == 2990 for show in shows)
    assert all(show.date.tzinfo is not None for show in shows)
    assert all(show.tickets for show in shows)


def test_scraper_key_is_discoverable():
    scraper_class = ScraperMapping().scraper_class_map.get("brasstix")
    assert scraper_class is BrassTixScraper
