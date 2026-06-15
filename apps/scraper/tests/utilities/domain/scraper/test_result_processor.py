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
        proc.organizer_venue_handler = MagicMock()
        # Default: no sibling source owns any venue, no prior history. Organizer
        # tests override these as needed.
        proc.organizer_venue_handler.is_venue_covered_elsewhere.return_value = False
        proc.organizer_venue_handler.get_venue_club_ids.return_value = []
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

    def _venue_show(self, club_id):
        """A show mock carrying a concrete per-venue club_id (organizer mode)."""
        show = MagicMock()
        show.club_id = club_id
        return show

    def _organizer_result(self, club_ids, **overrides):
        """A clean synthetic organizer-proxy result whose shows span the given
        per-venue club_ids (the proxy club_id is the synthetic placeholder)."""
        kwargs = dict(
            shows=[self._venue_show(cid) for cid in club_ids],
            is_synthetic=True,
            club_id=0,  # Club.SYNTHETIC_PROXY_PLACEHOLDER_ID
        )
        kwargs.update(overrides)
        return self._clean_result(**kwargs)

    def test_organizer_reconciles_each_distinct_venue_club_id(self):
        """TASK-2856: an organizer-mode proxy reconciles per distinct per-venue
        club_id present in its shows — not the proxy club_id."""
        proc = self._proc(stale_count=1)

        proc.insert_club_result(self._organizer_result([101, 101, 202]))

        deleted_club_ids = sorted(
            call.args[0]
            for call in proc.show_service.delete_stale_future_shows.call_args_list
        )
        assert deleted_club_ids == [101, 202]
        for call in proc.show_service.delete_stale_future_shows.call_args_list:
            assert call.args[1] == "eventbrite"
            assert call.args[2].tzinfo is not None  # tz-aware UTC cutoff
        # The synthetic proxy id (0) is never the delete target.
        assert 0 not in deleted_club_ids

    def test_organizer_skips_none_and_placeholder_club_ids(self):
        """Shows lacking a resolved venue club_id (None) or carrying the synthetic
        placeholder must not drive a delete."""
        proc = self._proc(stale_count=1)

        proc.insert_club_result(self._organizer_result([None, 0, 303]))

        deleted_club_ids = [
            call.args[0]
            for call in proc.show_service.delete_stale_future_shows.call_args_list
        ]
        assert deleted_club_ids == [303]

    def test_organizer_applies_cap_per_venue(self):
        """The RECONCILE_DELETE_CAP is enforced per venue — a single venue over
        the cap is skipped without affecting the others' reconciliation."""
        proc = self._proc()

        # Venue 101 is over the cap (11 > 10), venue 202 is within it (1).
        def count_by_venue(club_id, scraper_key, cutoff):
            return 11 if club_id == 101 else 1

        proc.show_service.count_stale_future_shows.side_effect = count_by_venue

        proc.insert_club_result(self._organizer_result([101, 202]))

        deleted_club_ids = [
            call.args[0]
            for call in proc.show_service.delete_stale_future_shows.call_args_list
        ]
        assert deleted_club_ids == [202]  # 101 skipped by the cap, 202 deleted

    def test_organizer_still_gated_on_clean_scrape(self):
        """A degraded organizer scrape (bot-blocked) reconciles no venue."""
        proc = self._proc()
        proc.insert_club_result(
            self._organizer_result([101, 202], bot_block_detected=True)
        )
        proc.show_service.count_stale_future_shows.assert_not_called()
        proc.show_service.delete_stale_future_shows.assert_not_called()

    def test_organizer_without_scraper_key_skips(self):
        """Without a scraper_key the per-venue delete cannot be scoped safely."""
        proc = self._proc()
        proc.insert_club_result(self._organizer_result([101], scraper_key=None))
        proc.show_service.delete_stale_future_shows.assert_not_called()

    # --- TASK-2859: persisted per-organizer venue history + dropped venues ---

    def test_organizer_records_current_venue_set_in_history(self):
        """A clean organizer run with a production_company_id persists this run's
        distinct venue set so a later run can diff against it."""
        proc = self._proc(stale_count=0)  # no stale shows; just exercise history
        proc.organizer_venue_handler.get_venue_club_ids.return_value = []

        proc.insert_club_result(
            self._organizer_result([101, 202], production_company_id=55)
        )

        proc.organizer_venue_handler.record_venues.assert_called_once_with(
            55, [101, 202]
        )

    def test_no_history_ops_without_production_company_id(self):
        """Without a production_company_id the run cannot key the history table, so
        no read/write/diff happens (TASK-2856 present-venue behaviour only)."""
        proc = self._proc(stale_count=1)

        proc.insert_club_result(self._organizer_result([101]))  # pc_id defaults None

        proc.organizer_venue_handler.get_venue_club_ids.assert_not_called()
        proc.organizer_venue_handler.record_venues.assert_not_called()

    def test_dropped_venue_is_reconciled_from_history(self):
        """A venue in the persisted prior set but absent from this run's shows
        dropped entirely from the feed and has its stale shows reconciled."""
        proc = self._proc(stale_count=1)
        # Prior run saw 101, 202, 303; this run only carries 101, 202.
        proc.organizer_venue_handler.get_venue_club_ids.return_value = [101, 202, 303]

        proc.insert_club_result(
            self._organizer_result([101, 202], production_company_id=55)
        )

        deleted_club_ids = sorted(
            call.args[0]
            for call in proc.show_service.delete_stale_future_shows.call_args_list
        )
        assert deleted_club_ids == [101, 202, 303]  # 303 reconciled as dropped
        # The dropped venue's stale history claim is forgotten.
        proc.organizer_venue_handler.forget_venue.assert_called_once_with(55, 303)
        # History rewritten to this run's set.
        proc.organizer_venue_handler.record_venues.assert_called_once_with(55, [101, 202])

    def test_dropped_venue_skipped_when_covered_by_sibling_source(self):
        """A dropped venue still owned by another organizer/direct source must NOT
        have its shows deleted, but its stale history claim is still forgotten."""
        proc = self._proc(stale_count=1)
        proc.organizer_venue_handler.get_venue_club_ids.return_value = [101, 303]

        def covered(pc_id, club_id):
            return club_id == 303  # 303 is owned by a sibling source

        proc.organizer_venue_handler.is_venue_covered_elsewhere.side_effect = covered

        proc.insert_club_result(
            self._organizer_result([101], production_company_id=55)
        )

        deleted_club_ids = [
            call.args[0]
            for call in proc.show_service.delete_stale_future_shows.call_args_list
        ]
        assert deleted_club_ids == [101]  # 303 NOT deleted — sibling owns it
        proc.organizer_venue_handler.forget_venue.assert_called_once_with(55, 303)

    def test_present_venue_skipped_when_covered_elsewhere(self):
        """A present venue a sibling source also maintains is not reconciled, so
        the sibling's non-overlapping inventory is never deleted (criterion 9184)."""
        proc = self._proc(stale_count=1)
        proc.organizer_venue_handler.get_venue_club_ids.return_value = []

        def covered(pc_id, club_id):
            return club_id == 202

        proc.organizer_venue_handler.is_venue_covered_elsewhere.side_effect = covered

        proc.insert_club_result(
            self._organizer_result([101, 202], production_company_id=55)
        )

        deleted_club_ids = sorted(
            call.args[0]
            for call in proc.show_service.delete_stale_future_shows.call_args_list
        )
        assert deleted_club_ids == [101]  # 202 skipped — covered elsewhere

    def test_coverage_check_failure_skips_reconcile_conservatively(self):
        """If the cross-organizer coverage lookup errors, the venue is treated as
        covered (no delete) — never delete on doubt."""
        proc = self._proc(stale_count=1)
        proc.organizer_venue_handler.get_venue_club_ids.return_value = []
        proc.organizer_venue_handler.is_venue_covered_elsewhere.side_effect = RuntimeError(
            "db down"
        )

        proc.insert_club_result(
            self._organizer_result([101], production_company_id=55)
        )

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

