"""Unit tests for the generic EventON extractor (TASK-2926).

Fixtures mirror the verified live shape of jillysmusicroom.com (EventON 4.0.6):
- the admin-ajax ``eventon_init_load`` loader returns
  ``cals.<cal_id>.json`` = a list of event dicts with ``event_id``,
  ``event_title`` and ``event_start_unix`` (local wall-clock encoded as UTC).
- ``/wp-json/wp/v2/ajde_events?include=<ids>`` yields id -> {link, event_type[]}.
- ``/wp-json/wp/v2/event_type`` exposes a "comedy" term whose id tags comedy
  events.
"""

import calendar

import pytz

from laughtrack.core.entities.event.eventon import EventONEvent
from laughtrack.scrapers.implementations.api.eventon.extractor import (
    build_loader_body,
    build_rest_meta,
    discover_term_ids,
    extract_events,
    parse_loader_events,
)

# Far-future wall-clock unix timestamps (2099) encoded as UTC, matching how
# EventON stores event_start_unix — keeps the past-filter from time-bombing.
FUTURE_7PM = calendar.timegm((2099, 7, 30, 19, 0, 0, 0, 0, 0))  # 2099-07-30 19:00
FUTURE_8PM = calendar.timegm((2099, 8, 15, 20, 0, 0, 0, 0, 0))

LOADER_JSON = {
    "cal_def": {"show_jsonld": True},
    "cals": {
        "MAIN": {
            "sc": {},
            "json": [
                {
                    "event_id": 4500,
                    "event_title": "Mid-Life Crisis: A Comedy Improv Troupe",
                    "event_start_unix": FUTURE_7PM,
                    "event_past": "no",
                },
                {
                    "event_id": 4600,
                    "event_title": "Swizzle Stick Band",
                    "event_start_unix": FUTURE_8PM,
                    "event_past": "no",
                },
                {
                    "event_id": 1000,
                    "event_title": "An Old Past Show",
                    "event_start_unix": 1577836800,  # 2020 — past flag set
                    "event_past": "yes",
                },
            ],
            "html": "<div>calendar shell</div>",
        }
    },
}

REST_ITEMS = [
    {"id": 4500, "link": "https://jillysmusicroom.com/events/mid-life-crisis/", "event_type": [8, 46]},
    {"id": 4600, "link": "https://jillysmusicroom.com/events/swizzle-stick-band/", "event_type": [8, 6]},
]

EVENT_TYPE_TERMS = [
    {"id": 8, "name": "ENTERTAINMENT", "slug": "entertainment"},
    {"id": 6, "name": "MUSIC", "slug": "music"},
    {"id": 46, "name": "COMEDY", "slug": "comedy"},
]


class _Club:
    id = 1
    name = "Jilly's Music Room"
    timezone = "America/New_York"


class TestBuildLoaderBody:
    def test_includes_action_and_full_sc_set(self):
        body = build_loader_body(cal_id="MAIN")
        assert "action=eventon_init_load" in body
        # nested sc params are urlencoded as cals[MAIN][sc][key]=value
        assert "cals%5BMAIN%5D%5Bsc%5D%5Bevent_past_future%5D=future" in body
        assert "cals%5BMAIN%5D%5Bsc%5D%5Bhide_past%5D=yes" in body
        assert "cals%5BMAIN%5D%5Bsc%5D%5Bcal_id%5D=MAIN" in body

    def test_cal_id_override(self):
        body = build_loader_body(cal_id="EVCAL2")
        assert "cals%5BEVCAL2%5D%5Bsc%5D%5Bcal_id%5D=EVCAL2" in body


class TestParseLoaderEvents:
    def test_drops_past_flagged_events(self):
        events = parse_loader_events(LOADER_JSON, cal_id="MAIN")
        ids = [e["event_id"] for e in events]
        assert ids == [4500, 4600]

    def test_falls_back_to_evcal_prefixed_cal(self):
        payload = {"cals": {"evcal_calendar_MAIN": {"json": [{"event_id": 1, "event_title": "x", "event_start_unix": FUTURE_7PM}]}}}
        assert len(parse_loader_events(payload, cal_id="MAIN")) == 1

    def test_empty_on_malformed(self):
        assert parse_loader_events({}, cal_id="MAIN") == []
        assert parse_loader_events({"cals": {}}, cal_id="MAIN") == []


class TestDiscoverTermIds:
    def test_finds_comedy_term(self):
        assert discover_term_ids(EVENT_TYPE_TERMS) == {46}

    def test_no_match(self):
        assert discover_term_ids(EVENT_TYPE_TERMS, target_names=("opera",)) == set()


