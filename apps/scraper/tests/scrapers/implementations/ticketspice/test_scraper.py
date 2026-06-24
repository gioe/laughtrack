"""Smoke tests for the generic TicketSpice (Webconnex) scraper.

The headline case is MULTI-DATE: a single TicketSpice form can sell several show
dates via a date-selection ``categories`` inventory (validated 2026-06-24 against
comedy.ticketspice.com/2026-comedy-uncorked-retzlaff-vineyards, which lists
June 27 / July 18 / August 22 under one form while ``appSettings.eventStart``
names only the first). The extractor must emit one event per dated category and
still handle legacy single-date forms (The Stage at Burke / TASK-3207) that have
no dated categories.

The bootstrap HTML is reconstructed in-process by :func:`_boot_html` (no network,
no recorded file): each member is a JSON *string* embedded in the
``window.__BOOTSTRAP__`` object literal, exactly as the live page encodes it, so
the test exercises the real regex + double-unescape extraction path.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticketspice.extractor import (
    extract_event,
    extract_events,
)
from laughtrack.scrapers.implementations.api.ticketspice.scraper import TicketSpiceScraper

_RETZLAFF_URL = "https://comedy.ticketspice.com/2026-comedy-uncorked-retzlaff-vineyards"


def _boot_html(app_settings: dict, form_data: dict | None) -> str:
    """Reproduce the live ``window.__BOOTSTRAP__`` encoding for a form page."""
    members = [f"\t\tappSettings: {json.dumps(json.dumps(app_settings))}"]
    if form_data is not None:
        members.append(f"\t\tformData: {json.dumps(json.dumps(form_data))}")
    body = ",\n".join(members)
    return (
        "<!DOCTYPE html><html><head><title>Form</title></head><body>\n"
        "<script>\n\twindow.__BOOTSTRAP__ = {\n"
        f"{body}\n"
        "\t};\n</script>\n</body></html>\n"
    )


def _retzlaff_html() -> str:
    app_settings = {
        "host": "comedy.ticketspice.com",
        "status": 1,
        "formName": "2026 Comedy Uncorked @ Retzlaff Vineyards",
        "formURL": _RETZLAFF_URL,
        "timeZone": "America/Los_Angeles",
        # First date only — 2026-06-28T02:30Z == 2026-06-27 19:30 PT.
        "eventStart": "2026-06-28T02:30:00Z",
        "calendarInfo": {"date": "2026-06-28T02:30:00Z", "timezone": "UTC"},
    }
    categories = [
        {"id": "cat-jun", "label": "June 27", "description": "Cody Woods, Nancy Lee, Rhoda Gravador", "open": True},
        {"id": "cat-jul", "label": "July 18", "description": "Stephen B., Mean Dave, Candy Shaw, Michael Booth"},
        {"id": "cat-aug", "label": "August 22", "description": "Joe Klocek, Carla Clay, Denise Lee"},
        # Not a date — must be skipped, not emitted as a show.
        {"id": "cat-don", "label": "Donation to Open Heart Kitchen", "description": "Help feed the hungry."},
    ]
    levels = [
        {"label": "Donation to Open Heart Kitchen", "category": "cat-don", "active": True, "visible": True},
        {"label": "June 27 General Admission Lawn Seat", "price": "40", "category": "cat-jun", "active": True, "visible": True},
        {"label": "June 27 Assigned Reserved Seat", "price": "45", "category": "cat-jun", "active": True, "visible": True},
        # Hidden back-office $1 level — must NOT be picked as the public price.
        {"label": "June 27 GA - Back Office", "price": "1", "category": "cat-jun", "active": True, "visible": False},
        {"label": "July 18 General Admission Lawn Seat", "price": "40", "category": "cat-jul", "active": True, "visible": True},
        {"label": "July 18 Table for 6", "price": "270", "category": "cat-jul", "active": True, "visible": True},
        {"label": "August 22 General Admission Lawn Seat", "price": "40", "category": "cat-aug", "active": True, "visible": True},
        {"label": "August 22 Table for 10", "price": "450", "category": "cat-aug", "active": True, "visible": True},
    ]
    form_data = {
        "type": "form",
        "soldOut": False,
        "elements": [
            {"type": "ticketBlock", "minDate": "2026-06-24", "categories": categories, "levels": levels},
        ],
    }
    return _boot_html(app_settings, form_data)


def _single_date_html() -> str:
    """Legacy single-date form (no dated categories) — The Stage at Burke style."""
    app_settings = {
        "host": "thestage.ticketspice.com",
        "status": 1,
        "formName": "Barley & Me Pod-uctions Comedy Show",
        "formURL": "https://thestage.ticketspice.com/barley-me-comedy",
        "timeZone": "America/Chicago",
        "eventStart": "2026-06-07T00:00:00Z",  # date-only (UTC midnight) -> no time
    }
    form_data = {
        "type": "form",
        "soldOut": False,
        "elements": [{"type": "ticketBlock", "levels": [{"label": "General Admission", "price": "9"}]}],
    }
    return _boot_html(app_settings, form_data)


# --------------------------------------------------------------------------- #
# Extractor — multi-date                                                       #
# --------------------------------------------------------------------------- #


def test_multidate_extracts_one_event_per_dated_category():
    events = extract_events(_retzlaff_html(), form_url=_RETZLAFF_URL)
    # Three dated categories; the "Donation" category is skipped.
    assert [e.event_date for e in events] == [
        date(2026, 6, 27),
        date(2026, 7, 18),
        date(2026, 8, 22),
    ]
    assert all(e.form_url == _RETZLAFF_URL for e in events)
    assert all(e.title == "2026 Comedy Uncorked @ Retzlaff Vineyards" for e in events)


def test_multidate_event_time_from_event_start_localized():
    # eventStart 2026-06-28T02:30Z -> 19:30 PT, reused for every date.
    events = extract_events(_retzlaff_html(), form_url=_RETZLAFF_URL)
    assert all(e.event_time == time(19, 30) for e in events)


def test_multidate_price_is_lowest_visible_per_category():
    events = {e.event_date: e for e in extract_events(_retzlaff_html(), form_url=_RETZLAFF_URL)}
    # June 27: visible 40/45 (hidden $1 ignored); July 18: 40/270; Aug 22: 40/450.
    assert events[date(2026, 6, 27)].price == 40.0
    assert events[date(2026, 7, 18)].price == 40.0
    assert events[date(2026, 8, 22)].price == 40.0


def test_multidate_description_carries_lineup_blurb():
    events = {e.event_date: e for e in extract_events(_retzlaff_html(), form_url=_RETZLAFF_URL)}
    assert "Cody Woods" in events[date(2026, 6, 27)].description


# --------------------------------------------------------------------------- #
# Extractor — single-date backward compatibility                              #
# --------------------------------------------------------------------------- #


def test_single_date_form_still_yields_one_event():
    events = extract_events(_single_date_html(), form_url="https://thestage.ticketspice.com/barley-me-comedy")
    assert len(events) == 1
    ev = events[0]
    assert ev.event_date == date(2026, 6, 7)
    assert ev.title == "Barley & Me Pod-uctions Comedy Show"
    assert ev.price == 9.0
    # date-only eventStart -> no wall-clock time derived
    assert ev.event_time is None


def test_extract_event_single_wrapper_returns_first():
    ev = extract_event(_retzlaff_html(), form_url=_RETZLAFF_URL)
    assert ev is not None and ev.event_date == date(2026, 6, 27)


def test_unpublished_and_empty_yield_nothing():
    assert extract_events("", form_url=_RETZLAFF_URL) == []
    assert extract_events("<html><body>nope</body></html>", form_url=_RETZLAFF_URL) == []
    draft = _boot_html({"status": 0, "formName": "Draft", "eventStart": "2026-06-07T00:00:00Z"}, None)
    assert extract_events(draft, form_url=_RETZLAFF_URL) == []


# --------------------------------------------------------------------------- #
# Full pipeline — extractor -> transformer -> Show                            #
# --------------------------------------------------------------------------- #


def _retzlaff_club() -> Club:
    club = Club(
        id=4242,
        name="Retzlaff Vineyards (Comedy Uncorked)",
        address="1356 S Livermore Ave, Livermore, CA 94550",
        website="https://comedyuncorked.com/livermore/",
        popularity=0,
        zip_code="94550",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="ticketspice",
        scraper_key="ticketspice",
        source_url=_RETZLAFF_URL,
        metadata={},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _future_multidate_html(dates: list[date]) -> str:
    """Multi-date bootstrap whose categories are the given (future) dates.

    Built relative to today so the full-pipeline test (which drops past dates in
    ``to_show``) never time-bombs once the recorded 2026 dates pass — see the
    far-future-test-dates convention.
    """
    first = min(dates)
    # eventStart at 19:30 local for the earliest date, expressed as a UTC instant
    # (PT is UTC-7 in summer, but the extractor reads the wall-clock back out via
    # the timeZone, so any same-instant encoding is fine for the assertion).
    event_start = datetime.combine(first, time(2, 30), tzinfo=timezone.utc) + timedelta(days=1)
    app_settings = {
        "host": "comedy.ticketspice.com",
        "status": 1,
        "formName": "2026 Comedy Uncorked @ Retzlaff Vineyards",
        "formURL": _RETZLAFF_URL,
        "timeZone": "America/Los_Angeles",
        "eventStart": event_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    categories = [
        {"id": f"cat-{i}", "label": d.strftime("%B %-d"), "description": "Comic A, Comic B"}
        for i, d in enumerate(dates)
    ]
    categories.append({"id": "cat-don", "label": "Donation to Open Heart Kitchen", "description": "x"})
    levels = [
        {"label": f"{d.strftime('%B %-d')} GA", "price": "40", "category": f"cat-{i}", "visible": True}
        for i, d in enumerate(dates)
    ]
    form_data = {"type": "form", "soldOut": False, "elements": [{"type": "ticketBlock", "categories": categories, "levels": levels}]}
    return _boot_html(app_settings, form_data)


@pytest.mark.asyncio
async def test_full_scrape_persists_one_show_per_future_date(monkeypatch):
    club = _retzlaff_club()
    today = datetime.now(timezone.utc).date()
    future_dates = [today + timedelta(days=7), today + timedelta(days=35), today + timedelta(days=63)]

    scraper = TicketSpiceScraper(club)

    async def fake_fetch(url):
        return _future_multidate_html(future_dates)

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch)

    shows = await scraper.scrape_async()

    # One Show per upcoming date, attached to the configured club, at 7:30pm PT.
    assert len(shows) == 3
    assert all(s.club_id == 4242 for s in shows)
    assert sorted(s.date.date() for s in shows) == sorted(future_dates)
    assert all(s.date.hour == 19 and s.date.minute == 30 for s in shows)
    assert all(s.show_page_url == _RETZLAFF_URL for s in shows)
    assert all(s.tickets for s in shows)
