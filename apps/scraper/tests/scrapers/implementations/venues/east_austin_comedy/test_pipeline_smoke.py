"""
Pipeline smoke tests for EastAustinComedyScraper and EastAustinComedyEvent.

Exercises get_data() against mocked Netlify availability API responses and
unit-tests the EastAustinComedyEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.east_austin_comedy import EastAustinComedyEvent
from laughtrack.scrapers.implementations.venues.east_austin_comedy.data import (
    EastAustinComedyPageData,
)
from laughtrack.scrapers.implementations.venues.east_austin_comedy.extractor import (
    EastAustinComedyEventExtractor,
)
from laughtrack.scrapers.implementations.venues.east_austin_comedy.scraper import (
    EastAustinComedyScraper,
    _DAY_NAMES,
)

_SCRAPING_URL = "https://eastaustincomedy.com/"


def _club() -> Club:
    _c = Club(id=999, name='East Austin Comedy', address='2505 East 6th St. Suite D', website='https://eastaustincomedy.com', popularity=0, zip_code='78702', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=_SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _availability_response(*show_times: str, date: str = "2026-04-04") -> dict:
    """Build an availability API response for a given date and list of show times."""
    times = {t: {"ga": {"remaining": 70, "soldOut": False}} for t in show_times}
    return {"availability": {date: times}}


# ---------------------------------------------------------------------------
# EastAustinComedyEventExtractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_parses_single_date_and_time():
    data = _availability_response("8:00 PM", date="2026-04-04")
    events = EastAustinComedyEventExtractor.parse_availability(data)

    assert len(events) == 1
    assert events[0].date == "2026-04-04"
    assert events[0].time == "8:00 PM"


def test_extractor_parses_multiple_times_per_date():
    data = _availability_response("6:00 PM", "8:00 PM", "10:00 PM", date="2026-04-05")
    events = EastAustinComedyEventExtractor.parse_availability(data)

    assert len(events) == 3
    times = {e.time for e in events}
    assert times == {"6:00 PM", "8:00 PM", "10:00 PM"}


def test_extractor_parses_multiple_dates():
    data = {
        "availability": {
            "2026-04-04": {"8:00 PM": {"ga": {"remaining": 70, "soldOut": False}}},
            "2026-04-11": {"8:00 PM": {"ga": {"remaining": 50, "soldOut": False}}},
        }
    }
    events = EastAustinComedyEventExtractor.parse_availability(data)
    assert len(events) == 2
    dates = {e.date for e in events}
    assert dates == {"2026-04-04", "2026-04-11"}


def test_extractor_returns_empty_on_missing_availability_key():
    events = EastAustinComedyEventExtractor.parse_availability({})
    assert events == []


def test_extractor_returns_empty_on_non_dict_input():
    events = EastAustinComedyEventExtractor.parse_availability(None)
    assert events == []


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches all 7 weekday endpoints and returns EastAustinComedyPageData."""
    scraper = EastAustinComedyScraper(_club())

    call_count = 0

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        nonlocal call_count
        call_count += 1
        # Return one show slot for Saturday, empty for all others
        if "showDay=saturday" in url:
            return _availability_response("8:00 PM", date="2026-04-04")
        return {"availability": {}}

    monkeypatch.setattr(EastAustinComedyScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_SCRAPING_URL)

    assert isinstance(result, EastAustinComedyPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].date == "2026-04-04"
    assert result.event_list[0].time == "8:00 PM"
    assert call_count == 7  # one call per weekday


@pytest.mark.asyncio
async def test_get_data_aggregates_all_weekdays(monkeypatch):
    """get_data() collects events from multiple weekday responses."""
    scraper = EastAustinComedyScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        if "showDay=friday" in url:
            return _availability_response("6:00 PM", "8:00 PM", "10:00 PM", date="2026-04-03")
        if "showDay=saturday" in url:
            return _availability_response("6:00 PM", "8:00 PM", "10:00 PM", date="2026-04-04")
        return {"availability": {}}

    monkeypatch.setattr(EastAustinComedyScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_SCRAPING_URL)

    assert isinstance(result, EastAustinComedyPageData)
    assert len(result.event_list) == 6


@pytest.mark.asyncio
async def test_get_data_deduplicates_same_date_time(monkeypatch):
    """get_data() does not produce duplicate slots if the same date+time appears in multiple days."""
    scraper = EastAustinComedyScraper(_club())

    # Return the same date+time from two different weekday calls
    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _availability_response("8:00 PM", date="2026-04-04")

    monkeypatch.setattr(EastAustinComedyScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_SCRAPING_URL)

    assert isinstance(result, EastAustinComedyPageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_empty(monkeypatch):
    """get_data() returns None when all weekday endpoints return empty availability."""
    scraper = EastAustinComedyScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"availability": {}}

    monkeypatch.setattr(EastAustinComedyScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_SCRAPING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fetch_returns_none(monkeypatch):
    """get_data() returns None when fetch_json returns None for all days."""
    scraper = EastAustinComedyScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(EastAustinComedyScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_SCRAPING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# EastAustinComedyEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(date: str = "2026-04-04", time: str = "8:00 PM") -> EastAustinComedyEvent:
    return EastAustinComedyEvent(date=date, time=time)


def test_to_show_returns_show_with_correct_name():
    event = _make_event()
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Live Stand-Up Comedy"


def test_to_show_returns_show_with_correct_date():
    event = _make_event(date="2026-04-04", time="8:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 4
    assert show.date.hour == 20  # 8 PM CDT


def test_to_show_has_empty_lineup():
    """East Austin Comedy does not publish comedian lineups."""
    event = _make_event()
    show = event.to_show(_club())

    assert show is not None
    assert show.lineup == []


def test_to_show_creates_ticket_with_homepage_url():
    """Ticket URL points to the homepage since booking is via embedded Square modal."""
    event = _make_event()
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://eastaustincomedy.com/#shows"


def test_to_show_handles_evening_show_time():
    event = _make_event(date="2026-04-03", time="10:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 22  # 10 PM


def test_to_show_handles_early_evening_show_time():
    event = _make_event(date="2026-04-04", time="6:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 18  # 6 PM


def test_to_show_returns_none_on_invalid_time():
    event = _make_event(time="not-a-time")
    show = event.to_show(_club())

    assert show is None


def test_to_show_returns_none_on_invalid_date():
    event = _make_event(date="not-a-date")
    show = event.to_show(_club())

    assert show is None
