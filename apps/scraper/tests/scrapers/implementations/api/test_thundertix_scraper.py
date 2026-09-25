import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.thundertix import ThunderTixPerformance
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.thundertix.data import ThunderTixPageData
from laughtrack.scrapers.implementations.api.thundertix.scraper import (
    GenericThunderTixScraper,
    ThunderTixCalendarConfig,
    ThunderTixCalendarScraper,
)


@dataclass
class _PageData(EventListContainer):
    event_list: list


def _club(
    source_url: str = "https://example.thundertix.com",
    metadata: dict | None = None,
) -> Club:
    club = Club(
        id=999,
        name="ThunderTix Test Venue",
        address="123 Test St",
        website="https://example.com",
        popularity=0,
        zip_code="60657",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="thundertix",
        scraper_key="thundertix",
        source_url=source_url,
        external_id=None,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _performance_dict(
    title="Public Show",
    event_id=1,
    performance_id=101,
    publicly_available=True,
) -> dict:
    return {
        "title": title,
        "start": "2026-03-24 20:00:00 -0500",
        "event_id": event_id,
        "performance_id": performance_id,
        "time_with_timezone": "Tue - Mar 24, 2026 - 8:00pm CDT",
        "truncated_url": f"/events/{event_id}",
        "order_products_url": f"/orders/new?event_id={event_id}&performance_id={performance_id}",
        "order_tickets_url": None,
        "publicly_available": publicly_available,
        "is_sold_out": False,
    }


def _stub_detail_page_fetch(monkeypatch):
    """Bypass detail-page price fetches in tests that don't exercise pricing."""

    async def no_price(self, url: str):
        return None

    monkeypatch.setattr(ThunderTixCalendarScraper, "_fetch_detail_page_price", no_price)


# ---------------------------------------------------------------------------
# Engine-level tests (ThunderTixCalendarScraper) — exercised via a small
# anonymous subclass so the config can be hard-coded from the test fixture.
# ---------------------------------------------------------------------------


class _ConfigurableThunderTixScraper(ThunderTixCalendarScraper):
    key = "configurable_thundertix_test"
    thundertix_config = ThunderTixCalendarConfig(
        base_url="https://example.thundertix.com",
        event_factory=ThunderTixPerformance.from_api_response,
        page_data_factory=lambda events: _PageData(event_list=events),
        weeks_ahead=3,
        current_week_start_ts=lambda: 1743292800,
    )


@pytest.mark.asyncio
async def test_builds_weekly_calendar_targets_from_config():
    scraper = _ConfigurableThunderTixScraper(_club())

    urls = await scraper.collect_scraping_targets()

    assert urls == [
        "https://example.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600",
        "https://example.thundertix.com/reports/calendar?week=0&start=1743897600&end=1744502400",
        "https://example.thundertix.com/reports/calendar?week=0&start=1744502400&end=1745107200",
    ]


@pytest.mark.asyncio
async def test_engine_applies_publicly_available_and_title_skip_filters(monkeypatch):
    class _SkipPrefixScraper(ThunderTixCalendarScraper):
        key = "thundertix_skip_test"
        thundertix_config = ThunderTixCalendarConfig(
            base_url="https://example.thundertix.com",
            event_factory=ThunderTixPerformance.from_api_response,
            page_data_factory=lambda events: _PageData(event_list=events),
            title_skip_prefixes=("CLASS:", "TRAINING CENTER:"),
        )

    api_fixture = [
        _performance_dict(title="Public Show", event_id=1, performance_id=101),
        _performance_dict(title="CLASS: Intro to Improv", event_id=2, performance_id=102),
        _performance_dict(title="TRAINING CENTER: Advanced Scene Work", event_id=3, performance_id=103),
        _performance_dict(title="Private Event", event_id=4, performance_id=104, publicly_available=False),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)
    _stub_detail_page_fetch(monkeypatch)

    result = await _SkipPrefixScraper(_club()).get_data(
        "https://example.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert [event.title for event in result.event_list] == ["Public Show"]


# ---------------------------------------------------------------------------
# GenericThunderTixScraper — config built per-instance from scraping_sources.
# ---------------------------------------------------------------------------


def test_generic_scraper_builds_config_from_club_source_url_only():
    """Bare base URL in source_url is used as-is; no skip-prefixes by default."""
    scraper = GenericThunderTixScraper(_club(source_url="https://postofficecafecabaret.thundertix.com"))

    assert scraper.thundertix_config.base_url == "https://postofficecafecabaret.thundertix.com"
    assert scraper.thundertix_config.title_skip_prefixes == ()


@pytest.mark.parametrize("bad_url", ["", "   ", "https://example.com", "/reports/calendar"])
def test_generic_scraper_rejects_non_thundertix_source_url(bad_url):
    """A misconfigured source_url surfaces a clear ValueError instead of producing 12 host-less URLs."""
    with pytest.raises(ValueError, match="thundertix.com"):
        GenericThunderTixScraper(_club(source_url=bad_url))


def test_generic_scraper_strips_calendar_path_from_source_url():
    """source_url ending in /reports/calendar is normalized to the venue root."""
    scraper = GenericThunderTixScraper(_club(source_url="https://theannoyance.thundertix.com/reports/calendar"))

    assert scraper.thundertix_config.base_url == "https://theannoyance.thundertix.com"


def test_generic_scraper_parses_title_skip_prefixes_metadata():
    """metadata.title_skip_prefixes (CSV) is parsed into a tuple of trimmed strings."""
    scraper = GenericThunderTixScraper(
        _club(
            source_url="https://theannoyance.thundertix.com",
            metadata={"title_skip_prefixes": "CLASS:, TRAINING CENTER:"},
        )
    )

    assert scraper.thundertix_config.title_skip_prefixes == ("CLASS:", "TRAINING CENTER:")


@pytest.mark.asyncio
async def test_generic_scraper_collects_12_weekly_urls_from_club_base():
    scraper = GenericThunderTixScraper(_club(source_url="https://theannoyance.thundertix.com"))

    urls = await scraper.collect_scraping_targets()

    assert len(urls) == 12
    for url in urls:
        assert url.startswith("https://theannoyance.thundertix.com/reports/calendar?week=0&start=")


@pytest.mark.asyncio
async def test_generic_scraper_get_data_returns_thundertix_page_data(monkeypatch):
    """get_data() returns a ThunderTixPageData with publicly_available + skip-prefix filtering applied."""
    scraper = GenericThunderTixScraper(
        _club(
            source_url="https://theannoyance.thundertix.com",
            metadata={"title_skip_prefixes": "CLASS:,TRAINING CENTER:"},
        )
    )

    api_fixture = [
        _performance_dict(title="Public Show", event_id=1, performance_id=101),
        _performance_dict(title="CLASS: Intro to Improv", event_id=2, performance_id=102),
        _performance_dict(title="Private Event", event_id=4, performance_id=104, publicly_available=False),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)
    _stub_detail_page_fetch(monkeypatch)

    result = await scraper.get_data(
        "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert isinstance(result, ThunderTixPageData)
    assert [event.title for event in result.event_list] == ["Public Show"]
    only_event = result.event_list[0]
    assert only_event.ticket_url == ("https://theannoyance.thundertix.com/orders/new?event_id=1&performance_id=101")


@pytest.mark.asyncio
async def test_generic_scraper_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when the API returns an empty array."""
    scraper = GenericThunderTixScraper(_club(source_url="https://theannoyance.thundertix.com"))

    async def fake_fetch_json_list(self, url: str):
        return []

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    result = await scraper.get_data(
        "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert result is None


# ---------------------------------------------------------------------------
# Detail-page JSON-LD price extraction — the calendar API has no price field;
# each event detail page embeds a schema.org AggregateOffer with lowPrice.
# ---------------------------------------------------------------------------


def _detail_page_html(low_price: str = "10.0") -> str:
    """Trimmed copy of a live ThunderTix event page JSON-LD block."""
    return (
        '<html><head><script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Event","name":"Jury Duty",'
        '"offers":{"@type":"AggregateOffer",'
        '"url":"https://theannoyance.thundertix.com/events/1",'
        '"priceCurrency":"USD","lowPrice":"' + low_price + '",'
        '"highPrice":"' + low_price + '",'
        '"availability":"https://schema.org/InStock"}}'
        "</script></head><body></body></html>"
    )


def _scraper_with_detail_pages(monkeypatch, html_by_url: dict, fetched: list):
    """Build a GenericThunderTixScraper whose detail-page fetches are stubbed."""
    scraper = GenericThunderTixScraper(_club(source_url="https://theannoyance.thundertix.com"))

    async def fake_fetch_html(self, url: str, **kwargs):
        fetched.append(url)
        result = html_by_url[url]
        if isinstance(result, Exception):
            raise result
        return result

    async def no_rate_limit(url):
        return None

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_html", fake_fetch_html)
    scraper.rate_limiter = SimpleNamespace(await_if_needed=no_rate_limit)
    return scraper


@pytest.mark.asyncio
async def test_get_data_attaches_jsonld_price_one_fetch_per_distinct_event(monkeypatch):
    """Performances carry the detail-page lowPrice; performances of one event share one fetch."""
    api_fixture = [
        _performance_dict(title="Early Show", event_id=1, performance_id=101),
        _performance_dict(title="Late Show", event_id=1, performance_id=102),
        _performance_dict(title="Other Show", event_id=2, performance_id=201),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    fetched = []
    scraper = _scraper_with_detail_pages(
        monkeypatch,
        {
            "https://theannoyance.thundertix.com/events/1": _detail_page_html("15.0"),
            "https://theannoyance.thundertix.com/events/2": _detail_page_html("40.0"),
        },
        fetched,
    )

    result = await scraper.get_data(
        "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert [event.price for event in result.event_list] == [15.0, 15.0, 40.0]
    assert sorted(fetched) == [
        "https://theannoyance.thundertix.com/events/1",
        "https://theannoyance.thundertix.com/events/2",
    ]


@pytest.mark.asyncio
async def test_detail_page_fetches_are_memoized_across_calendar_windows(monkeypatch):
    """The same event recurring in a later weekly window does not refetch its detail page."""
    api_fixture = [_performance_dict(title="Recurring Show", event_id=1, performance_id=101)]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    fetched = []
    scraper = _scraper_with_detail_pages(
        monkeypatch,
        {"https://theannoyance.thundertix.com/events/1": _detail_page_html("15.0")},
        fetched,
    )

    first = await scraper.get_data("https://theannoyance.thundertix.com/reports/calendar?week=0&start=1&end=2")
    second = await scraper.get_data("https://theannoyance.thundertix.com/reports/calendar?week=0&start=2&end=3")

    assert first.event_list[0].price == 15.0
    assert second.event_list[0].price == 15.0
    assert fetched == ["https://theannoyance.thundertix.com/events/1"]


@pytest.mark.asyncio
async def test_detail_page_fetch_failure_leaves_price_none(monkeypatch):
    """A failed detail-page fetch degrades to price-unknown instead of dropping the window."""
    api_fixture = [_performance_dict(title="Public Show", event_id=1, performance_id=101)]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    fetched = []
    scraper = _scraper_with_detail_pages(
        monkeypatch,
        {"https://theannoyance.thundertix.com/events/1": Exception("Connection refused")},
        fetched,
    )

    result = await scraper.get_data("https://theannoyance.thundertix.com/reports/calendar?week=0&start=1&end=2")

    assert [event.title for event in result.event_list] == ["Public Show"]
    assert result.event_list[0].price is None
    # Failed optional enrichment remains memoized for this run.
    await scraper.get_data("https://theannoyance.thundertix.com/reports/calendar?week=0&start=2&end=3")
    assert len(fetched) == 1


@pytest.mark.asyncio
async def test_detail_page_fetch_skips_venue_root_when_truncated_url_empty(monkeypatch):
    """An empty truncated_url leaves show_page_url == base_url; the venue root is never fetched."""
    rootless = _performance_dict(title="No Detail Page", event_id=1, performance_id=101)
    rootless["truncated_url"] = ""
    api_fixture = [rootless]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    fetched = []
    scraper = _scraper_with_detail_pages(monkeypatch, {}, fetched)

    result = await scraper.get_data("https://theannoyance.thundertix.com/reports/calendar?week=0&start=1&end=2")

    assert fetched == []
    assert result.event_list[0].price is None


def test_to_show_carries_price_into_fallback_ticket():
    """ThunderTixPerformance.price flows into the show's fallback ticket."""
    performance = ThunderTixPerformance.from_api_response(_performance_dict(), "https://theannoyance.thundertix.com")
    performance.price = 15.0

    show = performance.to_show(_club())

    assert show.tickets[0].price == 15.0


def test_to_show_defaults_to_price_unknown():
    """Without a detail-page price the fallback ticket stays price-unknown (None, not 0)."""
    performance = ThunderTixPerformance.from_api_response(_performance_dict(), "https://theannoyance.thundertix.com")

    show = performance.to_show(_club())

    assert show.tickets[0].price is None


def _utc_instant(dt: datetime) -> datetime:
    """Normalize a Show.date to a UTC instant regardless of tzinfo presence.

    The Show factory may store the date as UTC-naive; an aware datetime keeps
    its offset. Either way the underlying instant is what we assert on.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@pytest.mark.parametrize(
    "start_value, expected_utc",
    [
        # Primary space-separated format (ThunderTix default serialization).
        (
            "2026-03-24 20:00:00 -0500",
            datetime(2026, 3, 25, 1, 0, 0, tzinfo=timezone.utc),
        ),
        # ISO-8601 with milliseconds (returned under Accept: application/json).
        (
            "2026-06-10T21:30:00.000-05:00",
            datetime(2026, 6, 11, 2, 30, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_to_show_parses_both_start_datetime_formats(start_value, expected_utc):
    """to_show resolves both the space-separated and ISO-8601 start formats
    to the same correct aware instant (TASK-2849)."""
    data = _performance_dict()
    data.pop("time_with_timezone")  # Exercise fallback when no displayed time exists.
    data["start"] = start_value
    performance = ThunderTixPerformance.from_api_response(data, "https://theannoyance.thundertix.com")

    show = performance.to_show(_club())

    assert show is not None
    assert _utc_instant(show.date) == expected_utc


def test_to_show_warns_only_on_non_primary_datetime_format(caplog):
    """The dateutil fallback fires a Logger.warn for a serialization flip, but
    the primary strptime path stays silent (criteria 9161/9162)."""
    iso_data = _performance_dict()
    iso_data.pop("time_with_timezone")
    iso_data["start"] = "2026-06-10T21:30:00.000-05:00"
    iso_perf = ThunderTixPerformance.from_api_response(iso_data, "https://theannoyance.thundertix.com")

    with caplog.at_level(logging.WARNING):
        assert iso_perf.to_show(_club()) is not None

    fallback_warns = [
        r for r in caplog.records if "dateutil fallback" in r.getMessage() and "ThunderTixPerformance" in r.getMessage()
    ]
    assert fallback_warns, "expected a warn when the ISO-8601 fallback path fires"

    # The primary space-separated format must NOT trigger the fallback warn.
    caplog.clear()
    primary_perf = ThunderTixPerformance.from_api_response(_performance_dict(), "https://theannoyance.thundertix.com")
    with caplog.at_level(logging.WARNING):
        assert primary_perf.to_show(_club()) is not None
    assert not any(
        "dateutil fallback" in r.getMessage() for r in caplog.records
    ), "primary strptime format should not log a fallback warn"


@pytest.mark.asyncio
async def test_generic_scraper_get_data_raises_when_fetch_fails(monkeypatch):
    """A failed calendar must not appear healthy to stale-show reconciliation."""
    scraper = GenericThunderTixScraper(_club(source_url="https://theannoyance.thundertix.com"))

    async def fake_fetch_json_list(self, url: str):
        raise Exception("Connection refused")

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    from laughtrack.foundation.exceptions.scraping_errors import DataError

    with pytest.raises(DataError):
        await scraper.get_data("https://theannoyance.thundertix.com/reports/calendar")


@pytest.mark.asyncio
async def test_scrape_runtime_regression(monkeypatch):
    """Stalled optional prices preserve all weekly performances and drain tasks."""
    import asyncio

    scraper = GenericThunderTixScraper(_club())
    scraper._PRICE_BUDGET_SECONDS = 0.05
    scraper._PRICE_URL_TIMEOUT_SECONDS = 1
    calls, cancelled = [], []

    async def calendar(url):
        return [_performance_dict(event_id=1), _performance_dict(event_id=2)]

    async def detail(url, **kwargs):
        calls.append(url)
        assert kwargs == {"skip_js_fallback": True}
        if url.endswith("/1"):
            return _detail_page_html("15.0")
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(url)

    async def unlimited(url):
        pass

    scraper.fetch_json_list = calendar
    scraper.fetch_html = detail
    scraper.rate_limiter = SimpleNamespace(await_if_needed=unlimited)
    targets = await scraper.collect_scraping_targets()
    results = await asyncio.wait_for(asyncio.gather(*(scraper.get_data(url) for url in targets)), 0.5)
    assert len(results) == 12
    assert all([p.price for p in result.event_list] == [15.0, None] for result in results)
    assert len(calls) == 2
    assert len(cancelled) == 1
    assert all(task.done() for task in scraper._run_price_tasks.values())
    await scraper.get_data(targets[0])
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, RuntimeError("calendar unavailable")])
async def test_calendar_failure_is_nonretryable(monkeypatch, response):
    from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity

    scraper = GenericThunderTixScraper(_club())

    async def calendar(url):
        if isinstance(response, Exception):
            raise response
        return response

    scraper.fetch_json_list = calendar
    with pytest.raises(DataError) as error:
        await scraper.get_data("calendar")
    assert error.value.severity == ErrorSeverity.HIGH


@pytest.mark.asyncio
async def test_price_concurrency_timeout_includes_limiter_and_drains(monkeypatch):
    import asyncio

    scraper = GenericThunderTixScraper(_club())
    scraper._PRICE_URL_TIMEOUT_SECONDS = 0.03
    scraper._PRICE_CONCURRENCY = 2
    active = peak = cancelled = 0

    async def calendar(url):
        return [_performance_dict(event_id=i) for i in range(10)]

    async def limiter(url):
        nonlocal active, peak, cancelled
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.Event().wait()
        finally:
            active -= 1
            cancelled += 1

    async def unexpected_fetch(*args, **kwargs):
        pytest.fail("rate limiter never released a detail request")

    scraper.fetch_json_list = calendar
    scraper.fetch_html = unexpected_fetch
    scraper.rate_limiter = SimpleNamespace(await_if_needed=limiter)
    result = await asyncio.wait_for(scraper.get_data("calendar"), 0.5)
    assert len(result.event_list) == 10
    assert all(p.price is None for p in result.event_list)
    assert peak == 2
    assert active == 0
    assert cancelled == 10


@pytest.mark.asyncio
async def test_run_deadline_includes_base_calendar_rate_limit():
    import asyncio
    from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity

    scraper = GenericThunderTixScraper(_club())
    scraper._RUN_BUDGET_SECONDS = 0.03
    cancelled = []

    async def limiter(url):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(url)

    scraper.rate_limiter = SimpleNamespace(await_if_needed=limiter)
    targets = await scraper.collect_scraping_targets()
    with pytest.raises(DataError) as error:
        await asyncio.wait_for(scraper._fetch_all_raw_data(targets), 0.5)
    assert error.value.severity == ErrorSeverity.HIGH
    assert len(cancelled) == 12


@pytest.mark.asyncio
async def test_calendar_timeout_cancels_fetch_and_is_not_empty():
    import asyncio
    from laughtrack.foundation.exceptions.scraping_errors import DataError

    scraper = GenericThunderTixScraper(_club())
    scraper._CALENDAR_TIMEOUT_SECONDS = 0.03
    cancelled = []

    async def calendar(url):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(url)

    scraper.fetch_json_list = calendar
    with pytest.raises(DataError):
        await asyncio.wait_for(scraper.get_data("calendar"), 0.5)
    assert cancelled == ["calendar"]


@pytest.mark.asyncio
async def test_failure_cache_resets_for_new_run(monkeypatch):
    fetched = []
    scraper = _scraper_with_detail_pages(
        monkeypatch, {"https://theannoyance.thundertix.com/events/1": RuntimeError("blocked")}, fetched
    )

    async def calendar(url):
        return [_performance_dict()]

    scraper.fetch_json_list = calendar
    for _ in range(2):
        targets = await scraper.collect_scraping_targets()
        for url in targets:
            result = await scraper.get_data(url)
            assert result.event_list[0].price is None
    assert len(fetched) == 2


@pytest.mark.asyncio
async def test_queued_prices_have_request_budget_after_acquiring_slot():
    import asyncio

    scraper = GenericThunderTixScraper(_club())
    scraper._PRICE_CONCURRENCY = 1
    scraper._PRICE_URL_TIMEOUT_SECONDS = 0.04
    scraper._PRICE_BUDGET_SECONDS = 0.5

    async def calendar(url):
        return [_performance_dict(event_id=i) for i in range(5)]

    async def detail(url):
        await asyncio.sleep(0.02)
        return 15.0

    scraper.fetch_json_list = calendar
    scraper._fetch_detail_page_price = detail
    result = await scraper.get_data("calendar")
    assert [p.price for p in result.event_list] == [15.0] * 5


@pytest.mark.asyncio
async def test_invalid_performance_time_marks_calendar_failed(monkeypatch):
    from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity

    scraper = GenericThunderTixScraper(_club())

    async def calendar(url):
        return [_performance_dict()]

    def invalid(self, club):
        raise ValueError("invalid displayed timezone")

    scraper.fetch_json_list = calendar
    monkeypatch.setattr(ThunderTixPerformance, "resolve_start_datetime", invalid, raising=False)
    with pytest.raises(DataError) as error:
        await scraper.get_data("calendar")
    assert error.value.severity == ErrorSeverity.HIGH


@pytest.mark.parametrize("weeks", [0, -1, 27, 100000, True, 1.5, "", "invalid", "18.0"])
def test_rejects_invalid_calendar_horizon(weeks):
    with pytest.raises(ValueError, match="weeks_ahead"):
        GenericThunderTixScraper(_club(metadata={"weeks_ahead": weeks}))


@pytest.mark.asyncio
@pytest.mark.parametrize("weeks", [1, "18", 26])
async def test_configured_calendar_horizon_preserves_fixed_runtime_budget(weeks):
    from urllib.parse import parse_qs, urlparse

    scraper = GenericThunderTixScraper(_club(metadata={"weeks_ahead": weeks}))
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == int(weeks)
    first = parse_qs(urlparse(targets[0]).query)
    last = parse_qs(urlparse(targets[-1]).query)
    assert int(last["end"][0]) - int(first["start"][0]) == int(weeks) * 7 * 86400
    assert scraper._RUN_BUDGET_SECONDS == 150
    assert scraper._PRICE_BUDGET_SECONDS == 60


@pytest.mark.asyncio
async def test_optional_price_diagnostics_do_not_poison_calendar(monkeypatch):
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
        current_diagnostics,
    )

    scraper = GenericThunderTixScraper(_club())
    outer = ScrapeDiagnostics()

    async def calendar(url):
        assert current_diagnostics() is outer
        current_diagnostics().record_response(200)
        return [_performance_dict()]

    async def detail(url, **kwargs):
        assert current_diagnostics() is not outer
        current_diagnostics().record_response(403)
        current_diagnostics().record_bot_block("cloudflare challenge")
        raise RuntimeError("blocked price")

    async def unlimited(url):
        pass

    scraper.fetch_json_list = calendar
    scraper.fetch_html = detail
    scraper.rate_limiter = SimpleNamespace(await_if_needed=unlimited)
    token = bind_diagnostics(outer)
    try:
        targets = await scraper.collect_scraping_targets()
        results = await scraper._fetch_all_raw_data(targets)
        assert all(result.event_list[0].price is None for result, _ in results)
        assert current_diagnostics() is outer
        assert outer.http_status == 200
        assert not outer.bot_block_detected
        assert outer.fetches_ok == 12
        assert outer.fetches_failed == 0
        assert scraper._price_blocked_count == 1
    finally:
        reset_diagnostics(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [{"title": ""}, {"start": ""}, {"start": "invalid", "time_with_timezone": None}])
async def test_invalid_required_performance_fails_entire_window(change):
    from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity

    scraper = GenericThunderTixScraper(_club())

    async def calendar(url):
        return [_performance_dict(), dict(_performance_dict(), **change)]

    scraper.fetch_json_list = calendar
    with pytest.raises(DataError) as error:
        await scraper.get_data("calendar")
    assert error.value.severity == ErrorSeverity.HIGH
