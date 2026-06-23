"""Tests for the opt-in title filter on TicketWebScraper (TASK-3248).

Mixed-use TicketWeb venues (live-music rooms that also host a comedy series)
expose every event on the same calendar. The filter keeps only the comedy
shows when configured via scraping_sources.metadata:
  - include_title_patterns: keep only titles matching the comedy-series allowlist
  - exclude_title_patterns: drop titles matching the blocklist
Both are off by default, so pure-comedy TicketWeb sources are unchanged.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticketweb.scraper import TicketWebScraper


CALENDAR_URL = "https://neckofthewoodssf.example/events"

# A mixed-use live-music calendar: 2 comedy series + 3 band/DJ acts.
_MIXED = [
    ("Best of San Francisco Stand-Up Comedy", "2099-07-10 19:30:00", "/event/best-of-sf-1"),
    ("Clement St Comedy", "2099-07-17 19:30:00", "/event/clement-st-1"),
    ("Vicious Cycle of Time / Diablura", "2099-07-11 20:00:00", "/event/vicious-1"),
    ("Sinister Sounds Fest", "2099-07-12 20:00:00", "/event/sinister-1"),
    ("FlipaBeatClub Presents WAV Forum", "2099-07-18 21:00:00", "/event/wav-1"),
]


def _club(metadata: dict) -> Club:
    c = Club(
        id=999, name="Test Live-Music Venue", address="406 Clement St",
        website="https://neckofthewoodssf.example", popularity=0, zip_code="94118",
        phone_number="", visible=True, timezone="America/Los_Angeles",
    )
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform="custom", scraper_key="",
        source_url=CALENDAR_URL, external_id=None, metadata=metadata,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def _js_calendar_html(events) -> str:
    items = [
        f"{{ title: '{title}', start: new Date('{date}'), url: '{url}' }}"
        for title, date, url in events
    ]
    return f"<script>var all_events = [{', '.join(items)}];</script>"


def _scraper(metadata: dict) -> TicketWebScraper:
    s = TicketWebScraper(_club(metadata))
    s.fetch_html = AsyncMock(return_value=_js_calendar_html(_MIXED))
    return s


@pytest.mark.asyncio
async def test_include_patterns_keep_only_comedy_series():
    s = _scraper(
        {"include_title_patterns": ["Stand-Up Comedy", "Clement St Comedy"]}
    )
    targets = await s.collect_scraping_targets()
    assert sorted(targets) == ["/event/best-of-sf-1", "/event/clement-st-1"]


@pytest.mark.asyncio
async def test_filter_off_by_default_keeps_all_events():
    s = _scraper({})
    targets = await s.collect_scraping_targets()
    assert len(targets) == len(_MIXED) == 5


@pytest.mark.asyncio
async def test_exclude_patterns_drop_matching_events():
    s = _scraper({"exclude_title_patterns": ["Fest", "WAV Forum"]})
    targets = await s.collect_scraping_targets()
    # The two festival/DJ events are dropped; the rest pass through.
    assert "/event/sinister-1" not in targets
    assert "/event/wav-1" not in targets
    assert "/event/best-of-sf-1" in targets
    assert len(targets) == 3


@pytest.mark.asyncio
async def test_include_then_exclude_compose():
    # Keep "Comedy" titles, but still drop an explicitly-excluded one.
    s = _scraper(
        {
            "include_title_patterns": ["Comedy"],
            "exclude_title_patterns": ["Clement"],
        }
    )
    targets = await s.collect_scraping_targets()
    assert targets == ["/event/best-of-sf-1"]
