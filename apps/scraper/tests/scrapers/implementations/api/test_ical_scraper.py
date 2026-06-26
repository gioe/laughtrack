"""Tests for the generic ical (iCalendar / Google Calendar) scraper."""

from datetime import datetime, timezone
from pathlib import Path

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ical.data import IcalPageData
from laughtrack.scrapers.implementations.api.ical.extractor import IcalExtractor
from laughtrack.scrapers.implementations.api.ical.scraper import IcalScraper

_FIXTURE = Path(__file__).parent / "fixtures" / "ical_hotjava.ics"
_SOURCE_URL = "https://calendar.google.com/calendar/ical/hotjavaevents%40gmail.com/public/basic.ics"
_EVENT_PAGE = "https://hotjava.bar/events/"
_COMEDY_PATTERNS = ["comedy", "open mic", "stand-?up"]


def _ics() -> str:
    return _FIXTURE.read_text()


def _club(metadata: dict | None = None, timezone_name: str = "America/Chicago") -> Club:
    club = Club(
        id=11259,
        name="Hot Java Bar",
        address="4193 Manchester Ave",
        website="https://hotjava.bar/",
        popularity=0,
        zip_code="63110",
        phone_number="",
        visible=True,
        timezone=timezone_name,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="ical",
        scraper_key="ical",
        source_url=_SOURCE_URL,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_registry_resolves_ical_key():
    assert ScraperResolver().get("ical") is IcalScraper


def test_extractor_parses_and_skips_cancelled():
    """All non-cancelled VEVENTs parse; tz forms resolve correctly."""
    events = IcalExtractor.extract_events(_ics(), "America/Chicago", _EVENT_PAGE)
    titles = sorted(e.summary for e in events)
    # 6 VEVENTs minus the CANCELLED one = 5.
    assert len(events) == 5
    assert "Dark Ass Humor Comedy Show (Doors 8pm)" not in titles


def test_extractor_drop_before_skips_past():
    """drop_before skips events starting before the cutoff (deterministic)."""
    cutoff = datetime(2026, 7, 15, tzinfo=timezone.utc)
    events = IcalExtractor.extract_events(_ics(), "America/Chicago", _EVENT_PAGE, drop_before=cutoff)
    titles = sorted(e.summary for e in events)
    # Only the Aug 15 festival and the Jul 18 meeting start on/after the cutoff.
    assert titles == ["Amanda Jackson and Hot Java Events", "Comedy Festival All-Day Pass"]


def test_extractor_rejects_non_http_url():
    """A non-http URL field (e.g. messages://) falls back to the page URL."""
    ics = (
        "BEGIN:VCALENDAR\nBEGIN:VEVENT\n"
        "DTSTART:20260710T010000Z\nUID:x@google.com\n"
        "SUMMARY:Comedy Night\nURL:messages://open?message-guid=ABC\n"
        "END:VEVENT\nEND:VCALENDAR\n"
    )
    events = IcalExtractor.extract_events(ics, "America/Chicago", _EVENT_PAGE)
    assert len(events) == 1
    assert events[0].show_page_url == _EVENT_PAGE


def test_extractor_resolves_timezone_forms():
    """UTC, TZID, and date-only DTSTART values all resolve to aware datetimes."""
    by_title = {e.summary: e for e in IcalExtractor.extract_events(_ics(), "America/Chicago", _EVENT_PAGE)}
    # UTC 'Z' stamp -> aware UTC.
    wordup = by_title["WordUp! Open Mic (8pm-12am)"]
    assert wordup.start == datetime(2026, 7, 3, 1, 0, tzinfo=timezone.utc)
    # TZID America/Chicago 8pm CDT -> 01:00Z next day.
    dark = by_title["Morgan Casey presents Dark Comedy"]
    assert dark.start.astimezone(timezone.utc) == datetime(2026, 7, 11, 1, 0, tzinfo=timezone.utc)
    # date-only event is aware (localized to club tz midnight).
    fest = by_title["Comedy Festival All-Day Pass"]
    assert fest.start.tzinfo is not None


async def test_comedy_include_filter(monkeypatch):
    """include_title_patterns keeps only comedy-titled events."""
    scraper = IcalScraper(_club(metadata={
        "include_title_patterns": _COMEDY_PATTERNS,
        "event_page_url": _EVENT_PAGE,
        "include_past_events": True,
    }))

    async def fake_fetch_html(url):
        assert url == _SOURCE_URL
        return _ics()

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, IcalPageData)
    titles = sorted(e.summary for e in page.event_list)
    # R&B Thursday + the Calendly meeting dropped; CANCELLED dropped by parser.
    assert titles == [
        "Comedy Festival All-Day Pass",
        "Morgan Casey presents Dark Comedy",
        "WordUp! Open Mic (8pm-12am)",
    ]


async def test_no_filter_keeps_all(monkeypatch):
    """With no patterns configured, every non-cancelled event is kept."""
    scraper = IcalScraper(_club(metadata={"event_page_url": _EVENT_PAGE, "include_past_events": True}))

    async def fake_fetch_html(url):
        return _ics()

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    page = await scraper.get_data(_SOURCE_URL)
    assert isinstance(page, IcalPageData)
    assert len(page.event_list) == 5


async def test_scrape_async_produces_shows(monkeypatch):
    """End-to-end: fetch -> parse -> filter -> transformer -> Shows."""
    scraper = IcalScraper(_club(metadata={
        "include_title_patterns": _COMEDY_PATTERNS,
        "event_page_url": _EVENT_PAGE,
        "include_past_events": True,
    }))

    async def fake_fetch_html(url):
        return _ics()

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    shows = await scraper.scrape_async()
    assert len(shows) == 3
    by_name = {s.name: s for s in shows}

    # Event with its own URL keeps it.
    dark = by_name["Morgan Casey presents Dark Comedy"]
    assert dark.show_page_url == "https://hotjava.bar/events/dark-comedy"
    assert dark.date.tzinfo is not None

    # Event without a URL falls back to the configured venue events page.
    # show_page_url is trailing-slash-normalized by the enhancement pipeline;
    # the ticket purchase_url is built pre-normalization and keeps the slash.
    wordup = by_name["WordUp! Open Mic (8pm-12am)"]
    assert wordup.show_page_url == "https://hotjava.bar/events"
    assert wordup.tickets and wordup.tickets[0].purchase_url == _EVENT_PAGE


async def test_non_ics_response_returns_none(monkeypatch):
    scraper = IcalScraper(_club())

    async def fake_fetch_html(url):
        return "<html><body>not a calendar</body></html>"

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    assert await scraper.get_data(_SOURCE_URL) is None
