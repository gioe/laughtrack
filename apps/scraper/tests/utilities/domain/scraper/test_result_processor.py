"""Tests for ScrapingResultProcessor incremental persistence."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


def _make_processor():
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    with patch.object(ScrapingResultProcessor, '__init__', lambda self, *a, **kw: None):
        proc = ScrapingResultProcessor.__new__(ScrapingResultProcessor)
        proc.show_service = MagicMock()
        proc.metrics_service = MagicMock()
    return proc


def _make_result(club_name, num_shows=2, error=None, scraper_key=None):
    shows = [MagicMock() for _ in range(num_shows)]
    return ClubScrapingResult(
        club_name=club_name, shows=shows, execution_time=1.0, error=error,
        scraper_key=scraper_key,
    )


class TestInsertClubResult:
    def test_inserts_shows_for_club(self):
        proc = _make_processor()
        db_result = DatabaseOperationResult(inserts=3)
        proc.show_service.insert_shows.return_value = db_result

        result = _make_result("Comedy Club", num_shows=3)
        outcome = proc.insert_club_result(result)

        proc.show_service.insert_shows.assert_called_once_with(
            result.shows, club_name="Comedy Club", scraper_key=None,
        )
        assert outcome.inserts == 3

    def test_forwards_scraper_key_for_attribution(self):
        """scraper_key from ClubScrapingResult flows to ShowService for shows.last_scraped_by stamping (TASK-2051)."""
        proc = _make_processor()
        proc.show_service.insert_shows.return_value = DatabaseOperationResult(inserts=2)

        result = _make_result("Stress Factory", num_shows=2, scraper_key="live_nation")
        proc.insert_club_result(result)

        proc.show_service.insert_shows.assert_called_once_with(
            result.shows, club_name="Stress Factory", scraper_key="live_nation",
        )

    def test_error_entries_propagated_from_db_errors(self):
        proc = _make_processor()
        db_result = DatabaseOperationResult(
            db_errors=1,
            error_entries=[("Comedy Club", "DB error batch 1/1: connection reset")],
        )
        proc.show_service.insert_shows.return_value = db_result

        result = _make_result("Comedy Club", num_shows=5)
        outcome = proc.insert_club_result(result)

        assert outcome.db_errors == 1
        assert len(outcome.error_entries) == 1
        assert outcome.error_entries[0][0] == "Comedy Club"
        assert "DB error" in outcome.error_entries[0][1]

    def test_no_error_entries_on_success(self):
        proc = _make_processor()
        db_result = DatabaseOperationResult(inserts=2)
        proc.show_service.insert_shows.return_value = db_result

        result = _make_result("Happy Club", num_shows=2)
        outcome = proc.insert_club_result(result)

        assert outcome.error_entries == []

    def test_returns_empty_result_when_no_shows(self):
        proc = _make_processor()
        result = _make_result("Empty Club", num_shows=0)

        outcome = proc.insert_club_result(result)

        proc.show_service.insert_shows.assert_not_called()
        assert outcome.inserts == 0
        assert outcome.total == 0


class TestProcessResults:
    def test_uses_provided_db_result_for_metrics(self):
        proc = _make_processor()
        club_results = [_make_result("Club A"), _make_result("Club B")]
        provided_db_result = DatabaseOperationResult(inserts=5, updates=2)

        proc.process_results(club_results, provided_db_result)

        proc.metrics_service.end_session.assert_called_once_with(club_results, provided_db_result)

    def test_defaults_to_empty_db_result_when_none_provided(self):
        proc = _make_processor()
        club_results = [_make_result("Club A")]

        proc.process_results(club_results)

        args = proc.metrics_service.end_session.call_args[0]
        assert args[1] == DatabaseOperationResult()

    def test_does_not_call_insert_shows(self):
        """process_results must not insert any shows — that's done per-club in scrape_one()."""
        proc = _make_processor()
        club_results = [_make_result("Club A", num_shows=5)]
        db_result = DatabaseOperationResult(inserts=5)

        proc.process_results(club_results, db_result)

        proc.show_service.insert_shows.assert_not_called()


