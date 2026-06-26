"""Tests for the do314 / DoStuff Media venue scraper."""

import json
from datetime import datetime
from pathlib import Path

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.do314.data import Do314PageData
from laughtrack.scrapers.implementations.api.do314.scraper import Do314Scraper

_FIXTURE = Path(__file__).parent / "fixtures" / "do314_venue_events.json"
_SOURCE_URL = "https://do314.com/venues/apotheosis-comics-and-lounge/events.json"


def _payload() -> dict:
    return json.loads(_FIXTURE.read_text())


def _club(metadata: dict | None = None, timezone: str = "America/Chicago") -> Club:
    club = Club(
        id=999,
        name="Apotheosis Comics and Lounge",
        address="3206 S Grand Blvd",
        website="https://shopapotheosis.com/",
        popularity=0,
        zip_code="63118",
        phone_number="",
        visible=True,
        timezone=timezone,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="do314",
        scraper_key="do314",
        source_url=_SOURCE_URL,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_registry_resolves_do314_key():
    """The scraper is auto-discovered by its `key` attribute."""
    assert ScraperResolver().get("do314") is Do314Scraper


async def test_default_filter_keeps_only_comedy(monkeypatch):
    """By default only category_param == 'comedy' upcoming events survive."""
    scraper = Do314Scraper(_club())

    async def fake_fetch_json(url):
        assert url == _SOURCE_URL
        return _payload()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, Do314PageData)
    titles = sorted(e.title for e in page.event_list)
    # Music event dropped, past event dropped, malformed (no title) dropped.
    assert titles == ["Apotheosis Comedy Showcase", "South City Comedy Showcase"]


async def test_include_all_categories_keeps_music(monkeypatch):
    """The metadata override disables the comedy-only filter."""
    scraper = Do314Scraper(_club(metadata={"do314_include_all_categories": True}))

    async def fake_fetch_json(url):
        return _payload()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, Do314PageData)
    titles = sorted(e.title for e in page.event_list)
    # 2 comedy + 1 music upcoming; past + malformed still dropped.
    assert titles == [
        "Apotheosis Comedy Showcase",
        "Indie Rock Night",
        "South City Comedy Showcase",
    ]


async def test_scrape_async_produces_shows(monkeypatch):
    """End-to-end: targets -> get_data -> transformer pipeline -> Shows."""
    scraper = Do314Scraper(_club())

    async def fake_fetch_json(url):
        return _payload()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    shows = await scraper.scrape_async()
    assert len(shows) == 2
    by_name = {s.name: s for s in shows}

    showcase = by_name["Apotheosis Comedy Showcase"]
    assert showcase.club_id == 999
    # Absolute do314 event page URL.
    assert showcase.show_page_url == (
        "https://do314.com/events/2026/7/5/apotheosis-comedy-showcase-tickets"
    )
    # begin_time is ISO 8601 with offset -> timezone-aware datetime.
    assert isinstance(showcase.date, datetime)
    assert showcase.date.tzinfo is not None
    # Ticket falls back to the buy_url when present.
    assert showcase.tickets
    assert showcase.tickets[0].purchase_url.endswith(
        "/apotheosis-comedy-showcase-tickets/buy"
    )


async def test_empty_feed_returns_none(monkeypatch):
    """A venue with no event_groups yields no page data (not an error)."""
    scraper = Do314Scraper(_club())

    async def fake_fetch_json(url):
        return {"venue": {"id": 1}, "event_groups": []}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    assert await scraper.get_data(_SOURCE_URL) is None
