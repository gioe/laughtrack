"""Tests for the 1234ticket platform scraper (TASK-3350).

The 1234ticket landing-data API returns every event across the platform's
venues with no category, so the scraper filters to one venue (by UUID) and
applies an opt-in comedy title allowlist. These tests cover venue filtering,
the comedy include/exclude filter (matched against the de-hyphenated link
slug), the date+time combination, slug-derived naming, and past-event skipping.
"""

import pytest
from datetime import datetime, timezone

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticket1234.scraper import Ticket1234Scraper
from laughtrack.scrapers.implementations.api.ticket1234.data import Ticket1234PageData
from laughtrack.scrapers.implementations.api.ticket1234.extractor import (
    display_name,
    event_slug,
    show_datetime,
)

LANDING_URL = "https://api.1234ticket.com/api_040/landing-data"
FLAMINGO_UUID = "6853052c-f82a-4e10-9171-3f88889bf2df"
OTHER_UUID = "0000aaaa-0000-0000-0000-000000000000"


def _venue(uuid, name):
    return {"id": uuid, "name": name}


# Mirrors the live landing-data shape: title is an abbreviated lowercase word,
# the slug carries the real name, date = midnight venue-local in UTC,
# time = true-UTC time-of-day on a throwaway date.
PAYLOAD = {
    "ok": True,
    "data": {
        "events": [
            # Comedy at Flamingo (future): recurring stand-up. 8:30 PM ET.
            {"title": "edy", "description": "PRIMER SHOW EN VIVO",
             "date": "2099-07-10T04:00:00.000Z", "time": "2026-06-11T00:30:00.000Z",
             "link": "https://live.1234ticket.com/events/el-show-de-eddy-suarez-3228a60272",
             "venue": _venue(FLAMINGO_UUID, "Flamingo Theater Bar"), "venue_id": FLAMINGO_UUID},
            # Music at Flamingo (future): salsa concert — must be filtered OUT.
            {"title": "willy", "description": "CON WILLY SE BAILA",
             "date": "2099-06-27T04:00:00.000Z", "time": "2026-05-30T00:30:00.000Z",
             "link": "https://live.1234ticket.com/events/willy-chirino-d4353b8957",
             "venue": _venue(FLAMINGO_UUID, "Flamingo Theater Bar"), "venue_id": FLAMINGO_UUID},
            # Comedy but at a DIFFERENT venue — must be filtered OUT (wrong venue).
            {"title": "George", "description": "comedy",
             "date": "2099-08-01T04:00:00.000Z", "time": "2026-06-11T00:30:00.000Z",
             "link": "https://live.1234ticket.com/events/some-comedy-at-other-aaaa",
             "venue": _venue(OTHER_UUID, "La Scala de Miami"), "venue_id": OTHER_UUID},
            # Comedy at Flamingo but in the PAST — must be skipped.
            {"title": "alexis", "description": "QUE DESASTRE",
             "date": "2000-07-18T04:00:00.000Z", "time": "2026-04-23T00:30:00.000Z",
             "link": "https://live.1234ticket.com/events/alexis-valdes-87d5c38e29",
             "venue": _venue(FLAMINGO_UUID, "Flamingo Theater Bar"), "venue_id": FLAMINGO_UUID},
        ]
    },
}

COMEDY_PATTERNS = ["comedy", "comedian", "stand up", "standup", "humor",
                   "george harris", "eddy suarez", "alexis valdes"]


def _club():
    c = Club(id=99100, name='Flamingo Theater Bar', address='905 Brickell Bay Dr, Miami, FL 33131',
             website='https://live.1234ticket.com/venues/1', popularity=0, zip_code='33131',
             phone_number='', visible=True, timezone='America/New_York')
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform='custom', scraper_key='1234ticket', source_url=LANDING_URL,
        external_id=None,
        metadata={"venue_id": FLAMINGO_UUID, "include_title_patterns": COMEDY_PATTERNS},
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def test_event_slug_strips_trailing_hash():
    assert event_slug("https://live.1234ticket.com/events/el-show-de-eddy-suarez-3228a60272") \
        == "el-show-de-eddy-suarez"


def test_display_name_prefers_deslugified_when_title_abbreviated():
    # Abbreviated single-word title -> de-slugify the link.
    assert display_name("edy", "https://x/events/el-show-de-eddy-suarez-3228a60272") \
        == "El Show De Eddy Suarez"
    # Already-good multi-word title is kept verbatim.
    assert display_name("El Show De George Harris", "https://x/events/whatever-abcd1234") \
        == "El Show De George Harris"


def test_show_datetime_combines_date_and_time_to_utc():
    # date = Jul 10 midnight EDT (04:00Z); time = 00:30Z -> 8:30 PM EDT.
    # Expected true-UTC instant: Jul 11 00:30 UTC.
    dt = show_datetime("2099-07-10T04:00:00.000Z", "2026-06-11T00:30:00.000Z", "America/New_York")
    assert dt == datetime(2099, 7, 11, 0, 30, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_get_data_filters_to_venue_and_comedy(monkeypatch):
    scraper = Ticket1234Scraper(_club())

    calls = {"n": 0}

    async def fake_fetch_json(self, url, **kwargs):
        calls["n"] += 1
        # Single page of results; second call returns empty to stop pagination.
        return PAYLOAD if calls["n"] == 1 else {"ok": True, "data": {"events": []}}

    monkeypatch.setattr(Ticket1234Scraper, "fetch_json", fake_fetch_json)
    result = await scraper.get_data(LANDING_URL)

    assert isinstance(result, Ticket1234PageData)
    # Only the future Flamingo comedy event survives: music dropped, wrong-venue
    # dropped, past event dropped.
    assert len(result.event_list) == 1
    ev = result.event_list[0]
    assert ev.name == "El Show De Eddy Suarez"
    assert ev.start_date == datetime(2099, 7, 11, 0, 30, tzinfo=timezone.utc)
    assert ev.show_page_url.endswith("el-show-de-eddy-suarez-3228a60272")
