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


def _make_metric(name, scraper_type=None, ok=0, error=1, none_resp=0):
    total = ok + error + none_resp
    return DomainRequestMetrics(
        club_name=name, scraper_type=scraper_type,
        total=total, ok=ok, error=error, none_resp=none_resp,
    )


def _make_multi_club_summary(clubs):
    """Build a ScrapingRunSummary containing the given DomainRequestMetrics list."""
    s = ScrapingRunSummary()
    s.per_club.extend(clubs)
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

    def test_outage_path_sends_empty_individual_and_nonempty_outage_lines(self):
        """All 5 clubs of a scraper type fail → discord called with empty individual + outage_lines."""
        svc = self._make_service(threshold=70.0)
        clubs = [_make_metric(f"Club {i}", scraper_type="seatengine") for i in range(5)]
        summary = _make_multi_club_summary(clubs)

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
        good = [_make_metric(f"Good {i}", scraper_type="seatengine", ok=1, error=0) for i in range(3)]
        bad = [_make_metric("Bad Club", scraper_type="seatengine")]
        summary = _make_multi_club_summary(good + bad)

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
        clubs = [_make_metric(f"Club {i}", scraper_type="tessera") for i in range(5)]
        summary = _make_multi_club_summary(clubs)

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

    def test_full_outage_produces_summary_line(self):
        """All 5 clubs of a scraper type fail → single outage summary, no individual entries."""
        svc = self._make_service()
        clubs = [_make_metric(f"Club {i}", scraper_type="seatengine") for i in range(5)]
        summary = _make_multi_club_summary(clubs)

        outage_lines, individual = svc._classify_failing(clubs, summary)

        assert len(outage_lines) == 1
        assert "seatengine" in outage_lines[0]
        assert "5/5" in outage_lines[0]
        assert individual == []

    def test_partial_outage_produces_individual_alerts(self):
        """Only 1/4 clubs fail (25%) → individual alerts, no outage summary."""
        svc = self._make_service()
        good = [_make_metric(f"Good {i}", scraper_type="seatengine", ok=1, error=0) for i in range(3)]
        bad = [_make_metric("Bad Club", scraper_type="seatengine")]
        summary = _make_multi_club_summary(good + bad)

        outage_lines, individual = svc._classify_failing(bad, summary)

        assert outage_lines == []
        assert len(individual) == 1
        assert individual[0].club_name == "Bad Club"

    def test_boundary_exactly_80_percent_is_outage(self):
        """4/5 clubs failing = 80% → triggers outage threshold."""
        svc = self._make_service()
        good = [_make_metric("Good", scraper_type="tessera", ok=1, error=0)]
        bad = [_make_metric(f"Bad {i}", scraper_type="tessera") for i in range(4)]
        summary = _make_multi_club_summary(good + bad)

        outage_lines, individual = svc._classify_failing(bad, summary)

        assert len(outage_lines) == 1
        assert "4/5" in outage_lines[0]
        assert individual == []

    def test_boundary_just_below_80_percent_is_individual(self):
        """3/4 clubs failing = 75% → below threshold, individual alerts."""
        svc = self._make_service()
        good = [_make_metric("Good", scraper_type="tessera", ok=1, error=0)]
        bad = [_make_metric(f"Bad {i}", scraper_type="tessera") for i in range(3)]
        summary = _make_multi_club_summary(good + bad)

        outage_lines, individual = svc._classify_failing(bad, summary)

        assert outage_lines == []
        assert len(individual) == 3

    def test_mixed_provider_outage_and_individual(self):
        """One provider at full outage (5/5), another at partial (1/5)."""
        svc = self._make_service()
        se_clubs = [_make_metric(f"SE {i}", scraper_type="seatengine") for i in range(5)]
        t_good = [_make_metric(f"TG {i}", scraper_type="tessera", ok=1, error=0) for i in range(4)]
        t_bad = [_make_metric("TB", scraper_type="tessera")]
        summary = _make_multi_club_summary(se_clubs + t_good + t_bad)

        outage_lines, individual = svc._classify_failing(se_clubs + t_bad, summary)

        assert len(outage_lines) == 1
        assert "seatengine" in outage_lines[0]
        assert len(individual) == 1
        assert individual[0].club_name == "TB"

    def test_no_scraper_type_treated_as_individual(self):
        """Clubs without scraper_type always go to individual regardless of count."""
        svc = self._make_service()
        clubs = [_make_metric(f"No Type {i}", scraper_type=None) for i in range(5)]
        summary = _make_multi_club_summary(clubs)

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
        # Provide an enabled ScrapingSource so _sorted_enabled_sources returns it,
        # mirroring how production Club entities are constructed from scraping_sources.
        if scraper_key:
            source = MagicMock()
            source.scraper_key = scraper_key
            source.enabled = True
            source.priority = 0
            source.id = 1
            club.scraping_sources = [source]
            club.scraping_source = source
        else:
            club.scraping_sources = []
            club.scraping_source = None
        return club

    @pytest.mark.asyncio
    async def test_ok_when_shows_returned(self):
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        result = ClubScrapingResult(club_name="Club", shows=[MagicMock()], execution_time=1.0)
        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.return_value = result
        svc._scraping_resolver.get.return_value = lambda club, **kw: mock_scraper

        club = self._make_club()
        _, summary, _ = await svc._scrape_clubs_concurrently([club])

        assert len(summary.per_club) == 1
        m = summary.per_club[0]
        assert m.ok == 1
        assert m.none_resp == 0
        assert m.error == 0

    @pytest.mark.asyncio
    async def test_none_resp_when_no_shows_no_error(self):
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        result = ClubScrapingResult(club_name="Club", shows=[], execution_time=1.0)
        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.return_value = result
        svc._scraping_resolver.get.return_value = lambda club, **kw: mock_scraper

        club = self._make_club()
        _, summary, _ = await svc._scrape_clubs_concurrently([club])

        m = summary.per_club[0]
        assert m.none_resp == 1
        assert m.ok == 0
        assert m.error == 0

    @pytest.mark.asyncio
    async def test_error_when_result_has_error(self):
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        result = ClubScrapingResult(club_name="Club", shows=[], execution_time=0.0, error="boom")
        mock_scraper = MagicMock()
        mock_scraper.scrape_with_result.return_value = result
        svc._scraping_resolver.get.return_value = lambda club, **kw: mock_scraper

        club = self._make_club()
        _, summary, _ = await svc._scrape_clubs_concurrently([club])

        m = summary.per_club[0]
        assert m.error == 1
        assert m.ok == 0
        assert m.none_resp == 0

    @pytest.mark.asyncio
    async def test_clubs_run_concurrently(self):
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
        results, summary, _ = await svc._scrape_clubs_concurrently(clubs)
        elapsed = time.monotonic() - start

        assert len(results) == 4
        # Verify at least 2 clubs overlapped — this directly proves concurrency without relying on wall-clock timing
        assert max(active_at_once) >= 2

    @pytest.mark.asyncio
    async def test_one_club_failure_does_not_abort_others(self):
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
        results, summary, _ = await svc._scrape_clubs_concurrently(clubs)

        assert len(results) == 3
        assert len(summary.per_club) == 3
        good_metrics = [m for m in summary.per_club if "Good" in m.club_name]
        bad_metrics = [m for m in summary.per_club if "Bad" in m.club_name]
        assert all(m.ok == 1 for m in good_metrics)
        assert bad_metrics[0].error == 1

    @pytest.mark.asyncio
    async def test_skipped_clubs_emit_warning(self):
        """Clubs with no enabled scraping_sources are skipped and emit a summary warning."""
        from laughtrack.core.services.scraping import ScrapingService
        svc = self._make_service()

        # Both clubs have no scraping_sources, so _sorted_enabled_sources returns
        # an empty list and scrape_one short-circuits to the (None, None) skip path.
        no_key_club = self._make_club(name="No Key Club", scraper_key=None)
        no_key_club.scraper = None

        bad_key_club = self._make_club(name="Bad Key Club", scraper_key=None)
        bad_key_club.scraper = None

        with patch('laughtrack.core.services.scraping.Logger') as mock_logger:
            results, summary, _ = await svc._scrape_clubs_concurrently([no_key_club, bad_key_club])

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


