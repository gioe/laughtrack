"""
Pipeline smoke tests for EsthersFolliesScraper and EsthersFolliesEvent.

Exercises get_data() against mocked VBO Tickets HTTP responses and unit-tests
the EsthersFolliesEvent.to_show() transformation path.
"""

import re
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.esthers_follies import EsthersFolliesEvent
from laughtrack.scrapers.implementations.venues.esthers_follies.data import (
    EsthersFolliesPageData,
)
from laughtrack.scrapers.implementations.venues.esthers_follies.extractor import (
    EsthersFolliesEventExtractor,
)
from laughtrack.scrapers.implementations.venues.esthers_follies.scraper import (
    EsthersFolliesScraper,
    _VBO_LOADPLUGIN_URL,
)

_SCRAPING_URL = "https://www.esthersfollies.com/tickets"

# Fake VBO session UUID used in mocked responses
_FAKE_SESSION = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"

# Minimal loadplugin HTML that embeds a session UUID
_LOADPLUGIN_HTML = f"""
<html><head></head><body>
<script>
    document.addEventListener("DOMContentLoaded", function () {{
        window.parent.postMessage(
            JSON.stringify({{
                type: "userSessionID",
                orgID: "7876",
                value: "{_FAKE_SESSION}"
            }}),
            "*"
        );
        window.location.href = "https://plugin.vbotickets.com/v5.0/event.asp?s={_FAKE_SESSION}";
    }});
</script>
</body></html>
"""


def _date_slider_html(*shows) -> str:
    """Build a minimal VBO date slider HTML fragment for the given show tuples.

    Each ``show`` is ``(edid, month, day, weekday, time)``.
    """
    items = []
    for edid, month, day, weekday, time in shows:
        items.append(f"""
            <li>
                <div role="tab" tabindex="0" class="SelectorBox Black"
                     id="edid{edid}" onclick="LoadEvent('39242','{edid}');">
                    <div class="DateMonth __edid{edid}">{month}<div></div></div>
                    <div class="DateDay __edid{edid}">{day}<div></div></div>
                    <div class="DateTime __edid{edid}">
                        <span class="WeekDay">{weekday}</span>
                        <span class="WeekDayTime"> - {time}</span>
                        <div></div>
                    </div>
                </div>
            </li>
        """)
    return "<ul>" + "".join(items) + "</ul>"


def _club() -> Club:
    _c = Club(id=999, name="Esther's Follies", address='525 E. 6th Street', website='https://www.esthersfollies.com', popularity=0, zip_code='78701', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=_SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# ---------------------------------------------------------------------------
# EsthersFolliesEventExtractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_parses_single_show():
    html = _date_slider_html(("645532", "Mar", "26", "Thu", "7:00 PM"))
    events = EsthersFolliesEventExtractor.extract_shows(html)

    assert len(events) == 1
    ev = events[0]
    assert ev.edid == "645532"
    assert ev.month == "Mar"
    assert ev.day == 26
    assert ev.weekday == "Thu"
    assert ev.time == "7:00 PM"


def test_extractor_parses_multiple_shows():
    html = _date_slider_html(
        ("645591", "Mar", "27", "Fri", "7:00 PM"),
        ("645592", "Mar", "27", "Fri", "9:00 PM"),
        ("645857", "Mar", "28", "Sat", "7:00 PM"),
        ("645858", "Mar", "28", "Sat", "9:00 PM"),
    )
    events = EsthersFolliesEventExtractor.extract_shows(html)

    assert len(events) == 4
    times = {(e.month, e.day, e.time) for e in events}
    assert ("Mar", 27, "7:00 PM") in times
    assert ("Mar", 27, "9:00 PM") in times
    assert ("Mar", 28, "7:00 PM") in times
    assert ("Mar", 28, "9:00 PM") in times


def test_extractor_deduplicates_same_edid():
    # Duplicate EDID should only appear once
    html = _date_slider_html(
        ("645532", "Mar", "26", "Thu", "7:00 PM"),
        ("645532", "Mar", "26", "Thu", "7:00 PM"),
    )
    events = EsthersFolliesEventExtractor.extract_shows(html)
    assert len(events) == 1


def test_extractor_returns_empty_for_empty_html():
    events = EsthersFolliesEventExtractor.extract_shows("")
    assert events == []


def test_extractor_returns_empty_for_no_matches():
    events = EsthersFolliesEventExtractor.extract_shows("<ul><li>No shows</li></ul>")
    assert events == []


# ---------------------------------------------------------------------------
# EsthersFolliesEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def test_event_to_show_returns_valid_show():
    club = _club()
    # Use a future date guaranteed to be upcoming
    ev = EsthersFolliesEvent(edid="645532", month="Apr", day=3, weekday="Fri", time="7:00 PM")

    with patch("laughtrack.core.entities.event.esthers_follies.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        show = ev.to_show(club)

    assert show is not None
    assert show.name == "Esther's Follies"
    assert show.description == "Sketch Comedy | Political Satire | Award-winning Magic"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://www.esthersfollies.com/tickets"


def test_event_to_show_year_rollover():
    """A past month/day should advance to the next year."""
    club = _club()
    # January show when today is March 25 — should be Jan 2027
    ev = EsthersFolliesEvent(edid="999999", month="Jan", day=10, weekday="Sat", time="9:00 PM")

    with patch("laughtrack.core.entities.event.esthers_follies.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        show = ev.to_show(club)

    assert show is not None
    assert show.date.year == 2027


def test_event_to_show_invalid_month_returns_none():
    club = _club()
    ev = EsthersFolliesEvent(edid="0", month="Xyz", day=1, weekday="Mon", time="7:00 PM")
    show = ev.to_show(club)
    assert show is None


# ---------------------------------------------------------------------------
# EsthersFolliesScraper.get_data() integration-style smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data(monkeypatch):
    """get_data() extracts shows when VBO API responds with valid HTML."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    slider_html = _date_slider_html(
        ("645532", "Mar", "26", "Thu", "7:00 PM"),
        ("645591", "Mar", "27", "Fri", "7:00 PM"),
        ("645592", "Mar", "27", "Fri", "9:00 PM"),
    )

    async def fake_fetch_html(url, **kwargs):
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        return slider_html

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)

    assert isinstance(result, EsthersFolliesPageData)
    assert len(result.event_list) == 3
    edids = {e.edid for e in result.event_list}
    assert "645532" in edids
    assert "645591" in edids
    assert "645592" in edids


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_session(monkeypatch):
    """get_data() returns None if session UUID is missing from loadplugin response."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    async def fake_fetch_html(url, **kwargs):
        return "<html><body>No session here</body></html>"

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_slider_empty(monkeypatch):
    """get_data() returns None if the date slider returns no shows."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    async def fake_fetch_html(url, **kwargs):
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        return "<ul></ul>"

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)
    assert result is None
