"""Tests for ScrapingService per-club metrics, summary emission, and alerting."""

import threading
import time
from unittest.mock import MagicMock, patch, call
import pytest

from laughtrack.core.models.domain_metrics import DomainRequestMetrics, ScrapingRunSummary
from laughtrack.core.models.results import ClubScrapingResult


def _make_summary(ok=0, none_resp=0, error=0, club_name="Test Club", scraper_type=None):
    s = ScrapingRunSummary()
    m = DomainRequestMetrics(club_name=club_name, scraper_type=scraper_type,
                             total=ok + none_resp + error,
                             ok=ok, none_resp=none_resp, error=error)
    s.per_club.append(m)
    return s


def _make_mock_config(channels=None):
    """Return a MonitoringConfig mock that reports the given channels."""
    mock_config = MagicMock()
    mock_config.get_configured_channels.return_value = channels if channels is not None else ["discord"]
    mock_config.is_discord_configured.return_value = "discord" in (channels or ["discord"])
    mock_config.discord_webhook_url = "https://discord.example/webhook" if "discord" in (channels or ["discord"]) else None
    return mock_config


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
        summary = _make_summary(error=1)  # 0% success rate, no scraper_type → individual
        mock_config = _make_mock_config(channels=["discord"])
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            with patch.object(svc, '_send_discord_alert') as mock_alert:
                svc._check_and_alert(summary)
                mock_alert.assert_called_once()
                individual_arg = mock_alert.call_args[0][0]
                assert len(individual_arg) == 1
                assert individual_arg[0].club_name == "Test Club"

    def test_alert_not_fired_when_exactly_at_threshold(self):
        svc = self._make_service(threshold=70.0)
        # exactly 70% success — should NOT fire (below_threshold uses strict <)
        summary = _make_summary(ok=7, error=3)
        with patch.object(svc, '_send_discord_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_not_called()

    def _make_multi_club_summary(self, clubs):
        """Build a ScrapingRunSummary containing the given DomainRequestMetrics list."""
        s = ScrapingRunSummary()
        s.per_club.extend(clubs)
        return s

    def _make_metric(self, name, scraper_type=None, ok=0, error=1, none_resp=0):
        total = ok + error + none_resp
        return DomainRequestMetrics(
            club_name=name, scraper_type=scraper_type,
            total=total, ok=ok, error=error, none_resp=none_resp,
        )

    def test_outage_path_sends_empty_individual_and_nonempty_outage_lines(self):
        """All 5 clubs of a scraper type fail → discord called with empty individual + outage_lines."""
        svc = self._make_service(threshold=70.0)
        clubs = [self._make_metric(f"Club {i}", scraper_type="seatengine") for i in range(5)]
        summary = self._make_multi_club_summary(clubs)

        mock_config = _make_mock_config(channels=["discord"])
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            with patch.object(svc, '_send_discord_alert') as mock_alert:
                svc._check_and_alert(summary)
                mock_alert.assert_called_once()
                individual_arg = mock_alert.call_args[0][0]
                outage_lines_kwarg = mock_alert.call_args[1].get('outage_lines', [])
                assert individual_arg == []
                assert len(outage_lines_kwarg) == 1

    def test_partial_failure_sends_individual_with_empty_outage_lines(self):
        """Only 1/4 clubs of a scraper type fail (<80%) → individual entries, empty outage_lines."""
        svc = self._make_service(threshold=70.0)
        good = [self._make_metric(f"Good {i}", scraper_type="seatengine", ok=1, error=0) for i in range(3)]
        bad = [self._make_metric("Bad Club", scraper_type="seatengine")]
        summary = self._make_multi_club_summary(good + bad)

        mock_config = _make_mock_config(channels=["discord"])
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            with patch.object(svc, '_send_discord_alert') as mock_alert:
                svc._check_and_alert(summary)
                mock_alert.assert_called_once()
                individual_arg = mock_alert.call_args[0][0]
                outage_lines_kwarg = mock_alert.call_args[1].get('outage_lines', [])
                assert len(individual_arg) == 1
                assert individual_arg[0].club_name == "Bad Club"
                assert outage_lines_kwarg == []

    def test_outage_lines_contain_correct_summary_format(self):
        """Outage summary string contains scraper type and N/total count."""
        svc = self._make_service(threshold=70.0)
        clubs = [self._make_metric(f"Club {i}", scraper_type="tessera") for i in range(5)]
        summary = self._make_multi_club_summary(clubs)

        mock_config = _make_mock_config(channels=["discord"])
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            with patch.object(svc, '_send_discord_alert') as mock_alert:
                svc._check_and_alert(summary)
                outage_lines_kwarg = mock_alert.call_args[1].get('outage_lines', [])
                assert len(outage_lines_kwarg) == 1
                line = outage_lines_kwarg[0]
                assert "tessera" in line
                assert "5/5" in line


class TestCheckAndAlertChannelDispatch:
    """Tests for multi-channel dispatch logic in _check_and_alert."""

    def _make_service(self, threshold=70.0):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = threshold
        return svc

    def _run_with_channels(self, svc, channels):
        summary = _make_summary(error=1)
        mock_config = _make_mock_config(channels=channels)
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            with patch.object(svc, '_send_discord_alert') as mock_discord, \
                 patch.object(svc, '_send_email_alert') as mock_email, \
                 patch.object(svc, '_send_webhook_alert') as mock_webhook:
                svc._check_and_alert(summary)
                return mock_discord, mock_email, mock_webhook

    def test_discord_only_calls_discord(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["discord"])
        mock_discord.assert_called_once()
        mock_email.assert_not_called()
        mock_webhook.assert_not_called()

    def test_email_only_calls_email(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["email"])
        mock_discord.assert_not_called()
        mock_email.assert_called_once()
        mock_webhook.assert_not_called()

    def test_webhook_only_calls_webhook(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["webhook"])
        mock_discord.assert_not_called()
        mock_email.assert_not_called()
        mock_webhook.assert_called_once()

    def test_all_three_channels_calls_all(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(
            svc, ["discord", "email", "webhook"]
        )
        mock_discord.assert_called_once()
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()

    def test_empty_channels_calls_none(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, [])
        mock_discord.assert_not_called()
        mock_email.assert_not_called()
        mock_webhook.assert_not_called()


class TestClassifyFailing:
    def _make_service(self):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
        return svc

    def _m(self, name, scraper_type=None, ok=0, error=1, none_resp=0):
        total = ok + error + none_resp
        return DomainRequestMetrics(club_name=name, scraper_type=scraper_type,
                                    total=total, ok=ok, error=error, none_resp=none_resp)

    def _summary(self, metrics):
        s = ScrapingRunSummary()
        s.per_club.extend(metrics)
        return s

    def test_full_outage_produces_summary_line(self):
        """All 5 clubs of a scraper type fail → single outage summary, no individual entries."""
        svc = self._make_service()
        clubs = [self._m(f"Club {i}", scraper_type="seatengine") for i in range(5)]
        summary = self._summary(clubs)

        outage_lines, individual = svc._classify_failing(clubs, summary)

        assert len(outage_lines) == 1
        assert "seatengine" in outage_lines[0]
        assert "5/5" in outage_lines[0]
        assert individual == []

    def test_partial_outage_produces_individual_alerts(self):
        """Only 1/4 clubs fail (25%) → individual alerts, no outage summary."""
        svc = self._make_service()
        good = [self._m(f"Good {i}", scraper_type="seatengine", ok=1, error=0) for i in range(3)]
        bad = [self._m("Bad Club", scraper_type="seatengine")]
        summary = self._summary(good + bad)

        outage_lines, individual = svc._classify_failing(bad, summary)

        assert outage_lines == []
        assert len(individual) == 1
        assert individual[0].club_name == "Bad Club"

    def test_boundary_exactly_80_percent_is_outage(self):
        """4/5 clubs failing = 80% → triggers outage threshold."""
        svc = self._make_service()
        good = [self._m("Good", scraper_type="tessera", ok=1, error=0)]
        bad = [self._m(f"Bad {i}", scraper_type="tessera") for i in range(4)]
        summary = self._summary(good + bad)

        outage_lines, individual = svc._classify_failing(bad, summary)

        assert len(outage_lines) == 1
        assert "4/5" in outage_lines[0]
        assert individual == []

    def test_boundary_just_below_80_percent_is_individual(self):
        """3/4 clubs failing = 75% → below threshold, individual alerts."""
        svc = self._make_service()
        good = [self._m("Good", scraper_type="tessera", ok=1, error=0)]
        bad = [self._m(f"Bad {i}", scraper_type="tessera") for i in range(3)]
        summary = self._summary(good + bad)

        outage_lines, individual = svc._classify_failing(bad, summary)

        assert outage_lines == []
        assert len(individual) == 3

    def test_mixed_provider_outage_and_individual(self):
        """One provider at full outage (5/5), another at partial (1/5)."""
        svc = self._make_service()
        se_clubs = [self._m(f"SE {i}", scraper_type="seatengine") for i in range(5)]
        t_good = [self._m(f"TG {i}", scraper_type="tessera", ok=1, error=0) for i in range(4)]
        t_bad = [self._m("TB", scraper_type="tessera")]
        summary = self._summary(se_clubs + t_good + t_bad)

        outage_lines, individual = svc._classify_failing(se_clubs + t_bad, summary)

        assert len(outage_lines) == 1
        assert "seatengine" in outage_lines[0]
        assert len(individual) == 1
        assert individual[0].club_name == "TB"

    def test_no_scraper_type_treated_as_individual(self):
        """Clubs without scraper_type always go to individual regardless of count."""
        svc = self._make_service()
        clubs = [self._m(f"No Type {i}", scraper_type=None) for i in range(5)]
        summary = self._summary(clubs)

        outage_lines, individual = svc._classify_failing(clubs, summary)

        assert outage_lines == []
        assert len(individual) == 5


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

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
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
