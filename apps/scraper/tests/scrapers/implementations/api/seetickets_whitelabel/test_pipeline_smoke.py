import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.data import (
    SeeTicketsWhitelabelPageData,
)
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.extractor import (
    SeeTicketsWhitelabelExtractor,
)
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.scraper import (
    SeeTicketsWhitelabelScraper,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _club(metadata=None):
    c = Club(
        id=11479,
        name="The Port Comedy Club",
        address="813 S Broadway, Baltimore, MD 21231",
        website="https://portcomedy.com/",
        popularity=0,
        zip_code="21231",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=c.id,
        platform="custom",
        scraper_key="seetickets_whitelabel",
        source_url="https://wl.eventim.us/?afflky=ThePortComedyClub",
        external_id=None,
        metadata={
            "profile_id": "15127815",
            "whitelabel_key": "ThePortComedyClub",
            **(metadata or {}),
        },
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def test_extract_events_parses_event_cards_from_recorded_fixture():
    html = (FIXTURES / "eventim_page.html").read_text()

    events = SeeTicketsWhitelabelExtractor.extract_events(html, base_url="https://wl.eventim.us")

    assert [event.name for event in events] == ["New Material Night", "Captain's Quarters"]
    assert events[0].event_id == "679796"
    assert events[0].start_date == "June 28 2026"
    assert events[0].ticket_url == "https://wl.eventim.us/event/New-Material-Night/679796?afflky=ThePortComedyClub"


def test_event_to_show_uses_date_and_ticket_url():
    html = (FIXTURES / "eventim_page.html").read_text()
    event = SeeTicketsWhitelabelExtractor.extract_events(html, base_url="https://wl.eventim.us")[0]

    event.start_datetime = "2026-06-28T20:00"
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "New Material Night"
    assert show.date.year == 2026 and show.date.month == 6 and show.date.day == 28
    assert show.date.tzinfo is not None
    assert show.tickets[0].purchase_url == event.ticket_url


@pytest.mark.asyncio
async def test_get_data_fetches_whitelabel_pages_from_browser(monkeypatch):
    scraper = SeeTicketsWhitelabelScraper(_club({"max_months": 2, "page_size": 15}))
    html = (FIXTURES / "eventim_page.html").read_text()
    calls = []

    class FakeBrowser:
        async def fetch_seetickets_whitelabel_pages(self, **kwargs):
            calls.append(kwargs)
            return [html]

        async def close(self):
            return None

    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.seetickets_whitelabel.scraper.PlaywrightBrowser",
        lambda *args, **kwargs: FakeBrowser(),
    )

    # Only network/browser boundaries are mocked; real identity/time parsing runs.
    async def _no_detail(url, **kwargs):
        return (
            '<script type="application/ld+json">'
            + json.dumps({"@type": "Event", "url": url, "startDate": "2026-06-28T20:00"})
            + "</script>"
        )

    monkeypatch.setattr(scraper, "fetch_html", _no_detail)

    result = await scraper.get_data("https://wl.eventim.us/?afflky=ThePortComedyClub")

    assert isinstance(result, SeeTicketsWhitelabelPageData)
    assert len(result.event_list) == 2
    assert calls == [
        {
            "profile_id": "15127815",
            "whitelabel_key": "ThePortComedyClub",
            "affiliate_key": "ThePortComedyClub",
            "base_url": "https://wl.eventim.us",
            "max_months": 2,
            "page_size": 15,
        }
    ]


@pytest.mark.asyncio
async def test_collect_scraping_targets_requires_profile_and_whitelabel_keys():
    assert await SeeTicketsWhitelabelScraper(_club()).collect_scraping_targets() == [
        "https://wl.eventim.us/?afflky=ThePortComedyClub"
    ]
    assert await SeeTicketsWhitelabelScraper(_club({"profile_id": ""})).collect_scraping_targets() == []


def test_parse_detail_start_datetime_reads_timed_json_ld_startdate():
    html = (FIXTURES / "event_detail.html").read_text()

    assert (
        SeeTicketsWhitelabelScraper._parse_detail_start_datetime(
            html, "https://wl.eventim.us/event/Captains-Quarters/679769"
        )
        == "2026-06-29T20:00"
    )


def test_parse_detail_start_datetime_ignores_date_only_startdate():
    html = (
        '<script type="application/ld+json">'
        '{"@type": "Event", "name": "X", "startDate": "2026-06-29", '
        '"url": "https://wl.eventim.us/event/X/1"}'
        "</script>"
    )

    assert SeeTicketsWhitelabelScraper._parse_detail_start_datetime(html, "https://wl.eventim.us/event/X/1") is None


def test_event_to_show_uses_detail_page_time_when_present():
    event = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )[0]
    event.start_datetime = "2026-06-29T20:00"

    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 20 and show.date.minute == 0
    assert show.date.tzinfo is not None


