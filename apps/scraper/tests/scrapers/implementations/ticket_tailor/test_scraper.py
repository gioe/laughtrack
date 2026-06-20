"""Smoke tests for TicketTailorScraper using a recorded box-office fixture.

Fixture captured 2026-06-20 from tickettailor.com/events/milwaukeecomedy/
(curl_cffi impersonate=chrome120 + Referer milwaukeecomedy.com to clear
Cloudflare). The account is a roving producer; the listing's one event is at
Vendetta Coffee Bar (zip 53204).
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.ticket_tailor.extractor import (
    extract_account_slug,
    extract_events,
    listing_url_for_account,
)
from laughtrack.scrapers.implementations.ticket_tailor.scraper import TicketTailorScraper

_FIXTURE = (Path(__file__).parent / "fixtures" / "listing.html").read_text()


@pytest.fixture
def producer_proxy() -> Club:
    """Synthetic proxy Club like _build_synthetic_proxy_for_company produces."""
    c = Club(
        id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID,
        name="Milwaukee Comedy (producer)",
        address="",
        website="https://www.milwaukeecomedy.com/",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
        is_synthetic=True,
    )
    c.active_scraping_source = ScrapingSource(
        id=1,
        platform="custom",
        scraper_key="ticket_tailor",
        source_url="https://www.tickettailor.com/events/milwaukeecomedy/",
        metadata={"account_slug": "milwaukeecomedy"},
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def _fake_venue_club(venue: dict) -> Club:
    return Club(
        id=999,
        name=venue["name"],
        address="",
        website="",
        popularity=0,
        zip_code=venue.get("zip_code", ""),
        phone_number="",
        visible=True,
        timezone=venue.get("timezone") or "America/Chicago",
    )


def test_listing_url_and_slug_roundtrip():
    url = listing_url_for_account("milwaukeecomedy")
    assert url == "https://www.tickettailor.com/events/milwaukeecomedy/"
    assert extract_account_slug(url) == "milwaukeecomedy"
    assert extract_account_slug("https://www.tickettailor.com/all-tickets/foo/") == "foo"
    assert extract_account_slug("https://example.com/x") is None


def test_extract_events_from_fixture():
    events = extract_events(_FIXTURE)
    assert len(events) == 1
    ev = events[0]
    assert "Comedy for a Cause" in ev.title
    assert ev.start == datetime(2026, 6, 30, 18, 0)  # 6:00 PM
    assert ev.timezone == "America/Chicago"  # CDT
    assert ev.venue_name == "Vendetta Coffee Bar"
    assert ev.venue_zip == "53204"
    assert ev.event_url.endswith("/events/milwaukeecomedy/2260402")


def test_extract_events_empty():
    assert extract_events("") == []
    assert extract_events("<html><body>no events</body></html>") == []


def test_parse_location_without_zip():
    from laughtrack.scrapers.implementations.ticket_tailor.extractor import _parse_location

    assert _parse_location("Lakefront Brewery") == ("Lakefront Brewery", "")
    assert _parse_location("Vendetta Coffee Bar, 53204") == ("Vendetta Coffee Bar", "53204")


@pytest.mark.asyncio
async def test_full_scrape_routes_to_per_venue_club(monkeypatch, producer_proxy):
    scraper = TicketTailorScraper(producer_proxy)

    async def fake_fetch(url):
        return _FIXTURE

    monkeypatch.setattr(scraper, "_fetch_listing", fake_fetch)
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", _fake_venue_club)

    shows = await scraper.scrape_async()
    assert len(shows) == 1
    show = shows[0]
    # Show is attached to the per-venue club (999), NOT the hidden producer proxy.
    assert show.club_id == 999
    assert show.date is not None
    assert show.tickets
    assert show.tickets[0].purchase_url.endswith("/events/milwaukeecomedy/2260402")


@pytest.mark.asyncio
async def test_full_scrape_empty_listing(monkeypatch, producer_proxy):
    scraper = TicketTailorScraper(producer_proxy)

    async def fake_fetch(url):
        return "<html><body>no events</body></html>"

    monkeypatch.setattr(scraper, "_fetch_listing", fake_fetch)
    shows = await scraper.scrape_async()
    assert shows == []


def test_referer_uses_producer_website(producer_proxy):
    scraper = TicketTailorScraper(producer_proxy)
    assert scraper._referer() == "https://www.milwaukeecomedy.com/"
