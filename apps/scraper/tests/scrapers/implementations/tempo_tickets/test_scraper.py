"""Smoke tests for TempoTicketsScraper using recorded Tempo HTML fixtures.

Fixtures were captured 2026-06-20 from:
  - listing.html : listing.php?c=80  (ComedySportz Milwaukee, 4 recurring events)
  - event.html   : /event/NtjnAX     (2026 ComedySportz Friday 7:30 Match)
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.tempo_tickets.extractor import (
    extract_event_dates,
    extract_event_links,
    listing_url_for_category,
)
from laughtrack.scrapers.implementations.tempo_tickets.scraper import TempoTicketsScraper

_FIXTURES = Path(__file__).parent / "fixtures"
_LISTING_HTML = (_FIXTURES / "listing.html").read_text()
_EVENT_HTML = (_FIXTURES / "event.html").read_text()
# Reference date matching the fixture capture, so year inference is deterministic.
_REF = date(2026, 6, 20)


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=9001,
        name="ComedySportz Milwaukee",
        address="420 S 1st St",
        website="https://cszmke.com",
        popularity=0,
        zip_code="53204",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Milwaukee",
        state="WI",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="tempo_tickets",
        source_url="https://www.tempotickets.com/tempotickets/site/pages/listing.php?c=80",
        metadata={"category_id": "80"},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_listing_url_built_from_category():
    assert (
        listing_url_for_category("80")
        == "https://www.tempotickets.com/tempotickets/site/pages/listing.php?c=80"
    )


def test_extract_event_links_from_listing():
    links = extract_event_links(_LISTING_HTML)
    # The captured listing has 4 distinct recurring events.
    assert len(links) == 4
    codes = {code for code, _title, _url in links}
    assert {"Dtjn0D", "mtjnZL", "NtjnAX", "PtjnCb"} == codes
    for _code, title, url in links:
        assert title  # non-empty title
        assert url.startswith("https://www.tempotickets.com/event/")


def test_extract_event_links_empty_html():
    assert extract_event_links("") == []
    assert extract_event_links("<html><body>no events</body></html>") == []


def test_extract_event_dates_skips_placeholder_and_past():
    dates = extract_event_dates(_EVENT_HTML, today=_REF)
    # 13 upcoming options (the value='0' placeholder is skipped; the 25
    # date_past divs are not inside the select, so never appear here).
    assert len(dates) == 13
    date_ids = [date_id for date_id, _dt in dates]
    assert "0" not in date_ids
    assert "27784" in date_ids  # first real option: Fri Jun 26 @ 7:30pm

    first_id, first_dt = dates[0]
    assert first_id == "27784"
    assert first_dt == datetime(2026, 6, 26, 19, 30)


def test_extract_event_dates_year_rollover():
    """A January option scraped in December rolls over to the next year."""
    html = (
        "<select name='EventDateID'>"
        "<option value='0'></option>"
        "<option value='99'>Fri Jan 9 @ 7:30pm (Doors open 6pm)</option>"
        "</select>"
    )
    dates = extract_event_dates(html, today=date(2026, 12, 15))
    assert dates == [("99", datetime(2027, 1, 9, 19, 30))]


@pytest.mark.asyncio
async def test_collect_scraping_targets(monkeypatch, club):
    scraper = TempoTicketsScraper(club)

    async def fake_fetch(url, **kwargs):
        return _LISTING_HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 4
    assert all(t.startswith("https://www.tempotickets.com/event/") for t in targets)


@pytest.mark.asyncio
async def test_get_data_fans_out_dates(monkeypatch, club):
    scraper = TempoTicketsScraper(club)

    async def fake_fetch(url, **kwargs):
        return _EVENT_HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    page = await scraper.get_data("https://www.tempotickets.com/event/NtjnAX")
    assert page is not None
    assert len(page.event_list) == 13
    event = page.event_list[0]
    assert event.title
    assert event.event_url == "https://www.tempotickets.com/event/NtjnAX"
    assert event.date_id == "27784"


@pytest.mark.asyncio
async def test_full_scrape_returns_shows(monkeypatch, club):
    """End-to-end: listing -> event pages -> dated Show objects (N > 0)."""
    scraper = TempoTicketsScraper(club)

    async def fake_fetch(url, **kwargs):
        if "listing.php" in url:
            return _LISTING_HTML
        return _EVENT_HTML

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    shows = await scraper.scrape_async()
    # 4 events x 13 upcoming dates (each event page fixture is the same).
    assert len(shows) > 0
    for show in shows:
        assert show.club_id == club.id
        assert show.date is not None
        assert show.tickets
        assert show.tickets[0].purchase_url.startswith(
            "https://www.tempotickets.com/event/"
        )