class TestExtractEvents:
    def test_joins_links_no_filter(self):
        meta = build_rest_meta(REST_ITEMS)
        events = extract_events(parse_loader_events(LOADER_JSON), meta)
        assert [e.title for e in events] == [
            "Mid-Life Crisis: A Comedy Improv Troupe",
            "Swizzle Stick Band",
        ]
        assert events[0].show_page_url == "https://jillysmusicroom.com/events/mid-life-crisis/"

    def test_comedy_filter_keeps_only_comedy(self):
        meta = build_rest_meta(REST_ITEMS)
        events = extract_events(parse_loader_events(LOADER_JSON), meta, comedy_term_ids={46})
        assert [e.title for e in events] == ["Mid-Life Crisis: A Comedy Improv Troupe"]

    def test_drops_event_without_rest_link(self):
        meta = build_rest_meta([REST_ITEMS[0]])  # only 4500 has a link
        events = extract_events(parse_loader_events(LOADER_JSON), meta)
        assert [e.title for e in events] == ["Mid-Life Crisis: A Comedy Improv Troupe"]

    def test_empty_filter_set_fails_closed(self):
        # A configured-but-unresolved comedy filter (empty set, not None) must
        # import NOTHING rather than flooding a comedy-only DB with all events.
        meta = build_rest_meta(REST_ITEMS)
        events = extract_events(parse_loader_events(LOADER_JSON), meta, comedy_term_ids=set())
        assert events == []


class TestToShow:
    def test_localizes_wall_clock_to_club_tz(self):
        ev = EventONEvent(
            title="Comedy Night",
            start_unix=FUTURE_7PM,
            show_page_url="https://jillysmusicroom.com/events/comedy-night/",
        )
        show = ev.to_show(_Club())
        assert show is not None
        local = show.date.astimezone(pytz.timezone("America/New_York"))
        assert (local.year, local.month, local.day, local.hour) == (2099, 7, 30, 19)
        assert show.tickets[0].purchase_url == "https://jillysmusicroom.com/events/comedy-night/"

    def test_past_event_returns_none(self):
        ev = EventONEvent(
            title="Old Show",
            start_unix=1577836800,  # 2020
            show_page_url="https://jillysmusicroom.com/events/old/",
        )
        assert ev.to_show(_Club()) is None


import json

from unittest.mock import AsyncMock

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.eventon.scraper import EventONScraper


def _make_scraper(event_type_filter=None):
    meta = {"event_type_filter": event_type_filter} if event_type_filter else {}
    src = ScrapingSource(
        platform="custom", scraper_key="eventon",
        source_url="https://jillysmusicroom.com", priority=0, enabled=True,
        id=1, club_id=999, metadata=meta,
    )
    club = Club(
        id=999, name="Jilly's Music Room", address="", website="https://jillysmusicroom.com",
        popularity=0, zip_code="44308", phone_number="", visible=True,
        timezone="America/New_York", city="Akron", state="OH",
        scraping_sources=[src], active_scraping_source=src,
    )
    return EventONScraper(club)


def _fetch_json_side_effect(url):
    if "ajde_events" in url:
        return REST_ITEMS
    if "event_type" in url:
        return EVENT_TYPE_TERMS
    return None


class TestGetDataOrchestration:
    async def test_comedy_filter_keeps_only_comedy(self):
        scraper = _make_scraper(event_type_filter="comedy")
        scraper.post_form = AsyncMock(return_value=json.dumps(LOADER_JSON))
        scraper.fetch_json = AsyncMock(side_effect=_fetch_json_side_effect)

        page = await scraper.get_data("https://jillysmusicroom.com")
        assert page is not None
        assert [e.title for e in page.event_list] == ["Mid-Life Crisis: A Comedy Improv Troupe"]

    async def test_no_filter_imports_all(self):
        scraper = _make_scraper(event_type_filter=None)
        scraper.post_form = AsyncMock(return_value=json.dumps(LOADER_JSON))
        scraper.fetch_json = AsyncMock(side_effect=_fetch_json_side_effect)

        page = await scraper.get_data("https://jillysmusicroom.com")
        assert page is not None
        assert {e.title for e in page.event_list} == {
            "Mid-Life Crisis: A Comedy Improv Troupe",
            "Swizzle Stick Band",
        }

    async def test_unresolved_filter_fails_closed(self):
        # event_type taxonomy returns no comedy term -> filter set() -> import none.
        scraper = _make_scraper(event_type_filter="comedy")
        scraper.post_form = AsyncMock(return_value=json.dumps(LOADER_JSON))

        def side_effect(url):
            if "ajde_events" in url:
                return REST_ITEMS
            if "event_type" in url:
                return [{"id": 6, "name": "MUSIC", "slug": "music"}]  # no comedy term
            return None

        scraper.fetch_json = AsyncMock(side_effect=side_effect)
        page = await scraper.get_data("https://jillysmusicroom.com")
        # No comedy term -> empty filter set -> nothing imported -> None page.
        assert page is None
