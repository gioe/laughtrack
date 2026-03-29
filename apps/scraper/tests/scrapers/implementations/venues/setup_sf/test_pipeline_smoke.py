"""
Pipeline smoke tests for SetupSFScraper and SetupSFEvent.

Exercises the CSV extraction path and the SetupSFEvent.to_show() transformation
without making real HTTP calls or hitting the Google Sheets API.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.setup_sf import SetupSFEvent
from laughtrack.scrapers.implementations.venues.setup_sf.data import SetupSFPageData
from laughtrack.scrapers.implementations.venues.setup_sf.extractor import SetupSFExtractor
from laughtrack.scrapers.implementations.venues.setup_sf.scraper import SetupSFScraper

_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTGjBPXefy3N-RiCW15l_DaDovBB8d11X9PpGMRxUt_BRYzjoBtKUTyNhIf1AzaRJFLFxF71rMOWWku"
    "/pub?gid=495747966&single=true&output=csv"
)


def _club() -> Club:
    return Club(
        id=999,
        name="The Setup SF",
        address="630 Broadway",
        website="https://setupcomedy.com",
        scraping_url=_CSV_URL,
        popularity=0,
        zip_code="94133",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _csv_rows(*rows: tuple) -> str:
    """Build a minimal CSV string from (date, time, title, venue, ticket_url) tuples."""
    header = "date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out"
    lines = [header]
    for date_str, time_str, title, venue, ticket_url in rows:
        lines.append(f"{date_str},Fri,{time_str},{title},{venue},San Francisco,{ticket_url},,")
    return "\n".join(lines)


def _future_csv() -> str:
    return _csv_rows(
        ("2099-04-03", "9:00 PM", "The Setup at The Palace Theater", "The Palace Theater",
         "https://setupcomedy.com/tickets-3/palace-theater-friday-april-3rd-9pm"),
        ("2099-04-04", "8:00 PM", "The Setup at The Lost Church", "The Lost Church",
         "https://setupcomedy.com/tickets-3/lost-church-saturday-april-4th-8pm"),
    )


def _make_event(
    date_str: str = "2099-04-03",
    time_str: str = "9:00 PM",
    title: str = "The Setup at The Palace Theater",
    venue: str = "The Palace Theater",
    ticket_url: str = "https://setupcomedy.com/tickets-3/palace-theater-friday-april-3rd-9pm",
    sold_out: bool = False,
) -> SetupSFEvent:
    return SetupSFEvent(
        date=date_str,
        time=time_str,
        title=title,
        venue=venue,
        ticket_url=ticket_url,
        sold_out=sold_out,
    )


# ---------------------------------------------------------------------------
# SetupSFExtractor tests
# ---------------------------------------------------------------------------


def test_extract_events_returns_upcoming_events():
    """extract_events() parses a CSV and returns upcoming events."""
    csv_text = _future_csv()
    events = SetupSFExtractor.extract_events(csv_text, today=date(2026, 1, 1))

    assert len(events) == 2
    titles = {e.title for e in events}
    assert "The Setup at The Palace Theater" in titles
    assert "The Setup at The Lost Church" in titles


def test_extract_events_filters_past_events():
    """extract_events() skips rows whose date is before today."""
    csv_text = _csv_rows(
        ("2020-01-01", "9:00 PM", "Old Show", "The Palace Theater",
         "https://setupcomedy.com/tickets-3/old-show"),
        ("2099-12-31", "9:00 PM", "Future Show", "The Palace Theater",
         "https://setupcomedy.com/tickets-3/future-show"),
    )
    events = SetupSFExtractor.extract_events(csv_text, today=date(2026, 1, 1))

    assert len(events) == 1
    assert events[0].title == "Future Show"


def test_extract_events_skips_rows_with_missing_fields():
    """extract_events() skips rows that have an empty title or ticket_url."""
    csv_text = (
        "date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out\n"
        "2099-04-03,Fri,9:00 PM,,The Palace Theater,San Francisco,https://setupcomedy.com/t/1,,\n"
        "2099-04-04,Fri,9:00 PM,Has Title,The Palace Theater,San Francisco,,,\n"
        "2099-04-05,Fri,9:00 PM,Good Show,The Palace Theater,San Francisco,https://setupcomedy.com/t/2,,\n"
    )
    events = SetupSFExtractor.extract_events(csv_text, today=date(2026, 1, 1))

    assert len(events) == 1
    assert events[0].title == "Good Show"


def test_extract_events_returns_empty_for_all_past():
    """extract_events() returns an empty list when all rows are in the past."""
    csv_text = _csv_rows(
        ("2020-01-01", "9:00 PM", "Old Show A", "The Palace Theater", "https://setupcomedy.com/t/1"),
        ("2021-06-15", "8:00 PM", "Old Show B", "The Lost Church", "https://setupcomedy.com/t/2"),
    )
    events = SetupSFExtractor.extract_events(csv_text, today=date.today())
    assert events == []


def test_extract_events_returns_empty_for_empty_csv():
    """extract_events() returns an empty list when the CSV has only a header."""
    csv_text = "date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out\n"
    events = SetupSFExtractor.extract_events(csv_text, today=date.today())
    assert events == []


def test_extract_events_parses_ticket_url():
    """extract_events() correctly captures the ticket_url field."""
    csv_text = _csv_rows(
        ("2099-04-03", "9:00 PM", "Comedy Night", "The Palace Theater",
         "https://setupcomedy.com/tickets-3/palace-theater-friday-april-3rd-9pm"),
    )
    events = SetupSFExtractor.extract_events(csv_text, today=date(2026, 1, 1))

    assert len(events) == 1
    assert events[0].ticket_url == "https://setupcomedy.com/tickets-3/palace-theater-friday-april-3rd-9pm"


def test_extract_events_two_concurrent_shows_different_venues():
    """extract_events() returns both shows when two events start at the same time in different venues.

    Each show has a distinct ticket_url — deduplication must not collapse them.
    """
    csv_text = _csv_rows(
        ("2099-04-04", "9:00 PM", "Show A", "The Palace Theater",
         "https://setupcomedy.com/tickets-3/palace-saturday"),
        ("2099-04-04", "9:00 PM", "Show B", "The Lost Church",
         "https://setupcomedy.com/tickets-3/lost-church-saturday"),
    )
    events = SetupSFExtractor.extract_events(csv_text, today=date(2026, 1, 1))

    assert len(events) == 2, "Both concurrent shows at different venues must be extracted"
    venues = {e.venue for e in events}
    assert "The Palace Theater" in venues
    assert "The Lost Church" in venues


# ---------------------------------------------------------------------------
# SetupSFEvent.to_show() tests
# ---------------------------------------------------------------------------


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(title="The Setup at The Palace Theater")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "The Setup at The Palace Theater"


def test_to_show_parses_date_and_time():
    """to_show() correctly parses date + time into a datetime in LA timezone."""
    # 2099-04-03 9:00 PM = April 3 2099 at 21:00 in LA
    event = _make_event(date_str="2099-04-03", time_str="9:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2099
    assert show.date.month == 4
    assert show.date.day == 3
    assert show.date.hour == 21
    assert show.date.minute == 0


def test_to_show_parses_8pm_time():
    """to_show() correctly parses the 8:00 PM time slot."""
    event = _make_event(date_str="2099-04-04", time_str="8:00 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 20


def test_to_show_uses_ticket_url_as_show_page():
    """to_show() uses the ticket_url as the show page URL."""
    url = "https://setupcomedy.com/tickets-3/palace-theater-friday-april-3rd-9pm"
    event = _make_event(ticket_url=url)
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == url
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == url


def test_to_show_uses_venue_as_room():
    """to_show() stores the CSV venue column as the room name."""
    event = _make_event(venue="The Lost Church")
    show = event.to_show(_club())

    assert show is not None
    assert show.room == "The Lost Church"


def test_to_show_returns_none_for_invalid_date():
    """to_show() returns None when the date string cannot be parsed."""
    event = _make_event(date_str="not-a-date", time_str="9:00 PM")
    show = event.to_show(_club())

    assert show is None


def test_to_show_returns_none_for_unsupported_time_format():
    """to_show() returns None when the time string matches no known format."""
    event = _make_event(date_str="2099-04-03", time_str="quarter past nine")
    show = event.to_show(_club())

    assert show is None


def test_compact_time_normalised_9pm():
    """to_show() correctly parses compact time format '9PM' (no colon, no space)."""
    event = _make_event(date_str="2099-04-03", time_str="9PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 21
    assert show.date.minute == 0


def test_compact_time_normalised_9_pm_with_space():
    """to_show() correctly parses compact time format '9 PM' (no colon)."""
    event = _make_event(date_str="2099-04-03", time_str="9 PM")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 21


def test_compact_time_normalised_24hr():
    """to_show() correctly parses 24-hour time format '21:00'."""
    event = _make_event(date_str="2099-04-03", time_str="21:00")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 21
    assert show.date.minute == 0


def test_to_show_marks_sold_out_ticket():
    """to_show() passes the sold_out flag through to the ticket."""
    event = _make_event(sold_out=True)
    show = event.to_show(_club())

    assert show is not None
    assert show.tickets[0].sold_out is True


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_csv_url():
    """collect_scraping_targets() returns the Google Sheets CSV URL from club.scraping_url."""
    scraper = SetupSFScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 1
    assert "docs.google.com/spreadsheets" in targets[0]
    assert "output=csv" in targets[0]


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_single_url():
    """collect_scraping_targets() returns exactly one URL."""
    scraper = SetupSFScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 1


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches the CSV and returns SetupSFPageData with events."""
    scraper = SetupSFScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        return _future_csv()

    monkeypatch.setattr(SetupSFScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_CSV_URL)

    assert isinstance(result, SetupSFPageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_csv(monkeypatch):
    """get_data() returns None when the CSV has no upcoming events."""
    scraper = SetupSFScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        return "date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out\n"

    monkeypatch.setattr(SetupSFScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_CSV_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_null_response(monkeypatch):
    """get_data() returns None when fetch_html returns an empty string."""
    scraper = SetupSFScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        return ""

    monkeypatch.setattr(SetupSFScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_CSV_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_client_exception(monkeypatch):
    """get_data() returns None when fetch_html raises an exception."""
    scraper = SetupSFScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(SetupSFScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(_CSV_URL)
    assert result is None


# ---------------------------------------------------------------------------
# Transformation pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """Full pipeline: get_data() + transform_data() produces Show objects."""
    scraper = SetupSFScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        return _future_csv()

    monkeypatch.setattr(SetupSFScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    page_data = await scraper.get_data(_CSV_URL)
    assert page_data is not None

    shows = scraper.transform_data(page_data, _CSV_URL)
    assert len(shows) > 0
    assert all(s.name for s in shows)


@pytest.mark.asyncio
async def test_transformation_pipeline_preserves_event_name(monkeypatch):
    """transform_data() preserves the event title as the Show name."""
    scraper = SetupSFScraper(_club())

    csv_text = _csv_rows(
        ("2099-04-03", "9:00 PM", "The Setup at The Palace Theater", "The Palace Theater",
         "https://setupcomedy.com/tickets-3/palace-theater-friday-april-3rd-9pm"),
    )

    async def fake_fetch_html(self, url: str, **kwargs):
        return csv_text

    monkeypatch.setattr(SetupSFScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    page_data = await scraper.get_data(_CSV_URL)
    shows = scraper.transform_data(page_data, _CSV_URL)

    assert len(shows) == 1
    assert shows[0].name == "The Setup at The Palace Theater"
