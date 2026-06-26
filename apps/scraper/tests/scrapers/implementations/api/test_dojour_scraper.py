"""Tests for the Dojour platform scraper."""

import json
from datetime import datetime
from pathlib import Path

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.dojour.data import DojourPageData
from laughtrack.scrapers.implementations.api.dojour.scraper import DojourScraper

_FIXTURE = Path(__file__).parent / "fixtures" / "dojour_user_feed.json"
_SOURCE_URL = "https://dojour.us/embed/u/sisyphusbrewing?cal_type=upcoming"


def _payload() -> dict:
    return json.loads(_FIXTURE.read_text())


def _club(timezone: str = "America/Chicago") -> Club:
    club = Club(
        id=999,
        name="Sisyphus Brewing & Comedy",
        address="712 Ontario Ave W #100",
        website="https://www.sisyphusbrewing.com/",
        popularity=0,
        zip_code="55403",
        phone_number="",
        visible=True,
        timezone=timezone,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="dojour",
        scraper_key="dojour",
        source_url=_SOURCE_URL,
        metadata={},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_registry_resolves_dojour_key():
    """The scraper is auto-discovered by its `key` attribute."""
    assert ScraperResolver().get("dojour") is DojourScraper


def test_parse_username_variants():
    """Username parses from embed/profile URLs and a bare slug."""
    parse = DojourScraper._parse_username
    assert parse("https://dojour.us/embed/u/sisyphusbrewing?cal_type=upcoming") == "sisyphusbrewing"
    assert parse("https://dojour.us/u/sisyphusbrewing") == "sisyphusbrewing"
    assert parse("sisyphusbrewing") == "sisyphusbrewing"


async def test_expands_showings_and_drops_cancelled_and_past(monkeypatch):
    """Each upcoming showing yields a DojourEvent; cancelled + past are dropped."""
    scraper = DojourScraper(_club())

    async def fake_fetch_json(url):
        assert "username=sisyphusbrewing" in url
        return _payload()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, DojourPageData)
    # Sam Schedler (2 showings) + Open Mic (1) + Fumi Abe (1 future; 1 past dropped)
    # = 4 showings. Cancelled Show is excluded entirely.
    assert len(page.event_list) == 4
    titles = {e.title for e in page.event_list}
    assert "Cancelled Show" not in titles
    assert titles == {
        "Sam Schedler Presents: Pride Weekend Comedy /// Comedy",
        "Stand Up Comedy Open Mic",
        "Fumi Abe /// Comedy",
    }


async def test_scrape_async_produces_shows(monkeypatch):
    """End-to-end: targets -> get_data -> transformer pipeline -> Shows."""
    scraper = DojourScraper(_club())

    async def fake_fetch_json(url):
        return _payload()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    shows = await scraper.scrape_async()
    assert len(shows) == 4
    for show in shows:
        assert show.club_id == 999
        assert isinstance(show.date, datetime)
        assert show.date.tzinfo is not None
        assert show.tickets

    by_url_date = {(s.show_page_url, s.date.hour): s for s in shows}

    # Multi-option offer -> min price ($18.00). HTML description stripped.
    sam_7pm = by_url_date[("https://dojour.us/e/83034-sam-schedler-presents-pride-weekend-comedy", 19)]
    assert sam_7pm.tickets[0].price == 18.0
    assert sam_7pm.tickets[0].purchase_url == "https://dojour.us/e/83034/showings"
    assert "<b>" not in (sam_7pm.description or "")

    # Free open mic -> no offer options -> unknown price (None).
    open_mic = next(s for s in shows if s.name == "Stand Up Comedy Open Mic")
    assert open_mic.tickets[0].price is None

    # Fumi Abe -> only the future showing survives, priced $25.00.
    fumi = next(s for s in shows if s.name == "Fumi Abe /// Comedy")
    assert fumi.date.year == 2027
    assert fumi.tickets[0].price == 25.0


async def test_empty_feed_returns_none(monkeypatch):
    """A venue with no results yields no page data (not an error)."""
    scraper = DojourScraper(_club())

    async def fake_fetch_json(url):
        return {"results": [], "next": None}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    assert await scraper.get_data(_SOURCE_URL) is None


def _event(eid: int, title: str, start_dt: str) -> dict:
    return {
        "event": {
            "id": eid,
            "title": title,
            "absolute_url": f"https://dojour.us/e/{eid}",
            "call_to_action_url": f"https://dojour.us/e/{eid}/showings",
            "cancelled": False,
            "upcoming_showing_set": [{"id": eid, "start_dt": start_dt, "timezone": "America/Chicago"}],
        }
    }


async def test_event_without_showing_set_falls_back_to_row(monkeypatch):
    """An event missing upcoming_showing_set falls back to the row's own start_dt."""
    scraper = DojourScraper(_club())
    payload = {
        "next": None,
        "results": [
            {
                "id": 700,
                "start_dt": "2027-12-01T20:00:00-0600",
                "timezone": "America/Chicago",
                "offer": {"id": 700, "option_set": [{"active": True, "price": 3000}]},
                "event": {
                    "id": 700,
                    "title": "Fallback Show /// Comedy",
                    "absolute_url": "https://dojour.us/e/700-fallback",
                    "call_to_action_url": "https://dojour.us/e/700/showings",
                    "cancelled": False,
                    # no upcoming_showing_set key at all
                },
            }
        ],
    }

    async def fake_fetch_json(url):
        return payload

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, DojourPageData)
    assert len(page.event_list) == 1
    ev = page.event_list[0]
    assert ev.title == "Fallback Show /// Comedy"
    assert ev.start_dt == "2027-12-01T20:00:00-0600"
    assert ev.min_price_cents == 3000  # price read from the row-level offer


async def test_pagination_follows_next_url(monkeypatch):
    """get_data follows the response `next` URL and merges all pages."""
    scraper = DojourScraper(_club())
    page2_url = "https://dojour.us/api/event_instances/user_feed/?page=2&username=sisyphusbrewing"
    calls = []

    async def fake_fetch_json(url):
        calls.append(url)
        if "page=2" in url:
            return {"next": None, "results": [_event(2, "B /// Comedy", "2027-11-02T19:00:00-0500")]}
        return {"next": page2_url, "results": [_event(1, "A /// Comedy", "2027-11-01T19:00:00-0500")]}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, DojourPageData)
    assert {e.title for e in page.event_list} == {"A /// Comedy", "B /// Comedy"}
    # Page 1 (built URL) + page 2 (the `next` URL) were both fetched.
    assert len(calls) == 2
    assert any("page=2" in u for u in calls)