def test_event_to_show_refuses_missing_detail_time():
    event = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )[0]

    show = event.to_show(_club())

    assert show is None


@pytest.mark.asyncio
async def test_attach_detail_page_times_rejects_incomplete_calendar(monkeypatch):
    scraper = SeeTicketsWhitelabelScraper(_club())
    detail_html = (FIXTURES / "event_detail.html").read_text()
    events = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )
    # One failed detail invalidates the calendar, while verified data remains
    # available diagnostically and can never authorize an incomplete save.
    fetched = []

    async def _fetch(url, **kwargs):
        fetched.append((url, kwargs.get("skip_js_fallback")))
        if url == events[0].ticket_url:
            raise RuntimeError("blocked")
        return detail_html

    monkeypatch.setattr(scraper, "fetch_html", _fetch)

    from laughtrack.foundation.exceptions.scraping_errors import DataError

    with pytest.raises(DataError, match="verified showtime"):
        await scraper._attach_detail_page_times(events)

    assert events[0].start_datetime == ""  # failed fetch → degraded
    assert events[1].start_datetime == "2026-06-29T20:00"  # enriched
    # Convention #296: detail fetches opt out of the Playwright fallback.
    assert all(skip is True for _, skip in fetched)


@pytest.mark.asyncio
async def test_verified_showtimes_and_bounded_enrichment(monkeypatch):
    import asyncio
    from laughtrack.foundation.exceptions.scraping_errors import DataError

    scraper = SeeTicketsWhitelabelScraper(_club({"detail_timeout_seconds": 0.1, "detail_budget_seconds": 0.2}))
    events = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )
    cancelled = []

    async def rate_limit(url):
        return None

    async def fetch(url, **kwargs):
        if url == events[1].ticket_url:
            return (FIXTURES / "event_detail.html").read_text()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(url)

    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", rate_limit)
    monkeypatch.setattr(scraper, "fetch_html", fetch)
    with pytest.raises(DataError, match="verified showtime"):
        await asyncio.wait_for(scraper._attach_detail_page_times(events), timeout=0.8)
    assert cancelled == [events[0].ticket_url]
    assert events[0].to_show(_club(), enhanced=False) is None
    show = events[1].to_show(_club(), enhanced=False)
    assert show is not None
    assert (show.date.hour, show.date.minute) == (20, 0)
    assert show.date.utcoffset().total_seconds() == -4 * 3600


def test_unverified_detail_date_cannot_become_midnight():
    event = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )[0]
    assert event.to_show(_club(), enhanced=False) is None
    event.start_datetime = "2026-06-28"
    assert event.to_show(_club(), enhanced=False) is None


def _detail_blocks(*blocks):
    return '<script type="application/ld+json">' + json.dumps({"@graph": list(blocks)}) + "</script>"


