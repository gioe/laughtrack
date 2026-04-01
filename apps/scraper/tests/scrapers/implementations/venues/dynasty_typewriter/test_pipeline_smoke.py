"""
Pipeline smoke tests for DynastyTypewriterScraper and DynastyTypewriterEvent.

Exercises get_data() against mocked SquadUp API responses matching the actual
squadup.com structure, and unit-tests the DynastyTypewriterEvent.to_show()
transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.dynasty_typewriter import DynastyTypewriterEvent
from laughtrack.scrapers.implementations.venues.dynasty_typewriter.scraper import DynastyTypewriterScraper
from laughtrack.scrapers.implementations.venues.dynasty_typewriter.data import DynastyTypewriterPageData
from laughtrack.scrapers.implementations.venues.dynasty_typewriter.extractor import DynastyTypewriterExtractor

_SQUADUP_API_URL = (
    "https://www.squadup.com/api/v3/events"
    "?user_ids=7408591"
    "&page_size=100"
    "&topics_exclude=true"
    "&additional_attr=sold_out"
    "&include=custom_fields"
)


def _club() -> Club:
    return Club(
        id=200,
        name="Dynasty Typewriter",
        address="2511 Wilshire Blvd",
        website="https://www.dynastytypewriter.com",
        scraping_url=_SQUADUP_API_URL,
        popularity=0,
        zip_code="90057",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _raw_event(
    id_=131130,
    title="The Ultimate Improv Show",
    start_at="2026-04-01T19:30:00-07:00",
    url="https://squadup.com/events/the-ultimate-improv-show-30",
    timezone_name="America/Los_Angeles",
    location_name="Dynasty Typewriter",
) -> dict:
    return {
        "id": id_,
        "name": title,
        "start_at": start_at,
        "end_at": "2026-04-01T21:00:00-07:00",
        "url": url,
        "timezone_name": timezone_name,
        "sold_out": False,
        "ticketed": True,
        "location": {"name": location_name},
    }


def _api_response(events: list) -> dict:
    return {"events": events, "meta": {"messages": [], "paging": {"total_pages": 1}}}


# ---------------------------------------------------------------------------
# DynastyTypewriterExtractor tests
# ---------------------------------------------------------------------------


def test_extract_events_returns_events_from_response():
    """extract_events() parses an API response dict into DynastyTypewriterEvent objects."""
    raw = _api_response([
        _raw_event(id_=1, title="Show A"),
        _raw_event(id_=2, title="Show B"),
        _raw_event(id_=3, title="Show C"),
    ])
    events = DynastyTypewriterExtractor.extract_events(raw)

    assert len(events) == 3
    titles = {e.title for e in events}
    assert "Show A" in titles
    assert "Show B" in titles
    assert "Show C" in titles


def test_extract_events_returns_empty_list_for_empty_events():
    """extract_events() returns an empty list when the events array is empty."""
    events = DynastyTypewriterExtractor.extract_events(_api_response([]))
    assert events == []


def test_extract_events_returns_empty_list_for_missing_events_key():
    """extract_events() returns an empty list when the response has no events key."""
    events = DynastyTypewriterExtractor.extract_events({})
    assert events == []


def test_extract_events_skips_events_with_no_title():
    """extract_events() skips events with an empty or missing name."""
    raw = _api_response([
        {**_raw_event(id_=1), "name": ""},
        _raw_event(id_=2, title="Has Title"),
    ])
    events = DynastyTypewriterExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Has Title"


def test_extract_events_skips_events_with_no_start_at():
    """extract_events() skips events missing the start_at field."""
    raw = _api_response([
        {**_raw_event(id_=1), "start_at": ""},
        _raw_event(id_=2, title="Has Date"),
    ])
    events = DynastyTypewriterExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].title == "Has Date"


def test_extract_events_preserves_event_url():
    """extract_events() correctly captures the event URL."""
    raw = _api_response([_raw_event(id_=1, url="https://squadup.com/events/some-show-123")])
    events = DynastyTypewriterExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].url == "https://squadup.com/events/some-show-123"


def test_extract_events_captures_location_name():
    """extract_events() captures location.name from the API response."""
    raw = _api_response([_raw_event(id_=1, location_name="Dynasty Typewriter At The Hayworth")])
    events = DynastyTypewriterExtractor.extract_events(raw)

    assert len(events) == 1
    assert events[0].location_name == "Dynasty Typewriter At The Hayworth"


def test_extract_events_includes_hayworth_location_events():
    """Events with 'Dynasty Typewriter At The Hayworth' location are NOT filtered out.

    Both 'Dynasty Typewriter' and 'Dynasty Typewriter At The Hayworth' refer to
    the same physical venue at 2511 Wilshire Blvd, Los Angeles. All events from
    either location.name are included under the single club record.
    """
    raw = _api_response([
        _raw_event(id_=1, title="Main Show", location_name="Dynasty Typewriter"),
        _raw_event(id_=2, title="Hayworth Show", location_name="Dynasty Typewriter At The Hayworth"),
    ])
    events = DynastyTypewriterExtractor.extract_events(raw)

    assert len(events) == 2
    titles = {e.title for e in events}
    assert "Main Show" in titles
    assert "Hayworth Show" in titles


# ---------------------------------------------------------------------------
# DynastyTypewriterEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title="The Ultimate Improv Show",
    start_at="2026-04-01T19:30:00-07:00",
    url="https://squadup.com/events/the-ultimate-improv-show-30",
    timezone_name="America/Los_Angeles",
) -> DynastyTypewriterEvent:
    return DynastyTypewriterEvent(
        id="131130",
        title=title,
        start_at=start_at,
        url=url,
        timezone_name=timezone_name,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(title="Comedy Night Live")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Comedy Night Live"


def test_to_show_parses_iso8601_datetime_in_la_timezone():
    """to_show() correctly parses ISO 8601 datetime with UTC offset into LA time."""
    # "2026-04-01T19:30:00-07:00" = 7:30 PM PDT
    event = _make_event(start_at="2026-04-01T19:30:00-07:00")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 1
    assert show.date.hour == 19
    assert show.date.minute == 30


def test_to_show_uses_squadup_url_as_ticket_url():
    """to_show() uses the SquadUp event URL as the ticket/show page URL."""
    event = _make_event(url="https://squadup.com/events/comedy-night-99")
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == "https://squadup.com/events/comedy-night-99"
    assert len(show.tickets) == 1
    assert "squadup.com" in show.tickets[0].purchase_url


def test_to_show_returns_none_for_invalid_start_at():
    """to_show() returns None when start_at cannot be parsed."""
    event = _make_event(start_at="not-a-date")
    show = event.to_show(_club())

    assert show is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_single_url():
    """collect_scraping_targets() returns exactly one URL."""
    scraper = DynastyTypewriterScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 1


@pytest.mark.asyncio
async def test_collect_scraping_targets_url_contains_user_id():
    """collect_scraping_targets() URL includes the Dynasty Typewriter user_id."""
    scraper = DynastyTypewriterScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert "user_ids=7408591" in targets[0]


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


def _make_fake_session(status_code: int, payload: dict):
    """Return a fake AsyncSession context manager that returns *payload* as JSON."""

    class _FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return payload

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return _FakeResponse()

    return _FakeSession


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches the API and returns DynastyTypewriterPageData with events."""
    scraper = DynastyTypewriterScraper(_club())
    payload = _api_response([_raw_event(id_=1, title="Show A"), _raw_event(id_=2, title="Show B")])

    import laughtrack.scrapers.implementations.venues.dynasty_typewriter.scraper as mod
    monkeypatch.setattr(mod, "AsyncSession", lambda **kw: _make_fake_session(200, payload)())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_SQUADUP_API_URL)

    assert isinstance(result, DynastyTypewriterPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_events(monkeypatch):
    """get_data() returns None when the API returns an empty events list."""
    scraper = DynastyTypewriterScraper(_club())
    payload = _api_response([])

    import laughtrack.scrapers.implementations.venues.dynasty_typewriter.scraper as mod
    monkeypatch.setattr(mod, "AsyncSession", lambda **kw: _make_fake_session(200, payload)())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_SQUADUP_API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_403(monkeypatch):
    """get_data() returns None when the API returns HTTP 403."""
    scraper = DynastyTypewriterScraper(_club())

    import laughtrack.scrapers.implementations.venues.dynasty_typewriter.scraper as mod
    monkeypatch.setattr(mod, "AsyncSession", lambda **kw: _make_fake_session(403, {})())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_SQUADUP_API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_uses_bare_chrome_impersonation(monkeypatch):
    """get_data() uses AsyncSession(impersonate='chrome124') with no extra headers."""
    scraper = DynastyTypewriterScraper(_club())
    captured_kwargs: dict = {}

    class _FakeResponse:
        status_code = 200

        def json(self):
            return _api_response([_raw_event()])

    class _FakeSession:
        def __init__(self, **kw):
            captured_kwargs.update(kw)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return _FakeResponse()

    import laughtrack.scrapers.implementations.venues.dynasty_typewriter.scraper as mod
    monkeypatch.setattr(mod, "AsyncSession", _FakeSession)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    await scraper.get_data(_SQUADUP_API_URL)

    assert captured_kwargs.get("impersonate") == "chrome124"
