"""
Pipeline smoke tests for SunsetStripScraper and SquadUpEvent.

Exercises the JSON extraction path against minimal fixtures that mirror
the real SquadUP API response structure, and unit-tests the
SquadUpEvent.to_show() transformation path.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.scrapers.implementations.venues.sunset_strip.extractor import (
    SunsetStripEventExtractor,
)
from laughtrack.scrapers.implementations.venues.sunset_strip.page_data import (
    SunsetStripPageData,
)
from laughtrack.scrapers.implementations.venues.sunset_strip.scraper import (
    SunsetStripScraper,
)

SHOWS_URL = "https://www.sunsetstripatx.com/events"


def _club() -> Club:
    return Club(
        id=1,
        name="Sunset Strip Comedy Club",
        address="214 E 6th Street, Unit C",
        website="https://www.sunsetstripatx.com",
        scraping_url=SHOWS_URL,
        popularity=0,
        zip_code="78701",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _fixture_events():
    """
    Minimal SquadUP API event list mirroring the real API response.
    Contains three events: a comedian headliner, a generic showcase, and
    a generic secret show.
    """
    return [
        {
            "id": 111111,
            "name": "Jane Smith Live",
            "start_at": "2026-04-01T20:00:00-05:00",
            "end_at": "2026-04-01T22:00:00-05:00",
            "url": "https://squadup.com/events/jane-smith-live-1",
            "timezone_name": "America/Chicago",
            "timezone_abbreviation": "CDT",
        },
        {
            "id": 222222,
            "name": "Comedy Gold",
            "start_at": "2026-04-03T20:00:00-05:00",
            "end_at": "2026-04-03T22:00:00-05:00",
            "url": "https://squadup.com/events/comedy-gold-55",
            "timezone_name": "America/Chicago",
            "timezone_abbreviation": "CDT",
        },
        {
            "id": 333333,
            "name": "Deathsquad Secret Show",
            "start_at": "2026-04-02T20:00:00-05:00",
            "end_at": "2026-04-02T23:30:00-05:00",
            "url": "https://squadup.com/events/deathsquad-secret-show-90",
            "timezone_name": "America/Chicago",
            "timezone_abbreviation": "CDT",
        },
    ]


# ---------------------------------------------------------------------------
# SquadUpEvent.extract_performers() unit tests
# ---------------------------------------------------------------------------


def test_extract_performers_comedian_name():
    """extract_performers() returns the name for a plain headliner title."""
    assert SquadUpEvent.extract_performers("Jane Smith Live") == ["Jane Smith Live"]


def test_extract_performers_and_friends():
    """extract_performers() strips ' and Friends' suffix."""
    assert SquadUpEvent.extract_performers("Mike Jones and Friends") == ["Mike Jones"]


def test_extract_performers_and_friend_singular():
    """extract_performers() strips ' and Friend' (singular) suffix."""
    assert SquadUpEvent.extract_performers("Sara Lee and Friend") == ["Sara Lee"]


def test_extract_performers_showcase_is_generic():
    """extract_performers() returns [] for a generic showcase title."""
    assert SquadUpEvent.extract_performers("Comedy Showcase") == []


def test_extract_performers_comedy_gold_is_generic():
    """extract_performers() returns [] for 'Comedy Gold'."""
    assert SquadUpEvent.extract_performers("Comedy Gold") == []


def test_extract_performers_secret_show_is_generic():
    """extract_performers() returns [] for a 'Secret Show' title."""
    assert SquadUpEvent.extract_performers("Deathsquad Secret Show") == []


def test_extract_performers_open_mic_is_generic():
    """extract_performers() returns [] for an open mic title."""
    assert SquadUpEvent.extract_performers("Open Mic Night") == []


# ---------------------------------------------------------------------------
# SunsetStripEventExtractor.extract_shows() unit tests
# ---------------------------------------------------------------------------


def test_extractor_returns_all_events():
    """extract_shows() converts all valid event dicts to SquadUpEvent objects."""
    events = SunsetStripEventExtractor.extract_shows(_fixture_events())
    assert len(events) == 3


def test_extractor_headliner_has_performer():
    """extract_shows() extracts the comedian name from a headliner title."""
    events = SunsetStripEventExtractor.extract_shows(_fixture_events())
    jane = next((e for e in events if e.event_id == 111111), None)
    assert jane is not None
    assert jane.performers == ["Jane Smith Live"]


def test_extractor_generic_show_has_no_performers():
    """extract_shows() returns [] performers for generic showcase titles."""
    events = SunsetStripEventExtractor.extract_shows(_fixture_events())
    comedy_gold = next((e for e in events if e.event_id == 222222), None)
    assert comedy_gold is not None
    assert comedy_gold.performers == []


def test_extractor_parses_ticket_url():
    """extract_shows() sets the SquadUP URL as the ticket URL."""
    events = SunsetStripEventExtractor.extract_shows(_fixture_events())
    jane = next((e for e in events if e.event_id == 111111), None)
    assert jane is not None
    assert jane.url == "https://squadup.com/events/jane-smith-live-1"


def test_extractor_skips_events_missing_required_fields():
    """extract_shows() skips event dicts that are missing id, start_at, or url."""
    bad_events = [
        {"id": None, "name": "No ID Show", "start_at": "2026-04-01T20:00:00-05:00",
         "url": "https://squadup.com/events/no-id", "timezone_name": "America/Chicago"},
        {"id": 999, "name": "No Date Show", "start_at": None,
         "url": "https://squadup.com/events/no-date", "timezone_name": "America/Chicago"},
        {"id": 998, "name": "No URL Show", "start_at": "2026-04-01T20:00:00-05:00",
         "url": "", "timezone_name": "America/Chicago"},
    ]
    events = SunsetStripEventExtractor.extract_shows(bad_events)
    assert events == []


# ---------------------------------------------------------------------------
# SquadUpEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    event_id=111111,
    name="Jane Smith Live",
    start_at="2026-04-01T20:00:00-05:00",
    url="https://squadup.com/events/jane-smith-live-1",
    timezone_name="America/Chicago",
    performers=None,
) -> SquadUpEvent:
    return SquadUpEvent(
        event_id=event_id,
        name=name,
        start_at=start_at,
        url=url,
        timezone_name=timezone_name,
        performers=performers if performers is not None else ["Jane Smith Live"],
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct event name."""
    event = _make_event(name="Jane Smith Live")
    show = event.to_show(_club())
    assert show is not None
    assert show.name == "Jane Smith Live"


