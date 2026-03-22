"""Tests for ScrapingResultProcessor incremental persistence."""

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


def _make_result(club_name, num_shows=2, error=None):
    shows = [MagicMock() for _ in range(num_shows)]
    return ClubScrapingResult(
        club_name=club_name, shows=shows, execution_time=1.0, error=error
    )


class TestInsertClubResult:
    def test_inserts_shows_for_club(self):
        proc = _make_processor()
        db_result = DatabaseOperationResult(inserts=3)
        proc.show_service.insert_shows.return_value = db_result

        result = _make_result("Comedy Club", num_shows=3)
        outcome = proc.insert_club_result(result)

        proc.show_service.insert_shows.assert_called_once_with(result.shows, club_name="Comedy Club")
        assert outcome.inserts == 3

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

