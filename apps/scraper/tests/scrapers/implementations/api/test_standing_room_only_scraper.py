"""Tests for the Standing Room Only (SRO) box-office scraper."""

import json
from datetime import datetime, timezone

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.standing_room_only.data import (
    StandingRoomOnlyPageData,
)
from laughtrack.scrapers.implementations.api.standing_room_only.extractor import (
    StandingRoomOnlyExtractor,
)
from laughtrack.scrapers.implementations.api.standing_room_only.scraper import (
    StandingRoomOnlyScraper,
)

_ORIGIN = "https://www.standingroomonlytickets.com"
_SOURCE_URL = f"{_ORIGIN}/Event/ReadLiveEvents"

# Far-future epoch (convention #11: avoid test time-bombs) — 2099-07-09 23:30 UTC
# = 7:30 PM America/Detroit (EDT, UTC-4).
_FUTURE_MS = int(datetime(2099, 7, 9, 23, 30, tzinfo=timezone.utc).timestamp() * 1000)
_FUTURE_MS_2 = int(datetime(2099, 7, 10, 23, 0, tzinfo=timezone.utc).timestamp() * 1000)
_PAST_MS = int(datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
# .NET DateTime.MinValue sentinel used for unset End/OnSale fields.
_MIN_DATE_MS = -62135578800000


def _show(start_ms: int = _FUTURE_MS, is_old: bool = False, **overrides) -> dict:
    row = {
        "Start": f"/Date({start_ms})/",
        "End": f"/Date({_MIN_DATE_MS})/",
        "IsShowOld": is_old,
    }
    row.update(overrides)
    return row


def _event(event_id: int = 522, title: str = "Kate Brindle", shows: list | None = None) -> dict:
    return {
        "Id": event_id,
        "EventTitle": title,
        "Shows": shows if shows is not None else [_show()],
    }


def _payload(events: list) -> dict:
    return {"Data": events, "Total": len(events)}


def _club(timezone_name: str = "America/Detroit", source_url: str = _SOURCE_URL) -> Club:
    club = Club(
        id=999,
        name="One Night Stans Comedy Club",
        address="4761 Highland Rd",
        website="https://www.onenightstans.club/",
        popularity=0,
        zip_code="48328",
        phone_number="",
        visible=True,
        timezone=timezone_name,
        city="Waterford Township",
        state="MI",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="standing_room_only",
        source_url=source_url,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


# ---- registry / targets --------------------------------------------------

def test_registry_resolves_standing_room_only_key():
    assert ScraperResolver().get("standing_room_only") is StandingRoomOnlyScraper


async def test_collect_targets_builds_read_live_events_url():
    scraper = StandingRoomOnlyScraper(_club())
    assert await scraper.collect_scraping_targets() == [_SOURCE_URL]


async def test_collect_targets_derives_origin_from_full_url():
    """source_url path is ignored — the ReadLiveEvents target is host-derived."""
    scraper = StandingRoomOnlyScraper(_club(source_url=f"{_ORIGIN}/WebOffice/EventList/522"))
    assert await scraper.collect_scraping_targets() == [_SOURCE_URL]


async def test_collect_targets_empty_on_invalid_source_url():
    scraper = StandingRoomOnlyScraper(_club(source_url="not-a-url"))
    assert await scraper.collect_scraping_targets() == []


# ---- extractor -----------------------------------------------------------

def test_extractor_fans_event_into_one_event_per_showtime():
    """A headliner residency with 3 shows -> 3 StandingRoomOnlyEvent objects."""
    events = StandingRoomOnlyExtractor.extract_events(
        _payload([_event(shows=[_show(_FUTURE_MS), _show(_FUTURE_MS_2), _show(_FUTURE_MS + 86400000)])]),
        _ORIGIN,
    )
    assert len(events) == 3
    assert {e.title for e in events} == {"Kate Brindle"}
    assert {e.start_ms for e in events} == {_FUTURE_MS, _FUTURE_MS_2, _FUTURE_MS + 86400000}


def test_extractor_builds_weboffice_page_url():
    events = StandingRoomOnlyExtractor.extract_events(_payload([_event(event_id=527)]), _ORIGIN)
    assert events[0].show_page_url == f"{_ORIGIN}/WebOffice/EventList/527"


def test_extractor_drops_past_showtimes():
    events = StandingRoomOnlyExtractor.extract_events(
        _payload([_event(shows=[_show(_FUTURE_MS), _show(_PAST_MS)])]),
        _ORIGIN,
    )
    assert [e.start_ms for e in events] == [_FUTURE_MS]


def test_extractor_drops_is_show_old():
    events = StandingRoomOnlyExtractor.extract_events(
        _payload([_event(shows=[_show(_FUTURE_MS, is_old=True)])]),
        _ORIGIN,
    )
    assert events == []


def test_extractor_drops_min_date_sentinel():
    events = StandingRoomOnlyExtractor.extract_events(
        _payload([_event(shows=[_show(_MIN_DATE_MS)])]),
        _ORIGIN,
    )
    assert events == []


def test_extractor_skips_events_missing_id_or_title_or_shows():
    payload = _payload([
        _event(event_id=1, title="Good"),
        {"Id": None, "EventTitle": "No Id", "Shows": [_show()]},
        {"Id": "abc", "EventTitle": "Non-numeric Id", "Shows": [_show()]},
        {"Id": 2, "EventTitle": "", "Shows": [_show()]},
        {"Id": 3, "EventTitle": "No Shows", "Shows": None},
    ])
    events = StandingRoomOnlyExtractor.extract_events(payload, _ORIGIN)
    assert [e.event_id for e in events] == [1]


def test_extractor_non_dict_payload_returns_empty():
    assert StandingRoomOnlyExtractor.extract_events([], _ORIGIN) == []
    assert StandingRoomOnlyExtractor.extract_events({"Data": "nope"}, _ORIGIN) == []


def test_parse_dotnet_ms_handles_trailing_offset_and_garbage():
    parse = StandingRoomOnlyExtractor._parse_dotnet_ms
    assert parse(f"/Date({_FUTURE_MS}-0400)/") == _FUTURE_MS
    assert parse("/Date()/") is None
    assert parse("garbage") is None
    assert parse(None) is None
    assert parse(_FUTURE_MS) is None  # not a string


# ---- event.to_show -------------------------------------------------------

def test_event_to_show_localizes_utc_epoch_to_club_tz():
    events = StandingRoomOnlyExtractor.extract_events(_payload([_event()]), _ORIGIN)
    show = events[0].to_show(_club())
    assert show is not None
    assert show.name == "Kate Brindle"
    assert show.date.tzinfo is not None
    # 23:30 UTC -> 19:30 in America/Detroit (EDT)
    assert show.date.hour == 19 and show.date.minute == 30
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == f"{_ORIGIN}/WebOffice/EventList/522"


# ---- get_data / scrape_async (post_form mocked) --------------------------

async def test_get_data_builds_events(monkeypatch):
    scraper = StandingRoomOnlyScraper(_club())

    async def fake_post_form(url, data):
        assert url == _SOURCE_URL
        assert data == ""
        return json.dumps(_payload([_event(shows=[_show(_FUTURE_MS), _show(_FUTURE_MS_2)])]))

    monkeypatch.setattr(scraper, "post_form", fake_post_form)
    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, StandingRoomOnlyPageData)
    assert len(page.event_list) == 2


async def test_get_data_empty_body_returns_none(monkeypatch):
    scraper = StandingRoomOnlyScraper(_club())

    async def fake_post_form(url, data):
        return ""

    monkeypatch.setattr(scraper, "post_form", fake_post_form)
    assert await scraper.get_data(_SOURCE_URL) is None


async def test_get_data_non_json_returns_none(monkeypatch):
    scraper = StandingRoomOnlyScraper(_club())

    async def fake_post_form(url, data):
        return "<html>Login</html>"

    monkeypatch.setattr(scraper, "post_form", fake_post_form)
    assert await scraper.get_data(_SOURCE_URL) is None


async def test_get_data_no_upcoming_shows_returns_none(monkeypatch):
    scraper = StandingRoomOnlyScraper(_club())

    async def fake_post_form(url, data):
        return json.dumps(_payload([_event(shows=[_show(_PAST_MS)])]))

    monkeypatch.setattr(scraper, "post_form", fake_post_form)
    assert await scraper.get_data(_SOURCE_URL) is None


async def test_scrape_async_produces_shows(monkeypatch):
    """End-to-end: targets -> get_data -> transformer pipeline -> Shows."""
    scraper = StandingRoomOnlyScraper(_club())

    async def fake_post_form(url, data):
        return json.dumps(_payload([
            _event(event_id=522, title="Kate Brindle", shows=[_show(_FUTURE_MS)]),
            _event(event_id=523, title="Frank Roche", shows=[_show(_FUTURE_MS_2)]),
        ]))

    monkeypatch.setattr(scraper, "post_form", fake_post_form)
    shows = await scraper.scrape_async()
    assert len(shows) == 2
    for show in shows:
        assert show.club_id == scraper.club.id
        assert show.date is not None and show.date.tzinfo is not None
        assert show.tickets
        assert show.tickets[0].purchase_url.startswith(f"{_ORIGIN}/WebOffice/EventList/")