def test_detail_time_matches_event_identity_not_earliest_recommendation():
    url = "https://wl.eventim.us/event/target/123?afflky=ThePortComedyClub"
    html = _detail_blocks(
        {"@type": "Event", "url": "/event/unrelated/456", "startDate": "2026-09-24T18:00"},
        {"@type": "Event", "url": "/event/target-renamed/123", "startDate": "2026-09-24T20:00-04:00"},
    )
    assert SeeTicketsWhitelabelScraper._parse_detail_start_datetime(html, url) == "2026-09-24T20:00-04:00"


@pytest.mark.parametrize("second", ["2026-09-24T19:00", "2026-09-24", "not a datetime"])
def test_conflicting_or_invalid_matching_times_fail_closed(second):
    url = "https://wl.eventim.us/event/target/123"
    html = _detail_blocks(
        {"@type": "Event", "url": url, "startDate": "2026-09-24T20:00"},
        {"@type": "Event", "url": url, "startDate": second},
    )
    assert SeeTicketsWhitelabelScraper._parse_detail_start_datetime(html, url) is None


@pytest.mark.asyncio
async def test_total_enrichment_budget_cancels_running_and_queued_work(monkeypatch):
    import asyncio
    from laughtrack.foundation.exceptions.scraping_errors import DataError

    scraper = SeeTicketsWhitelabelScraper(
        _club({"detail_concurrency": 1, "detail_timeout_seconds": 20, "detail_budget_seconds": 0.1})
    )
    events = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )
    called = []
    stopped = []

    async def fetch(url):
        called.append(url)
        try:
            await asyncio.Event().wait()
        finally:
            stopped.append(url)

    monkeypatch.setattr(scraper, "_fetch_detail_start_datetime", fetch)
    with pytest.raises(DataError, match="verified showtime"):
        await asyncio.wait_for(scraper._attach_detail_page_times(events), 0.8)
    assert called == stopped == [events[0].ticket_url]
    assert all(event.to_show(_club(), enhanced=False) is None for event in events)


@pytest.mark.asyncio
async def test_enrichment_concurrency_and_metadata_are_clamped(monkeypatch):
    import asyncio
    from laughtrack.core.entities.event.seetickets_whitelabel import SeeTicketsWhitelabelEvent

    scraper = SeeTicketsWhitelabelScraper(_club({"detail_concurrency": 10000, "detail_budget_seconds": 99999}))
    events = [
        SeeTicketsWhitelabelEvent(str(i), "Show", "September 24 2026", f"https://wl.eventim.us/event/show/{i}")
        for i in range(20)
    ]
    active = 0
    peak = 0

    async def fetch(url):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.001)
            return "2026-09-24T20:00"
        finally:
            active -= 1

    monkeypatch.setattr(scraper, "_fetch_detail_start_datetime", fetch)
    await scraper._attach_detail_page_times(events)
    assert peak == 8 and active == 0
    assert scraper._bounded_seconds("detail_budget_seconds", 120, 120) == 120