class TestIncrementalPersistenceInScrapeOne:
    """Integration-style tests verifying per-club write timing in ScrapingService."""

    def _make_service(self):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
            svc.proxy_pool = None
            svc._scraping_resolver = MagicMock()
            mock_rp = MagicMock()
            mock_rp.insert_club_result.return_value = DatabaseOperationResult(inserts=1)
            svc._result_processor = mock_rp
        return svc

    def _make_club(self, name="Club"):
        club = MagicMock()
        club.name = name
        club.scraper = "test_scraper"
        club.id = 1
        club.as_context.return_value = {}
        return club

    def test_insert_club_result_called_once_per_club(self):
        """Each club's result is persisted immediately, not batched."""
        svc = self._make_service()

        club_a_result = ClubScrapingResult(club_name="Club A", shows=[MagicMock()], execution_time=1.0)
        club_b_result = ClubScrapingResult(club_name="Club B", shows=[MagicMock()], execution_time=1.0)

        def scraper_factory(club, **kw):
            s = MagicMock()
            s.scrape_with_result.return_value = (
                club_a_result if "A" in club.name else club_b_result
            )
            return s

        svc._scraping_resolver.get.return_value = scraper_factory

        clubs = [self._make_club("Club A"), self._make_club("Club B")]
        results, _, db_result = svc._scrape_clubs_with_metrics(clubs)

        assert svc._result_processor.insert_club_result.call_count == 2
        assert db_result.inserts == 2  # 1 insert accumulated per club

    def test_db_result_accumulates_across_clubs(self):
        """DatabaseOperationResult returned by _scrape_clubs_with_metrics sums all per-club inserts."""
        svc = self._make_service()
        svc._result_processor.insert_club_result.return_value = DatabaseOperationResult(inserts=3, updates=1)

        def scraper_factory(club, **kw):
            s = MagicMock()
            s.scrape_with_result.return_value = ClubScrapingResult(
                club_name=club.name, shows=[MagicMock()], execution_time=1.0
            )
            return s

        svc._scraping_resolver.get.return_value = scraper_factory

        clubs = [self._make_club(f"Club {i}") for i in range(3)]
        _, _, db_result = svc._scrape_clubs_with_metrics(clubs)

        assert db_result.inserts == 9   # 3 clubs × 3 inserts each
        assert db_result.updates == 3   # 3 clubs × 1 update each

    def test_insert_failure_does_not_abort_other_clubs(self):
        """A DB insert failure for one club must not prevent other clubs from being scraped."""
        svc = self._make_service()

        insert_count = [0]

        def insert_side_effect(result):
            insert_count[0] += 1
            if "Bad" in result.club_name:
                raise RuntimeError("DB connection lost")
            return DatabaseOperationResult(inserts=1)

        svc._result_processor.insert_club_result.side_effect = insert_side_effect

        def scraper_factory(club, **kw):
            s = MagicMock()
            s.scrape_with_result.return_value = ClubScrapingResult(
                club_name=club.name, shows=[MagicMock()], execution_time=1.0
            )
            return s

        svc._scraping_resolver.get.return_value = scraper_factory

        clubs = [
            self._make_club("Good Club 1"),
            self._make_club("Bad Club"),
            self._make_club("Good Club 2"),
        ]
        results, summary, db_result = svc._scrape_clubs_with_metrics(clubs)

        # All 3 clubs still scraped and returned
        assert len(results) == 3
        # insert_club_result attempted for all 3 clubs
        assert insert_count[0] == 3
        # Only the 2 good clubs contributed to db_result
        assert db_result.inserts == 2

    def test_insert_club_result_not_called_when_scraper_raises(self):
        """When the scraper itself raises, insert_club_result must not be called for that club."""
        svc = self._make_service()

        def scraper_factory(club, **kw):
            s = MagicMock()
            if "Crash" in club.name:
                s.scrape_with_result.side_effect = RuntimeError("scraper crash")
            else:
                s.scrape_with_result.return_value = ClubScrapingResult(
                    club_name=club.name, shows=[MagicMock()], execution_time=1.0
                )
            return s

        svc._scraping_resolver.get.return_value = scraper_factory

        clubs = [self._make_club("Good Club"), self._make_club("Crash Club")]
        results, summary, db_result = svc._scrape_clubs_with_metrics(clubs)

        # insert called once (for the good club only)
        assert svc._result_processor.insert_club_result.call_count == 1
        assert db_result.inserts == 1