def test_to_show_correct_date_and_time():
    """to_show() parses the ISO 8601 start_at into the correct date components."""
    event = _make_event(start_at="2026-04-01T20:00:00-05:00")
    show = event.to_show(_club())
    assert show is not None
    assert show.date.month == 4
    assert show.date.day == 1
    assert show.date.hour == 20


def test_to_show_ticket_url_is_squadup_url():
    """to_show() sets the ticket purchase URL to the SquadUP event URL."""
    event = _make_event(url="https://squadup.com/events/jane-smith-live-1")
    show = event.to_show(_club())
    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://squadup.com/events/jane-smith-live-1"


def test_to_show_comedian_in_lineup():
    """to_show() links the comedian name to the show's lineup."""
    event = _make_event(performers=["Jane Smith Live"])
    show = event.to_show(_club())
    assert show is not None
    assert len(show.lineup) == 1
    assert show.lineup[0].name == "Jane Smith Live"


def test_to_show_no_performers_empty_lineup():
    """to_show() produces an empty lineup for a generic show with no performers."""
    event = _make_event(name="Comedy Gold", performers=[])
    show = event.to_show(_club())
    assert show is not None
    assert show.lineup == []


def test_to_show_returns_none_on_invalid_date():
    """to_show() returns None when start_at cannot be parsed as ISO 8601."""
    event = _make_event(start_at="not-a-date")
    show = event.to_show(_club())
    assert show is None


# ---------------------------------------------------------------------------
# SunsetStripScraper.get_data() integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches API pages and returns SunsetStripPageData with events."""
    scraper = SunsetStripScraper(_club())

    async def fake_fetch(self, page: int):
        if page == 1:
            return {"events": _fixture_events(), "meta": {"paging": {"total_pages": 1}}}
        return None

    monkeypatch.setattr(SunsetStripScraper, "_fetch_events_page", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)

    assert isinstance(result, SunsetStripPageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_deduplicates_across_pages(monkeypatch):
    """get_data() deduplicates events by event_id across multiple pages."""
    scraper = SunsetStripScraper(_club())
    call_count = 0

    async def fake_fetch(self, page: int):
        nonlocal call_count
        call_count += 1
        if page <= 2:
            return {
                "events": _fixture_events(),
                "meta": {"paging": {"total_pages": 2}},
            }
        return None

    monkeypatch.setattr(SunsetStripScraper, "_fetch_events_page", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)

    assert result is not None
    assert len(result.event_list) == 3  # 3 unique IDs despite 2 pages of duplicates


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the API returns an empty event list."""
    scraper = SunsetStripScraper(_club())

    async def fake_fetch(self, page: int):
        return {"events": [], "meta": {"paging": {"total_pages": 1}}}

    monkeypatch.setattr(SunsetStripScraper, "_fetch_events_page", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fetch_fails(monkeypatch):
    """get_data() returns None when _fetch_events_page returns None."""
    scraper = SunsetStripScraper(_club())

    async def fake_fetch(self, page: int):
        return None

    monkeypatch.setattr(SunsetStripScraper, "_fetch_events_page", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_paginates_all_pages(monkeypatch):
    """get_data() fetches all pages indicated by meta.paging.total_pages."""
    scraper = SunsetStripScraper(_club())
    fetched_pages = []

    async def fake_fetch(self, page: int):
        fetched_pages.append(page)
        return {
            "events": [
                {
                    "id": page * 1000,
                    "name": f"Show Page {page}",
                    "start_at": "2026-04-01T20:00:00-05:00",
                    "url": f"https://squadup.com/events/show-page-{page}",
                    "timezone_name": "America/Chicago",
                }
            ],
            "meta": {"paging": {"total_pages": 3}},
        }

    monkeypatch.setattr(SunsetStripScraper, "_fetch_events_page", fake_fetch)

    result = await scraper.get_data(SHOWS_URL)

    assert result is not None
    assert fetched_pages == [1, 2, 3]
    assert len(result.event_list) == 3