@pytest.mark.asyncio
async def test_incomplete_showtimes_mark_target_failed(monkeypatch):
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )

    scraper = SeeTicketsWhitelabelScraper(_club())
    calls = []

    async def get_data(url):
        calls.append(url)
        events = SeeTicketsWhitelabelExtractor.extract_events(
            (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
        )
        await scraper._attach_detail_page_times(events)

    async def missing(url):
        return None

    async def no_rate_limit(url):
        return None

    monkeypatch.setattr(scraper, "get_data", get_data)
    monkeypatch.setattr(scraper, "_fetch_detail_start_datetime", missing)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", no_rate_limit)
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        result = await scraper._fetch_all_raw_data(["https://wl.eventim.us"])
    finally:
        reset_diagnostics(token)
    assert len(calls) == 1  # DataError never repeats the whole fan-out.
    assert result[0][0] is None
    assert diagnostics.fetches_failed == 1 and diagnostics.fetches_ok == 0


def test_official_calendar_reads_year_showtime_and_boiler_room():
    events = SeeTicketsWhitelabelExtractor.extract_calendar_events(
        (FIXTURES / "official_calendar.html").read_text(), base_url="https://portcomedy.com"
    )
    assert [(e.name, e.start_datetime) for e in events] == [
        ("Rosebud Baker", "2026-09-24T20:00:00"),
        ("Rosebud Baker", "2026-09-25T21:45:00"),
        ("The Boiler Room", "2026-09-30T20:00:00"),
        ("Cipha Sounds", "2027-01-21T20:00:00"),
    ]
    shows = [event.to_show(_club(), enhanced=False) for event in events]
    assert all(show is not None for show in shows)
    assert shows[0].date.utcoffset().total_seconds() == -4 * 3600
    assert shows[-1].date.utcoffset().total_seconds() == -5 * 3600


@pytest.mark.parametrize("missing", ["year", "showtime"])
def test_official_calendar_rejects_missing_year_or_showtime(missing):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup((FIXTURES / "official_calendar.html").read_text(), "html.parser")
    if missing == "year":
        soup.select_one(".seetickets-calendar-year-month-container").string = "September"
    else:
        soup.select_one("p.doortime-showtime").decompose()
    with pytest.raises(ValueError):
        SeeTicketsWhitelabelExtractor.extract_calendar_events(str(soup), base_url="https://portcomedy.com")


def test_official_calendar_rejects_conflicting_times_for_same_event():
    import copy
    from bs4 import BeautifulSoup

    soup = BeautifulSoup((FIXTURES / "official_calendar.html").read_text(), "html.parser")
    original = soup.select_one(".seetickets-calendar-event-container")
    extra = copy.copy(original)
    extra.select_one("p.doortime-showtime").string = "10:00PM"
    original.parent.append(extra)
    with pytest.raises(ValueError, match="conflicting performances"):
        SeeTicketsWhitelabelExtractor.extract_calendar_events(str(soup), base_url="https://portcomedy.com")


@pytest.mark.asyncio
async def test_official_calendar_pipeline_avoids_detail_fanout(monkeypatch):
    url = "https://portcomedy.com/calendar/"
    scraper = SeeTicketsWhitelabelScraper(_club({"calendar_url": url}))
    calls = []

    async def fetch(target, **kwargs):
        calls.append(target)
        assert target == url  # A ticket detail request would fail this test.
        return (FIXTURES / "official_calendar.html").read_text()

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    assert await scraper.collect_scraping_targets() == [url]
    data = await scraper.get_data(url)
    assert len(data.event_list) == 4
    assert calls == [url]
    assert all(event.to_show(_club(), enhanced=False) for event in data.event_list)


@pytest.mark.asyncio
async def test_legacy_listing_deadline_closes_browser_and_is_not_retryable(monkeypatch):
    import asyncio
    from laughtrack.foundation.exceptions.scraping_errors import ErrorSeverity
    from laughtrack.scrapers.implementations.api.seetickets_whitelabel.scraper import IncompleteCalendarError

    scraper = SeeTicketsWhitelabelScraper(_club())
    closed = []
    budgets = []

    class Browser:
        async def fetch_seetickets_whitelabel_pages(self, **kwargs):
            await asyncio.Event().wait()

        async def close(self):
            closed.append(True)

    real_wait = asyncio.wait_for

    async def accelerated_wait(awaitable, timeout):
        budgets.append(timeout)
        return await real_wait(awaitable, 0.01 if timeout == 40 else timeout)

    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.seetickets_whitelabel.scraper.PlaywrightBrowser", Browser
    )
    monkeypatch.setattr(asyncio, "wait_for", accelerated_wait)
    with pytest.raises(IncompleteCalendarError) as error:
        await scraper.get_data("https://wl.eventim.us")
    assert error.value.severity == ErrorSeverity.HIGH
    assert closed == [True]
    assert budgets == [40, 5]
