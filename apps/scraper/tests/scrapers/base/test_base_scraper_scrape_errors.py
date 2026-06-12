"""TASK-2833: per-target processing crashes must surface to ClubScrapingResult.error.

The base pipeline catches and logs per-target get_data/transform exceptions
without re-raising, so scrape() used to return cleanly even when every target
crashed — the club persisted success=true / error_message=null and the in-run
outcome classified like a clean empty calendar (TASK-2824's ImprovCity
incident: SimpleTixScraper crashed nightly with "Data processing error:
'list' object has no attribute 'get'" yet scraper_run_clubs recorded
success=true, errors_count=2, num_shows=0).

These tests pin the fix: a zero-show scrape that recorded at least one
fetch/transform exception surfaces the exception text on result.error, which
flips success to false (the scraper_run_clubs writer derives both columns
from result.error) and classifies the run-end outcome DEGRADED via the
orchestrator's metrics.error tick.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.core.models.domain_metrics import DomainRequestMetrics, ScrapeOutcome
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.scraping import _copy_diagnostics_into_metrics
from laughtrack.scrapers.base.base_scraper import (
    BaseScraper,
    _format_zero_show_scrape_error,
)


def _make_club() -> Club:
    _c = Club(id=786, name='ImprovCity', address='', website='https://example.com', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://example.com/events', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _disable_retries(scraper: BaseScraper) -> None:
    """Single attempt, no sleep — keeps the crash tests fast."""
    scraper.error_handler.retry_config.max_attempts = 1


def _metrics_from_result(result: ClubScrapingResult) -> DomainRequestMetrics:
    """Build the per-club metric the orchestrator's scrape_one produces so the
    test pins the outcome classification the in-run alert path will see.

    The per-stage field copies go through the real
    _copy_diagnostics_into_metrics; only the ok/none_resp/error tick is
    replicated here because it is inline in scrape_one rather than a callable
    helper. Keep this block in sync with scrape_one if its condition changes."""
    m = DomainRequestMetrics(club_name=result.club_name, club_id=result.club_id)
    m.total += 1
    if result.error:
        m.error += 1
    elif result.num_shows == 0:
        m.none_resp += 1
    else:
        m.ok += 1
    _copy_diagnostics_into_metrics(result, m)
    return m


class _GetDataCrashScraper(BaseScraper):
    """Replays the TASK-2824 shape: get_data raises after a clean fetch."""

    key = "crash_get_data"

    async def collect_scraping_targets(self):
        return ["https://example.com/a"]

    async def get_data(self, target):
        raise AttributeError("'list' object has no attribute 'get'")

    def transform_data(self, raw_data, target):
        return []


class _TransformCrashScraper(BaseScraper):
    """get_data returns a container; transform_data crashes. Pre-fix this was
    the EMPTY_CALENDAR misclassification path: fetches_ok ticked, nothing
    recorded the transform exception."""

    key = "crash_transform"

    async def collect_scraping_targets(self):
        return ["https://example.com/a"]

    async def get_data(self, target):
        return SimpleNamespace(event_list=[])

    def transform_data(self, raw_data, target):
        raise AttributeError("'list' object has no attribute 'get'")


class _PartialSuccessScraper(BaseScraper):
    """Two targets: one crashes in get_data, the other yields a show."""

    key = "partial"

    async def collect_scraping_targets(self):
        return ["https://example.com/bad", "https://example.com/good"]

    async def get_data(self, target):
        if target.endswith("/bad"):
            raise ValueError("boom")
        return SimpleNamespace(event_list=[{"e": 1}])

    def transform_data(self, raw_data, target):
        return [
            Show(
                name="Open Mic",
                club_id=786,
                date=datetime.now() + timedelta(days=7),
                show_page_url="https://example.com/good",
            )
        ]


class _CleanEmptyScraper(BaseScraper):
    """get_data returns None without raising — a legitimately empty page."""

    key = "clean_empty"

    async def collect_scraping_targets(self):
        return ["https://example.com/a"]

    async def get_data(self, target):
        return None

    def transform_data(self, raw_data, target):
        return []


class TestGetDataCrash:
    def test_error_carries_exception_text_and_flips_success(self):
        """Criterion 9129: a club whose get_data raises records
        success=false with the exception text on result.error (the
        scraper_run_clubs writer persists both straight from these)."""
        scraper = _GetDataCrashScraper(club=_make_club())
        _disable_retries(scraper)

        result = scraper.scrape_with_result()

        assert result.error is not None
        assert "'list' object has no attribute 'get'" in result.error
        assert result.success is False
        assert result.num_shows == 0

    def test_outcome_classifies_degraded(self):
        """Criterion 9129: the run-end outcome the alert path sees is
        DEGRADED, not EMPTY_CALENDAR."""
        scraper = _GetDataCrashScraper(club=_make_club())
        _disable_retries(scraper)

        result = scraper.scrape_with_result()
        metrics = _metrics_from_result(result)

        assert metrics.error == 1
        assert metrics.outcome == ScrapeOutcome.DEGRADED


class TestTransformCrash:
    def test_error_carries_exception_text_and_flips_success(self):
        scraper = _TransformCrashScraper(club=_make_club())
        _disable_retries(scraper)

        result = scraper.scrape_with_result()

        assert result.error is not None
        assert "transform failed" in result.error
        assert "'list' object has no attribute 'get'" in result.error
        assert result.success is False

    def test_outcome_classifies_degraded_not_empty_calendar(self):
        """Pre-fix this exact shape (fetch ok, transform crash, zero shows)
        fell through to EMPTY_CALENDAR and was filtered out of the
        below-threshold alert."""
        scraper = _TransformCrashScraper(club=_make_club())
        _disable_retries(scraper)

        result = scraper.scrape_with_result()
        metrics = _metrics_from_result(result)

        assert metrics.fetches_ok == 1
        assert metrics.outcome == ScrapeOutcome.DEGRADED


class TestZeroShowGate:
    def test_partial_success_keeps_club_healthy(self):
        """A scrape that produced shows stays success=true even when one
        target crashed — flipping it would fire the below-threshold alert on
        every transiently flaky detail page."""
        scraper = _PartialSuccessScraper(club=_make_club())
        _disable_retries(scraper)

        result = scraper.scrape_with_result()

        assert result.num_shows == 1
        assert result.error is None
        assert result.success is True
        assert _metrics_from_result(result).outcome == ScrapeOutcome.HEALTHY

    def test_clean_empty_scrape_still_classifies_empty_calendar(self):
        """No exception recorded → zero shows keeps the legitimate
        EMPTY_CALENDAR classification (and stays out of the alert)."""
        scraper = _CleanEmptyScraper(club=_make_club())
        _disable_retries(scraper)

        result = scraper.scrape_with_result()

        assert result.error is None
        assert result.success is True
        assert _metrics_from_result(result).outcome == ScrapeOutcome.EMPTY_CALENDAR


class TestFormatZeroShowScrapeError:
    def test_none_when_shows_were_produced(self):
        assert _format_zero_show_scrape_error(3, ["fetch failed for x: boom"]) is None

    def test_none_when_no_errors_recorded(self):
        assert _format_zero_show_scrape_error(0, []) is None

    def test_joins_distinct_messages(self):
        msg = _format_zero_show_scrape_error(0, ["a: boom", "b: bang"])
        assert msg == "a: boom; b: bang"

    def test_dedupes_and_caps_with_overflow_suffix(self):
        errors = [f"target {i}: boom" for i in range(5)] + ["target 0: boom"]
        msg = _format_zero_show_scrape_error(0, errors)
        assert msg == "target 0: boom; target 1: boom; target 2: boom (+2 more)"