class TestSendDiscordRunSummary:
    """Tests for _send_discord_run_summary — unconditional post-run Discord message."""

    def _make_service(self, threshold=70.0):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = threshold
        return svc

    def _make_db_result(self, total=10, inserts=8, updates=2):
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult
        return DatabaseOperationResult(total=total, inserts=inserts, updates=updates)

    def test_fires_on_clean_run_with_no_failures(self):
        """Summary is posted even when all clubs succeed (zero failures)."""
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()

        mock_config = _make_mock_config(channels=["discord"])
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.DiscordAlertChannel') as MockChannel:
            MockConfig.default.return_value = mock_config
            svc._send_discord_run_summary(summary, db_result)
            MockChannel.return_value.send.assert_called_once()

    def test_title_contains_clubs_ok_and_total(self):
        """Alert title shows clubs_ok/total_clubs count."""
        svc = self._make_service()
        clubs = [
            _make_metric("Club A", ok=1, error=0),
            _make_metric("Club B", ok=1, error=0),
            _make_metric("Club C", ok=0, error=1),
        ]
        summary = _make_multi_club_summary(clubs)
        db_result = self._make_db_result()

        mock_config = _make_mock_config(channels=["discord"])
        mock_alert_cls = MagicMock(return_value=MagicMock())
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', mock_alert_cls), \
             patch('gioe_libs.alerting.DiscordAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_discord_run_summary(summary, db_result)

        title = mock_alert_cls.call_args.kwargs.get('title', '')
        assert "2/3" in title
        assert "clubs OK" in title

    def test_body_includes_shows_counts(self):
        """Description includes shows scraped, inserted, and updated."""
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result(total=15, inserts=12, updates=3)

        mock_config = _make_mock_config(channels=["discord"])
        mock_alert_cls = MagicMock(return_value=MagicMock())
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', mock_alert_cls), \
             patch('gioe_libs.alerting.DiscordAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_discord_run_summary(summary, db_result)

        desc = mock_alert_cls.call_args.kwargs.get('message', '')
        assert "15" in desc  # total scraped
        assert "12" in desc  # inserted
        assert "3" in desc   # updated

    def test_per_club_breakdown_uses_checkmark_for_passing_clubs(self):
        """✅ icon appears for clubs at or above the success threshold."""
        svc = self._make_service(threshold=70.0)
        clubs = [_make_metric("Good Club", ok=1, error=0, none_resp=0)]
        summary = _make_multi_club_summary(clubs)
        db_result = self._make_db_result()

        mock_config = _make_mock_config(channels=["discord"])
        mock_alert_cls = MagicMock(return_value=MagicMock())
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', mock_alert_cls), \
             patch('gioe_libs.alerting.DiscordAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_discord_run_summary(summary, db_result)

        desc = mock_alert_cls.call_args.kwargs.get('message', '')
        assert "All clubs at or above threshold ✅" in desc

    def test_per_club_breakdown_uses_warning_for_failing_clubs(self):
        """⚠️ icon appears for clubs below the success threshold."""
        svc = self._make_service(threshold=70.0)
        clubs = [_make_metric("Bad Club", ok=0, error=1, none_resp=0)]
        summary = _make_multi_club_summary(clubs)
        db_result = self._make_db_result()

        mock_config = _make_mock_config(channels=["discord"])
        mock_alert_cls = MagicMock(return_value=MagicMock())
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', mock_alert_cls), \
             patch('gioe_libs.alerting.DiscordAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_discord_run_summary(summary, db_result)

        desc = mock_alert_cls.call_args.kwargs.get('message', '')
        assert "⚠️" in desc
        assert "Bad Club" in desc

    def test_skips_when_discord_not_configured(self):
        """No alert is sent when Discord is not configured."""
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()

        mock_config = MagicMock()
        mock_config.is_discord_configured.return_value = False
        mock_config.discord_webhook_url = None

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.DiscordAlertChannel') as MockChannel:
            MockConfig.default.return_value = mock_config
            svc._send_discord_run_summary(summary, db_result)
            MockChannel.return_value.send.assert_not_called()

    def test_scrape_all_clubs_calls_summary_with_db_result(self):
        """scrape_all_clubs passes db_result to _send_run_summary."""
        from laughtrack.core.services.scraping import ScrapingService
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult

        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
            svc.proxy_pool = None

        expected_db_result = DatabaseOperationResult(total=5, inserts=3, updates=2)
        summary = _make_summary(ok=1)

        svc.club_handler = MagicMock()
        svc.club_handler.get_all_clubs.return_value = [MagicMock()]
        svc.club_handler.refresh_club_total_shows.return_value = None
        svc.production_company_handler = MagicMock()
        svc._result_processor = MagicMock()
        svc._result_processor.process_results.return_value = None

        with patch.object(svc, '_try_validate_scraper_keys'), \
             patch.object(svc, '_scrape_clubs_with_metrics', return_value=([], summary, expected_db_result)), \
             patch.object(svc, '_scrape_production_companies', return_value=([], ScrapingRunSummary(), DatabaseOperationResult())), \
             patch.object(svc, '_emit_summary'), \
             patch.object(svc, '_check_and_alert'), \
             patch.object(svc, '_send_run_summary') as mock_summary:
            svc.scrape_all_clubs()
            mock_summary.assert_called_once_with(summary, expected_db_result)

    def test_scrape_single_club_refreshes_total_shows(self):
        """scrape_single_club refreshes clubs.total_shows after persisting results.

        Without this call, the denormalized clubs.total_shows counter goes stale
        whenever a venue is scraped via the per-club code path (e.g. make scrape-club).
        """
        from laughtrack.core.services.scraping import ScrapingService
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult

        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
            svc.proxy_pool = None

        mock_club = MagicMock()
        mock_club.name = "Test Club"
        svc.club_handler = MagicMock()
        svc.club_handler.get_clubs_by_ids.return_value = [mock_club]
        svc.club_handler.refresh_club_total_shows.return_value = None
        svc._result_processor = MagicMock()
        svc._result_processor.process_results.return_value = None

        with patch.object(svc, '_scrape_clubs_with_metrics',
                          return_value=([], _make_summary(ok=1), DatabaseOperationResult())):
            svc.scrape_single_club(club_id=837)

        svc.club_handler.refresh_club_total_shows.assert_called_once_with()

    def test_scrape_by_scraper_type_refreshes_total_shows(self):
        """scrape_by_scraper_type refreshes clubs.total_shows after persisting results.

        Without this call, running `make scrape-shows --types <type>` to backfill an
        entire platform leaves clubs.total_shows stale on every venue scraped that way.
        """
        from laughtrack.core.services.scraping import ScrapingService
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult

        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
            svc.proxy_pool = None

        mock_club = MagicMock()
        mock_club.name = "Test Club"
        svc.club_handler = MagicMock()
        svc.club_handler.get_clubs_for_scraper.return_value = [mock_club]
        svc.club_handler.refresh_club_total_shows.return_value = None
        svc._result_processor = MagicMock()
        svc._result_processor.process_results.return_value = None

        with patch.object(svc, '_scrape_clubs_with_metrics',
                          return_value=([], _make_summary(ok=1), DatabaseOperationResult())):
            svc.scrape_by_scraper_type(scraper_type="seatengine")

        svc.club_handler.refresh_club_total_shows.assert_called_once_with()