class TestStaleFutureShowReconciliation:
    """TASK-2847: a CLEAN scrape deletes future shows it stopped seeing; a
    failed/errored/bot-blocked/degraded scrape never does."""

    def _clean_result(self, **overrides):
        """A HEALTHY-by-default result (fetch reached source, no error/block)."""
        kwargs = dict(
            club_name="Commonwealth Brewing Co FFX",
            shows=[MagicMock()],
            execution_time=1.0,
            club_id=2301,
            scraper_key="eventbrite",
            fetches_ok=1,
            fetches_failed=0,
            items_before_filter=1,
            error=None,
            bot_block_detected=False,
        )
        kwargs.update(overrides)
        return ClubScrapingResult(**kwargs)

    def _proc(self, stale_count=1):
        """Processor whose count_stale_future_shows returns a concrete int so the
        cap logic runs (a bare MagicMock would break the numeric comparison)."""
        proc = _make_processor()
        proc.show_service.insert_shows.return_value = DatabaseOperationResult(inserts=1)
        proc.show_service.count_stale_future_shows.return_value = stale_count
        proc.show_service.delete_stale_future_shows.return_value = [
            {"id": 1532633, "name": "Cancelled Show", "date": "2026-07-24", "room": ""}
        ]
        return proc

    def test_reconciles_on_clean_healthy_scrape(self):
        proc = self._proc(stale_count=1)

        proc.insert_club_result(self._clean_result())

        proc.show_service.delete_stale_future_shows.assert_called_once()
        args = proc.show_service.delete_stale_future_shows.call_args[0]
        assert args[0] == 2301
        assert args[1] == "eventbrite"
        assert isinstance(args[2], datetime)
        assert args[2].tzinfo is not None  # tz-aware UTC cutoff

    def test_reconciles_on_clean_empty_calendar(self):
        """The Commonwealth case: 0 shows, but the fetch reached the source and
        found no events — the lone cancelled future show must be removed."""
        proc = self._proc(stale_count=1)

        proc.insert_club_result(self._clean_result(shows=[], items_before_filter=0))

        proc.show_service.insert_shows.assert_not_called()  # no shows to insert
        proc.show_service.delete_stale_future_shows.assert_called_once()

    def test_cap_exceeded_skips_delete(self):
        """A clean scrape that would drop more than the cap (silent-parser-break
        signature) must NOT delete — it logs for human review instead."""
        proc = self._proc(stale_count=11)  # default cap is 10

        proc.insert_club_result(self._clean_result(shows=[], items_before_filter=0))

        proc.show_service.count_stale_future_shows.assert_called_once()
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_cap_env_override_allows_larger_sweep(self, monkeypatch):
        monkeypatch.setenv("RECONCILE_DELETE_CAP", "50")
        proc = self._proc(stale_count=40)

        proc.insert_club_result(self._clean_result())

        proc.show_service.delete_stale_future_shows.assert_called_once()

    def test_zero_stale_count_skips_delete(self):
        proc = self._proc(stale_count=0)

        proc.insert_club_result(self._clean_result())

        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_when_error_present(self):
        proc = self._proc()
        proc.insert_club_result(self._clean_result(shows=[], error="boom"))
        proc.show_service.count_stale_future_shows.assert_not_called()
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_when_bot_blocked(self):
        proc = self._proc()
        proc.insert_club_result(self._clean_result(shows=[], bot_block_detected=True))
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_when_a_fetch_failed(self):
        proc = self._proc()
        proc.insert_club_result(self._clean_result(shows=[], fetches_failed=1))
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_when_no_fetch_succeeded(self):
        """fetches_ok == 0 is the DEGRADED fallback — absence is not trustworthy."""
        proc = self._proc()
        proc.insert_club_result(
            self._clean_result(shows=[], fetches_ok=0, items_before_filter=0)
        )
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_when_classifier_rejected_all(self):
        """0 shows but the parser saw candidates (items_before_filter > 0) — a
        parser bug there could wrongly delete live inventory."""
        proc = self._proc()
        proc.insert_club_result(self._clean_result(shows=[], items_before_filter=7))
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_for_synthetic_organizer_proxy(self):
        """Organizer/production-company proxy scrapes carry the proxy club_id but
        persist shows under per-venue ids — a club_id-scoped delete would
        mis-target, so reconciliation is skipped (tracked separately)."""
        proc = self._proc()
        proc.insert_club_result(self._clean_result(is_synthetic=True))
        proc.show_service.count_stale_future_shows.assert_not_called()
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_without_club_id(self):
        proc = self._proc()
        proc.insert_club_result(self._clean_result(club_id=None))
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_no_reconcile_without_scraper_key(self):
        proc = self._proc()
        proc.insert_club_result(self._clean_result(scraper_key=None))
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_cutoff_captured_before_insert_shows(self):
        """Safety-critical ordering: the reconcile cutoff must be captured BEFORE
        insert_shows stamps last_scraped_date=now(), else re-seen shows would be
        deletable. Pin the call order and that the cutoff precedes insert."""
        proc = self._proc(stale_count=1)
        call_order = []
        insert_ts = {}

        def record_insert(*a, **kw):
            call_order.append("insert")
            insert_ts["t"] = datetime.now(timezone.utc)
            return DatabaseOperationResult(inserts=1)

        def record_count(club_id, scraper_key, cutoff):
            call_order.append("count")
            # cutoff must predate the insert timestamp
            assert cutoff <= insert_ts["t"]
            return 1

        proc.show_service.insert_shows.side_effect = record_insert
        proc.show_service.count_stale_future_shows.side_effect = record_count

        proc.insert_club_result(self._clean_result())

        assert call_order == ["insert", "count"]

    def test_reconcile_failure_never_breaks_persistence(self):
        """A DB error during reconciliation is logged, not raised — the shows
        were already persisted and the run must continue."""
        proc = self._proc(stale_count=1)
        proc.show_service.delete_stale_future_shows.side_effect = RuntimeError("db down")

        outcome = proc.insert_club_result(self._clean_result())

        assert outcome.inserts == 1  # persistence result still returned

