"""
Pipeline smoke tests for IceHouseScraper and IceHouseEvent.

Exercises get_data() against mocked Tockify API responses matching the actual
tockify.com/api/ngevent structure, and unit-tests the IceHouseEvent.to_show()
transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ice_house import IceHouseEvent, _normalize_showclix_url
from laughtrack.scrapers.implementations.venues.ice_house.scraper import IceHouseScraper
from laughtrack.scrapers.implementations.venues.ice_house.data import IceHousePageData
from laughtrack.scrapers.implementations.venues.ice_house.extractor import IceHouseExtractor


def _club() -> Club:
    return Club(
        id=210,
        name="Ice House Comedy Club",
        address="24 N Mentor Ave",
        website="https://icehousecomedy.com",
        scraping_url="https://tockify.com/api/ngevent?calname=theicehouse&max=200",
        popularity=0,
        zip_code="91106",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _raw_event(
    uid="42",
    title="Comedy Night",
    # 2026-04-01T19:30:00-07:00 in ms = 1775097000000
    start_ms=1775097000000,
    ticket_url="https://www.showclix.com/event/comedy-night-4-1-26",
    tzid="America/Los_Angeles",
) -> dict:
    return {
        "eid": {"uid": uid, "seq": 0, "tid": start_ms, "rid": 0},
        "when": {
            "start": {"millis": start_ms, "tzid": tzid, "ltz": "PDT", "offset": -25200000},
            "end": {"millis": start_ms + 5400000, "tzid": tzid, "ltz": "PDT", "offset": -25200000},
            "allDay": False,
        },
        "content": {
            "summary": {"text": title},
            "description": {"text": ""},
            "customButtonText": "GET TICKETS",
            "customButtonLink": ticket_url,
            "noDetail": True,
            "tagset": {"tags": {}},
            "imageId": "",
            "attachments": [],
            "version": 1,
            "imageSets": [],
            "vlocation": {},
        },
        "status": {"name": "scheduled"},
        "kind": "singleton",
        "isExternal": False,
    }


def _api_response(events: list) -> dict:
    return {
        "events": events,
        "metaData": {
            "from": 1,
            "to": len(events),
            "start": 0,
            "end": len(events),
            "hasNext": False,
            "hasPrev": False,
        },
    }


# ---------------------------------------------------------------------------
# _normalize_showclix_url tests
# ---------------------------------------------------------------------------


def test_normalize_embed_url_to_www():
    """embed.showclix.com URLs are normalized to www.showclix.com."""
    raw = "https://embed.showclix.com/event/comedy-night-4-1-26"
    assert _normalize_showclix_url(raw) == "https://www.showclix.com/event/comedy-night-4-1-26"


def test_normalize_www_url_unchanged():
    """www.showclix.com URLs are returned unchanged."""
    url = "https://www.showclix.com/event/comedy-night-4-1-26"
    assert _normalize_showclix_url(url) == url


# ---------------------------------------------------------------------------
# IceHouseExtractor tests
# ---------------------------------------------------------------------------


def test_extract_events_returns_events_from_response():
    """extract_events() parses an API response dict into IceHouseEvent objects."""
    raw = _api_response([
        _raw_event(uid="1", title="Show A"),
        _raw_event(uid="2", title="Show B"),
        _raw_event(uid="3", title="Show C"),
    ])
    events = IceHouseExtractor.extract_events(raw)

    assert len(events) == 3
    titles = {e.title for e in events}
    assert "Show A" in titles
    assert "Show B" in titles
    assert "Show C" in titles


def test_extract_events_returns_empty_list_for_empty_events():
    """extract_events() returns an empty list when the events array is empty."""
    events = IceHouseExtractor.extract_events(_api_response([]))
    assert events == []


def test_extract_events_returns_empty_list_for_missing_events_key():
    """extract_events() returns an empty list when the response has no events key."""
    events = IceHouseExtractor.extract_events({})
    assert events == []


def test_extract_events_skips_events_with_no_title():
    """extract_events() skips events with an empty or missing summary text."""
    raw = _api_response([
        {**_raw_event(uid="1"), "content": {**_raw_event()["content"], "summary": {"text": ""}}},
        _raw_event(uid="2", title="Has Title"),
    ])
    events = IceHouseExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Has Title"


def test_extract_events_skips_events_with_no_uid():
    """extract_events() skips events with missing eid.uid."""
    no_uid = _raw_event()
    no_uid["eid"] = {}
    raw = _api_response([no_uid, _raw_event(uid="2", title="Has UID")])
    events = IceHouseExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Has UID"


def test_extract_events_preserves_ticket_url():
    """extract_events() correctly captures the customButtonLink as ticket_url."""
    raw = _api_response([_raw_event(uid="1", ticket_url="https://www.showclix.com/event/test-show")])
    events = IceHouseExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].ticket_url == "https://www.showclix.com/event/test-show"


def test_extract_events_preserves_start_ms():
    """extract_events() correctly captures the start timestamp in milliseconds."""
    raw = _api_response([_raw_event(uid="1", start_ms=1775097000000)])
    events = IceHouseExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].start_ms == 1775097000000


def test_extract_events_two_concurrent_shows():
    """extract_events() returns both shows when two events start at the same time.

    The Tockify API uses uid as the unique identifier, not the timestamp — so
    two events at the same start_ms but different uids must both be extracted.
    """
    raw = _api_response([
        _raw_event(uid="10", title="Show A", start_ms=1775097000000),
        _raw_event(uid="11", title="Show B", start_ms=1775097000000),
    ])
    events = IceHouseExtractor.extract_events(raw)

    assert len(events) == 2, "Both concurrent shows must be extracted"
    titles = {e.title for e in events}
    assert "Show A" in titles
    assert "Show B" in titles


# ---------------------------------------------------------------------------
# IceHouseEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    uid="42",
    title="Comedy Night",
    start_ms=1775097000000,   # 2026-04-01T19:30:00-07:00
    ticket_url="https://www.showclix.com/event/comedy-night-4-1-26",
    timezone="America/Los_Angeles",
) -> IceHouseEvent:
    return IceHouseEvent(
        uid=uid,
        title=title,
        start_ms=start_ms,
        ticket_url=ticket_url,
        timezone=timezone,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(title="Comedy Night Live")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Comedy Night Live"


def test_to_show_parses_ms_timestamp_in_la_timezone():
    """to_show() correctly converts a ms timestamp to a datetime in LA time."""
    # 1775097000000 ms = 2026-04-01T19:30:00-07:00 (PDT)
    event = _make_event(start_ms=1775097000000)
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 1
    assert show.date.hour == 19
    assert show.date.minute == 30


def test_to_show_uses_showclix_url_as_ticket_url():
    """to_show() uses the ShowClix event URL as the ticket/show page URL."""
    event = _make_event(ticket_url="https://www.showclix.com/event/comedy-night-99")
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == "https://www.showclix.com/event/comedy-night-99"
    assert len(show.tickets) == 1
    assert "showclix.com" in show.tickets[0].purchase_url


def test_to_show_normalizes_embed_ticket_url():
    """to_show() normalizes embed.showclix.com URLs to www.showclix.com."""
    event = _make_event(ticket_url="https://embed.showclix.com/event/comedy-night-99")
    show = event.to_show(_club())

    assert show is not None
    assert "www.showclix.com" in show.show_page_url
    assert "embed.showclix.com" not in show.show_page_url


def test_to_show_returns_none_for_invalid_timezone():
    """to_show() returns None when the timezone cannot be parsed."""
    event = _make_event(timezone="Not/A/Timezone")
    show = event.to_show(_club())

    assert show is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_single_url():
    """collect_scraping_targets() returns exactly one URL."""
    scraper = IceHouseScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 1


@pytest.mark.asyncio
async def test_collect_scraping_targets_url_contains_calname():
    """collect_scraping_targets() URL includes the Ice House calname."""
    scraper = IceHouseScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert "calname=theicehouse" in targets[0]


@pytest.mark.asyncio
async def test_collect_scraping_targets_url_contains_startms():
    """collect_scraping_targets() URL includes a startms timestamp."""
    scraper = IceHouseScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert "startms=" in targets[0]


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches the Tockify API and returns IceHousePageData with events."""
    scraper = IceHouseScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return _api_response([
            _raw_event(uid="1", title="Show A"),
            _raw_event(uid="2", title="Show B"),
        ])

    monkeypatch.setattr(IceHouseScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data("https://tockify.com/api/ngevent?calname=theicehouse&max=200&startms=0")

    assert isinstance(result, IceHousePageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_events(monkeypatch):
    """get_data() returns None when the API returns an empty events list."""
    scraper = IceHouseScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return _api_response([])

    monkeypatch.setattr(IceHouseScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data("https://tockify.com/api/ngevent?calname=theicehouse&max=200&startms=0")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_null_response(monkeypatch):
    """get_data() returns None when fetch_json returns None."""
    scraper = IceHouseScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(IceHouseScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data("https://tockify.com/api/ngevent?calname=theicehouse&max=200&startms=0")
    assert result is None