class TestSendRunSummary:
    """Tests for _send_run_summary channel dispatch."""

    def _make_service(self, threshold=70.0):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = threshold
        return svc

    def _make_db_result(self, total=10, inserts=8, updates=2):
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult
        return DatabaseOperationResult(total=total, inserts=inserts, updates=updates)

    def _run_with_channels(self, svc, channels):
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()
        mock_config = MagicMock()
        mock_config.get_configured_channels.return_value = channels
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch.object(svc, '_send_discord_run_summary') as mock_discord, \
             patch.object(svc, '_send_email_run_summary') as mock_email, \
             patch.object(svc, '_send_webhook_run_summary') as mock_webhook:
            MockConfig.default.return_value = mock_config
            svc._send_run_summary(summary, db_result)
        return mock_discord, mock_email, mock_webhook

    def test_email_only_calls_email_run_summary(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["email"])
        mock_discord.assert_not_called()
        mock_email.assert_called_once()
        mock_webhook.assert_not_called()

    def test_webhook_only_calls_webhook_run_summary(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["webhook"])
        mock_discord.assert_not_called()
        mock_email.assert_not_called()
        mock_webhook.assert_called_once()

    def test_email_without_discord_skips_discord(self):
        """When only email is configured (Discord absent), Discord summary is not sent."""
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["email"])
        mock_discord.assert_not_called()
        mock_email.assert_called_once()

    def test_webhook_without_discord_skips_discord(self):
        """When only webhook is configured (Discord absent), Discord summary is not sent."""
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, ["webhook"])
        mock_discord.assert_not_called()
        mock_webhook.assert_called_once()

    def test_all_channels_dispatches_all(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(
            svc, ["discord", "email", "webhook"]
        )
        mock_discord.assert_called_once()
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()

    def test_no_channels_dispatches_none(self):
        svc = self._make_service()
        mock_discord, mock_email, mock_webhook = self._run_with_channels(svc, [])
        mock_discord.assert_not_called()
        mock_email.assert_not_called()
        mock_webhook.assert_not_called()


class TestSendEmailRunSummary:
    """Tests for _send_email_run_summary."""

    def _make_service(self, threshold=70.0):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = threshold
        return svc

    def _make_db_result(self, total=10, inserts=8, updates=2):
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult
        return DatabaseOperationResult(total=total, inserts=inserts, updates=updates)

    def test_fires_when_email_configured(self):
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()

        mock_config = MagicMock()
        mock_config.is_email_configured.return_value = True
        mock_config.alert_recipients = ["ops@example.com"]

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('laughtrack.infrastructure.monitoring.channels.EmailAlertChannel') as MockChannel:
            MockConfig.default.return_value = mock_config
            svc._send_email_run_summary(summary, db_result)
            MockChannel.return_value.send.assert_called_once()

    def test_skips_when_email_not_configured(self):
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()

        mock_config = MagicMock()
        mock_config.is_email_configured.return_value = False
        mock_config.alert_recipients = []

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('laughtrack.infrastructure.monitoring.channels.EmailAlertChannel') as MockChannel:
            MockConfig.default.return_value = mock_config
            svc._send_email_run_summary(summary, db_result)
            MockChannel.return_value.send.assert_not_called()

    def test_run_summary_body_never_exceeds_text_channel_limit(self):
        """Email run summary body must be capped at _TEXT_CHANNEL_BODY_LIMIT chars."""
        from laughtrack.core.services.scraping import ScrapingService, _TEXT_CHANNEL_BODY_LIMIT

        svc = self._make_service()
        # Build a summary with enough clubs to blow past 8000 chars
        s = ScrapingRunSummary()
        for i in range(300):
            s.per_club.append(_make_metric(f"Club {i}", ok=1, error=0))
        db_result = self._make_db_result()

        captured_alerts = []

        def fake_Alert(**kwargs):
            a = MagicMock()
            a.message = kwargs.get("message", "")
            captured_alerts.append(a)
            return a

        mock_config = MagicMock()
        mock_config.is_email_configured.return_value = True
        mock_config.alert_recipients = ["ops@example.com"]

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', side_effect=fake_Alert), \
             patch('laughtrack.infrastructure.monitoring.channels.EmailAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_email_run_summary(s, db_result)

        assert len(captured_alerts) == 1
        assert len(captured_alerts[0].message) <= _TEXT_CHANNEL_BODY_LIMIT

    def test_run_summary_body_includes_omitted_count_when_truncated(self):
        """Email run summary truncation suffix must count omitted lines."""
        from laughtrack.core.services.scraping import ScrapingService

        svc = self._make_service()
        s = ScrapingRunSummary()
        for i in range(300):
            s.per_club.append(_make_metric(f"Club {i}", ok=1, error=0))
        db_result = self._make_db_result()

        captured_alerts = []

        def fake_Alert(**kwargs):
            a = MagicMock()
            a.message = kwargs.get("message", "")
            captured_alerts.append(a)
            return a

        mock_config = MagicMock()
        mock_config.is_email_configured.return_value = True
        mock_config.alert_recipients = ["ops@example.com"]

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', side_effect=fake_Alert), \
             patch('laughtrack.infrastructure.monitoring.channels.EmailAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_email_run_summary(s, db_result)

        assert len(captured_alerts) == 1
        assert "...and " in captured_alerts[0].message
        assert "more" in captured_alerts[0].message


class TestSendWebhookRunSummary:
    """Tests for _send_webhook_run_summary."""

    def _make_service(self, threshold=70.0):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = threshold
        return svc

    def _make_db_result(self, total=10, inserts=8, updates=2):
        from laughtrack.foundation.models.operation_result import DatabaseOperationResult
        return DatabaseOperationResult(total=total, inserts=inserts, updates=updates)

    def test_fires_when_webhook_configured(self):
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()

        mock_config = MagicMock()
        mock_config.is_webhook_configured.return_value = True
        mock_config.webhook_url = "https://hooks.example.com/run"
        mock_config.webhook_headers = {}

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.WebhookAlertChannel') as MockChannel:
            MockConfig.default.return_value = mock_config
            svc._send_webhook_run_summary(summary, db_result)
            MockChannel.return_value.send.assert_called_once()

    def test_skips_when_webhook_not_configured(self):
        svc = self._make_service()
        summary = _make_summary(ok=1)
        db_result = self._make_db_result()

        mock_config = MagicMock()
        mock_config.is_webhook_configured.return_value = False
        mock_config.webhook_url = None

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.WebhookAlertChannel') as MockChannel:
            MockConfig.default.return_value = mock_config
            svc._send_webhook_run_summary(summary, db_result)
            MockChannel.return_value.send.assert_not_called()

    def test_run_summary_body_never_exceeds_text_channel_limit(self):
        """Webhook run summary body must be capped at _TEXT_CHANNEL_BODY_LIMIT chars."""
        from laughtrack.core.services.scraping import ScrapingService, _TEXT_CHANNEL_BODY_LIMIT

        svc = self._make_service()
        s = ScrapingRunSummary()
        for i in range(300):
            s.per_club.append(_make_metric(f"Club {i}", ok=1, error=0))
        db_result = self._make_db_result()

        captured_alerts = []

        def fake_Alert(**kwargs):
            a = MagicMock()
            a.message = kwargs.get("message", "")
            captured_alerts.append(a)
            return a

        mock_config = MagicMock()
        mock_config.is_webhook_configured.return_value = True
        mock_config.webhook_url = "https://hooks.example.com/run"
        mock_config.webhook_headers = {}

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', side_effect=fake_Alert), \
             patch('gioe_libs.alerting.WebhookAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_webhook_run_summary(s, db_result)

        assert len(captured_alerts) == 1
        assert len(captured_alerts[0].message) <= _TEXT_CHANNEL_BODY_LIMIT

    def test_run_summary_body_includes_omitted_count_when_truncated(self):
        """Webhook run summary truncation suffix must count omitted lines."""
        from laughtrack.core.services.scraping import ScrapingService

        svc = self._make_service()
        s = ScrapingRunSummary()
        for i in range(300):
            s.per_club.append(_make_metric(f"Club {i}", ok=1, error=0))
        db_result = self._make_db_result()

        captured_alerts = []

        def fake_Alert(**kwargs):
            a = MagicMock()
            a.message = kwargs.get("message", "")
            captured_alerts.append(a)
            return a

        mock_config = MagicMock()
        mock_config.is_webhook_configured.return_value = True
        mock_config.webhook_url = "https://hooks.example.com/run"
        mock_config.webhook_headers = {}

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.Alert', side_effect=fake_Alert), \
             patch('gioe_libs.alerting.WebhookAlertChannel'):
            MockConfig.default.return_value = mock_config
            svc._send_webhook_run_summary(s, db_result)

        assert len(captured_alerts) == 1
        assert "...and " in captured_alerts[0].message
        assert "more" in captured_alerts[0].message


class TestTruncateDescriptionLines:
    """Unit tests for _truncate_description_lines embed-body helper."""

    def _fn(self, lines, limit):
        from laughtrack.core.services.scraping import _truncate_description_lines
        return _truncate_description_lines(lines, limit=limit)

    def test_short_list_is_returned_unchanged(self):
        lines = ["line one", "line two", "line three"]
        result = self._fn(lines, limit=2048)
        assert result == "\n".join(lines)

    def test_empty_list_returns_empty_string(self):
        assert self._fn([], limit=2048) == ""

    def test_result_never_exceeds_limit(self):
        # 337 domains each with a realistic line length (~60 chars)
        lines = [
            f"• Club {i}: 0% (0/1 ok, 0 empty, 1 errors)"
            for i in range(337)
        ]
        result = self._fn(lines, limit=2048)
        assert len(result) <= 2048

    def test_truncated_result_contains_and_more_suffix(self):
        lines = [f"• Club {i}: 0% (0/1 ok, 0 empty, 1 errors)" for i in range(337)]
        result = self._fn(lines, limit=2048)
        assert "...and " in result
        assert "more" in result

    def test_truncated_suffix_count_is_accurate(self):
        lines = [f"line {i}" for i in range(100)]
        result = self._fn(lines, limit=200)
        # Extract suffix count
        kept_lines = [line for line in result.split("\n") if not line.startswith("...and")]
        suffix_line = [line for line in result.split("\n") if line.startswith("...and")]
        assert len(suffix_line) == 1
        omitted_count = int(suffix_line[0].split()[1])
        assert len(kept_lines) + omitted_count == 100

    def test_outage_lines_appear_before_individual_clubs(self):
        """Platform-wide outage summaries (first in list) must not be dropped when truncating."""
        outage = ["⚠️ eventbrite appears to be down (50/50 venues failed)"]
        clubs = [f"• Club {i}: 0% (0/1 ok, 0 empty, 1 errors)" for i in range(200)]
        lines = outage + clubs
        result = self._fn(lines, limit=2048)
        assert outage[0] in result

    def test_greedy_packing_includes_short_lines_after_long_line(self):
        """A long line that doesn't fit should not cause all subsequent shorter lines to be dropped."""
        long_line = "X" * 150
        short_lines = [f"• Club {i}: short" for i in range(5)]
        # limit=200: long_line alone (150 chars) fits, but with a newline + short_line + suffix it may not.
        # The key assertion: short lines after a skipped long line must still appear.
        lines = ["header"] + [long_line] + short_lines
        result = self._fn(lines, limit=200)
        assert len(result) <= 200
        # At least one short line should be included (greedy packing, not early break)
        short_lines_in_result = [l for l in short_lines if l in result]
        assert len(short_lines_in_result) > 0, (
            "Greedy packing should include short lines that follow a skipped long line"
        )

    def test_discord_alert_description_never_exceeds_limit_with_many_failing(self):
        """Integration-style: _send_discord_alert must not produce an embed body > 2048 chars."""
        from laughtrack.core.services.scraping import ScrapingService

        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0

        # Build 337 failing metrics (mirrors the real incident)
        failing = [
            DomainRequestMetrics(club_name=f"Club {i}", total=1, ok=0, error=1)
            for i in range(337)
        ]

        sent_messages = []

        def fake_send(alert):
            sent_messages.append(alert.message)
            return True

        mock_channel = MagicMock()
        mock_channel.send = fake_send

        mock_config = MagicMock()
        mock_config.is_discord_configured.return_value = True
        mock_config.discord_webhook_url = "https://discord.example/webhook"

        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch('gioe_libs.alerting.DiscordAlertChannel', return_value=mock_channel):
            MockConfig.default.return_value = mock_config
            svc._send_discord_alert(failing)

        assert len(sent_messages) == 1
        assert len(sent_messages[0]) <= 2048
