"""Tests for the EventPrime get_events scraper.

The smoke test drives the full ``scrape_async`` pipeline against a captured
Flip Flops Comedy Club fixture (dates shifted to far-future / far-past to avoid
time-bomb failures per the scraper test-date convention).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.app.registry import discover_scrapers
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.eventprime.scraper import EventPrimeScraper

_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "get_events.json").read_text()
)
_ENDPOINT = "https://flipflopscomedy.com/wp-json/eventprime/v1/get_events"


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=999,
        name="Flip Flops Comedy Club",
        address="",
        website="https://flipflopscomedy.com/",
        popularity=0,
        zip_code="04064",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="Old Orchard Beach",
        state="ME",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="eventprime",
        source_url=_ENDPOINT,
        external_id=None,
        metadata={},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_registry_resolves_eventprime_key():
    assert discover_scrapers().get("eventprime") is EventPrimeScraper


@pytest.mark.asyncio
async def test_scraper_full_pipeline_produces_upcoming_shows(monkeypatch, club):
    scraper = EventPrimeScraper(club)

    async def fake_fetch_json(url, **kwargs):
        assert url == _ENDPOINT
        return _FIXTURE

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    shows = await scraper.scrape_async()

    # Fixture has 2 far-future events + 1 far-past; past is filtered.
    assert len(shows) == 2
    assert {s.club_id for s in shows} == {club.id}
    shell = next(s for s in shows if s.name.startswith("Shell Yeah"))
    assert shell.date.isoformat() == "2099-07-15T21:30:00-04:00"
    # multiple EventPrime tickets become multiple Show tickets
    assert sorted(t.price for t in shell.tickets) == [12.0, 35.0]
    # (URL normalization drops the trailing slash)
    assert shell.show_page_url.rstrip("/") == "https://flipflopscomedy.com/event/shell-yeah-a-night-of-longform-improv-4"
    # the captured past event ("2020-...") is dropped
    assert all(s.date.year >= 2099 for s in shows)


@pytest.mark.asyncio
async def test_no_source_url_yields_no_shows(monkeypatch):
    c = Club(id=2, name="No Config", address="", website="", popularity=0, zip_code="",
             phone_number="", visible=True, timezone="America/New_York", city="", state="ME")
    c.active_scraping_source = ScrapingSource(
        platform="custom", scraper_key="eventprime", source_url=None, metadata={},
    )
    scraper = EventPrimeScraper(c)

    async def fail_fetch(url, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("fetch_json should not run without a source_url")

    monkeypatch.setattr(scraper, "fetch_json", fail_fetch)
    assert await scraper.scrape_async() == []
