"""Tests for ScrapingService per-club metrics, summary emission, and alerting."""

import threading
import time
from unittest.mock import MagicMock, patch, call
import pytest

from laughtrack.core.models.domain_metrics import DomainRequestMetrics, ScrapingRunSummary
from laughtrack.core.models.results import ClubScrapingResult


def _make_summary(ok=0, none_resp=0, error=0, club_name="Test Club"):
    s = ScrapingRunSummary()
    m = DomainRequestMetrics(club_name=club_name, total=ok + none_resp + error,
                             ok=ok, none_resp=none_resp, error=error)
    s.per_club.append(m)
    return s


class TestCheckAndAlert:
    def _make_service(self, threshold=70.0):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = threshold
        return svc

    def test_no_alert_when_all_pass(self):
        svc = self._make_service()
        summary = _make_summary(ok=1)
        with patch.object(svc, '_send_discord_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_not_called()

    def test_alert_fired_when_club_below_threshold(self):
        svc = self._make_service(threshold=70.0)
        summary = _make_summary(error=1)  # 0% success rate
        with patch.object(svc, '_send_discord_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_called_once()
            failing = mock_alert.call_args[0][0]
            assert len(failing) == 1
            assert failing[0].club_name == "Test Club"

    def test_alert_not_fired_when_exactly_at_threshold(self):
        svc = self._make_service(threshold=70.0)
        # exactly 70% success — should NOT fire (below_threshold uses strict <)
        summary = _make_summary(ok=7, error=3)
        with patch.object(svc, '_send_discord_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_not_called()


class TestSendDiscordAlertSkipsWhenNotConfigured:
    def _make_service(self):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
        return svc

    def test_skips_when_discord_not_configured(self):
        svc = self._make_service()
        failing = [DomainRequestMetrics(club_name="X", total=1, error=1)]

        mock_config = MagicMock()
        mock_config.is_discord_configured.return_value = False
        mock_config.discord_webhook_url = None

        with patch('laughtrack.core.services.scraping.MonitoringConfig', create=True), \
             patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            # Should not raise; just logs a warning
            svc._send_discord_alert(failing)  # Would fail at asyncio.run if alert was sent


class TestScrapeClubsWithMetrics:
    """Test that _scrape_clubs_with_metrics correctly classifies outcomes."""

    def _make_service(self):
        from laughtrack.core.services.scraping import ScrapingService
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
            svc.proxy_pool = None
            svc._scraping_resolver = MagicMock()
            mock_rp = MagicMock()
            mock_rp.insert_club_result.return_value = DatabaseOperationResult()
            svc._result_processor = mock_rp
        return svc

    def _make_club(self, name="Club", scraper_key="test_scraper"):
        club = MagicMock()
        club.name = name
        club.scraper = scraper_key
        club.id = 1
        club.as_context.return_value = {}
        return club

    def test_ok_when_shows_returned(self):
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        result = ClubScrapingResult(club_name="Club", shows=[MagicMock()], execution_time=1.0)
        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.return_value = result
        svc._scraping_resolver.get.return_value = lambda club, **kw: mock_scraper

        club = self._make_club()
        _, summary, _ = svc._scrape_clubs_with_metrics([club])

        assert len(summary.per_club) == 1
        m = summary.per_club[0]
        assert m.ok == 1
        assert m.none_resp == 0
        assert m.error == 0

    def test_none_resp_when_no_shows_no_error(self):
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        result = ClubScrapingResult(club_name="Club", shows=[], execution_time=1.0)
        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.return_value = result
        svc._scraping_resolver.get.return_value = lambda club, **kw: mock_scraper

        club = self._make_club()
        _, summary, _ = svc._scrape_clubs_with_metrics([club])

        m = summary.per_club[0]
        assert m.none_resp == 1
        assert m.ok == 0
        assert m.error == 0

    def test_error_when_result_has_error(self):
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        result = ClubScrapingResult(club_name="Club", shows=[], execution_time=0.0, error="boom")
        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.return_value = result
        svc._scraping_resolver.get.return_value = lambda club, **kw: mock_scraper

        club = self._make_club()
        _, summary, _ = svc._scrape_clubs_with_metrics([club])

        m = summary.per_club[0]
        assert m.error == 1
        assert m.ok == 0
        assert m.none_resp == 0

    def test_clubs_run_concurrently(self):
        """Multiple clubs should scrape in parallel, not sequentially."""
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        active_at_once = []
        lock = threading.Lock()
        active = [0]

        def slow_scrape(club):
            with lock:
                active[0] += 1
                active_at_once.append(active[0])
            time.sleep(0.05)
            with lock:
                active[0] -= 1
            return ClubScrapingResult(club_name=club.name, shows=[MagicMock()], execution_time=0.05)

        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.side_effect = lambda: slow_scrape(mock_scraper._club)
        # Use a factory that attaches the club to the scraper so slow_scrape can access it
        def scraper_factory(club, **kw):
            s = MagicMock()
            s.scrape_with_result.side_effect = lambda: slow_scrape(club)
            return s

        svc._scraping_resolver.get.return_value = scraper_factory

        clubs = [self._make_club(name=f"Club {i}") for i in range(4)]
        start = time.monotonic()
        results, summary, _ = svc._scrape_clubs_with_metrics(clubs)
        elapsed = time.monotonic() - start

        assert len(results) == 4
        # Verify at least 2 clubs overlapped — this directly proves concurrency without relying on wall-clock timing
        assert max(active_at_once) >= 2

    def test_one_club_failure_does_not_abort_others(self):
        """A failure in one club's scraper must not prevent other clubs from completing."""
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        good_result = ClubScrapingResult(club_name="Good Club", shows=[MagicMock()], execution_time=1.0)

        def scraper_factory(club, **kw):
            s = MagicMock()
            if "Bad" in club.name:
                s.scrape_with_result.side_effect = RuntimeError("network timeout")
            else:
                s.scrape_with_result.return_value = good_result
            return s

        svc._scraping_resolver.get.return_value = scraper_factory

        clubs = [
            self._make_club(name="Good Club 1"),
            self._make_club(name="Bad Club"),
            self._make_club(name="Good Club 2"),
        ]
        results, summary, _ = svc._scrape_clubs_with_metrics(clubs)

        assert len(results) == 3
        assert len(summary.per_club) == 3
        good_metrics = [m for m in summary.per_club if "Good" in m.club_name]
        bad_metrics = [m for m in summary.per_club if "Bad" in m.club_name]
        assert all(m.ok == 1 for m in good_metrics)
        assert bad_metrics[0].error == 1

    def test_skipped_clubs_emit_warning(self):
        """Clubs with no scraper key or no matching scraper class emit a summary warning."""
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        # Club with no scraper key
        no_key_club = self._make_club(name="No Key Club", scraper_key=None)
        no_key_club.scraper = None

        # Club with unresolvable scraper key
        svc._scraping_resolver.get.return_value = None
        bad_key_club = self._make_club(name="Bad Key Club", scraper_key="unknown")

        with patch('laughtrack.core.services.scraping.Logger') as mock_logger:
            results, summary, _ = svc._scrape_clubs_with_metrics([no_key_club, bad_key_club])

        assert len(results) == 0
        assert len(summary.per_club) == 0
        warn_calls = [str(c) for c in mock_logger.warn.call_args_list]
        summary_warn = [c for c in warn_calls if "skipped" in c and "club(s)" in c]
        assert len(summary_warn) == 1, f"Expected one summary warning, got: {warn_calls}"
        assert "2" in summary_warn[0]

    def test_max_concurrent_clubs_reads_env_var(self):
        """MAX_CONCURRENT_CLUBS env var controls the semaphore limit."""
        import os
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        with patch.dict(os.environ, {"MAX_CONCURRENT_CLUBS": "3"}):
            assert svc._max_concurrent_clubs == 3

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MAX_CONCURRENT_CLUBS", None)
            assert svc._max_concurrent_clubs == 5  # default
