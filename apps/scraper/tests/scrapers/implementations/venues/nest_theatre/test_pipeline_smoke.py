"""
Pipeline smoke tests for NestTheatreScraper and NestTheatreEvent.

Exercises get_data() against mocked VBO Tickets responses (loadplugin session
handshake + showevents grid) using a trimmed real fixture, and unit-tests the
extractor's class filtering, recurring-date expansion, and the
NestTheatreEvent.to_show() transformation path.
"""

from datetime import date
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.nest_theatre import NestTheatreEvent
from laughtrack.scrapers.implementations.venues.nest_theatre.scraper import NestTheatreScraper
from laughtrack.scrapers.implementations.venues.nest_theatre.data import NestTheatrePageData
from laughtrack.scrapers.implementations.venues.nest_theatre.extractor import NestTheatreEventExtractor

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_GRID_HTML = (_FIXTURES_DIR / "showevents_grid.html").read_text()
# Stub loadplugin response carrying a session UUID in the shape VBO emits.
_LOADPLUGIN_HTML = '<html><script>var o = { value: "554d8105-2896-4c98-acb2-d0c8554ea8b4" };</script></html>'
_FIXED_TODAY = date(2026, 6, 15)


def _club() -> Club:
    c = Club(
        id=999, name="The Nest Theatre", address="2643 N High St",
        website="https://nesttheatre.com", popularity=0, zip_code="43202",
        phone_number="", visible=False, timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform="custom", scraper_key="nest_theatre",
        source_url="https://nesttheatre.com/shows/", external_id=None,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


# --------------------------------------------------------------------------- #
# Registry + targets
# --------------------------------------------------------------------------- #


def test_scraper_key_in_registry():
    from laughtrack.app.registry import SCRAPERS

    assert SCRAPERS.get("nest_theatre") is NestTheatreScraper


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_loadplugin_url():
    targets = await NestTheatreScraper(_club()).collect_scraping_targets()
    assert len(targets) == 1
    assert "plugin.vbotickets.com/plugin/loadplugin" in targets[0]
    assert "5D584EB6-2A49-4AFD-9430-259D26127F0B" in targets[0]


# --------------------------------------------------------------------------- #
# get_data()
# --------------------------------------------------------------------------- #


def _stub_fetch_html(monkeypatch, *, loadplugin=_LOADPLUGIN_HTML, grid=_GRID_HTML):
    async def fake_fetch_html(self, url: str, *args, **kwargs) -> str:
        if "loadplugin" in url:
            return loadplugin
        if "showevents" in url:
            return grid
        return ""

    monkeypatch.setattr(NestTheatreScraper, "fetch_html", fake_fetch_html)


@pytest.mark.asyncio
async def test_get_data_returns_live_shows_and_filters_classes(monkeypatch):
    """get_data() returns Live Shows only; the Level 1 class is excluded."""
    _stub_fetch_html(monkeypatch)
    result = await NestTheatreScraper(_club()).get_data("…/loadplugin")

    assert isinstance(result, NestTheatrePageData)
    names = {e.name for e in result.event_list}
    assert "PROUD: A Variety Show!" in names
    assert "Troika Improv Contest" in names
    assert "Christian Royce" in names
    # Class entry must never surface as a show.
    assert not any("Adult Improv Class" in n for n in names)


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_session(monkeypatch):
    """A loadplugin response without a session UUID yields None."""
    _stub_fetch_html(monkeypatch, loadplugin="<html>no session here</html>")
    assert await NestTheatreScraper(_club()).get_data("…/loadplugin") is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_grid(monkeypatch):
    """An empty showevents grid yields None."""
    _stub_fetch_html(monkeypatch, grid="")
    assert await NestTheatreScraper(_club()).get_data("…/loadplugin") is None


# --------------------------------------------------------------------------- #
# Extractor unit tests
# --------------------------------------------------------------------------- #


def test_extract_shows_filters_classes_and_expands_recurring():
    events = NestTheatreEventExtractor.extract_shows(_GRID_HTML, today=_FIXED_TODAY)
    by_name = {}
    for e in events:
        by_name.setdefault(e.name, []).append(e)

    assert set(by_name) == {"PROUD: A Variety Show!", "Troika Improv Contest", "Christian Royce"}
    # Troika lists 6/5,6/12,6/19,6/26,7/10,7/17,7/24 → 5 remain after dropping the two past dates.
    assert len(by_name["Troika Improv Contest"]) == 5
    assert all(e.dt_str >= _FIXED_TODAY.isoformat() for e in by_name["Troika Improv Contest"])


def test_extract_shows_parses_fields():
    events = NestTheatreEventExtractor.extract_shows(_GRID_HTML, today=_FIXED_TODAY)
    proud = next(e for e in events if e.name == "PROUD: A Variety Show!")
    assert proud.dt_str == "2026-06-18 19:30:00"
    assert proud.room == "Mainstage"
    assert proud.price == 13.0  # lowest of "$13.00 - $15.00"


def test_extract_shows_empty_html_returns_empty():
    assert NestTheatreEventExtractor.extract_shows("", today=_FIXED_TODAY) == []


# --------------------------------------------------------------------------- #
# to_show()
# --------------------------------------------------------------------------- #


def test_to_show_builds_show_with_ticket_and_timezone():
    event = NestTheatreEvent(
        name="PROUD: A Variety Show!", dt_str="2026-06-18 19:30:00",
        room="Mainstage", price=13.0,
    )
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "PROUD: A Variety Show!"
    assert show.date.year == 2026 and show.date.month == 6 and show.date.day == 18
    assert show.date.hour == 19 and show.date.minute == 30
    assert show.date.utcoffset() is not None  # localized to America/New_York
    assert show.room == "Mainstage"
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 13.0
    assert show.tickets[0].purchase_url == "https://nesttheatre.com/shows/"


def test_to_show_price_unknown_emits_fallback_ticket():
    event = NestTheatreEvent(name="Free Jam", dt_str="2026-07-01 20:00:00", price=None)
    show = event.to_show(_club())
    assert show is not None
    assert show.tickets[0].price is None


def test_to_show_returns_none_on_unparseable_date():
    event = NestTheatreEvent(name="Broken", dt_str="not-a-date", price=None)
    assert event.to_show(_club()) is None
