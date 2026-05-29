"""Tests for the run-health gate on the unconditional Discord run summary.

Before TASK-2511 the scraper posted a full run summary to Discord after every
`scrape_all_clubs` run, burying real signal (failures, regressions) under
per-run noise. Now that Grafana reads the persisted scraper-health tables and
fires rolling-average regression alerts, the per-run Discord summary is gated on
run health: a *healthy* run produces no Discord post. Discord therefore carries
only failures (this summary on a failing run, alongside the _check_and_alert
failure alert) and regressions (Grafana). Email and webhook stay unconditional.

The gate lives in `_send_run_summary`; `_send_discord_run_summary` itself is the
unchanged renderer and is exercised by test_scraping_service_metrics.py.
"""

from unittest.mock import MagicMock, patch

from laughtrack.core.models.domain_metrics import DomainRequestMetrics, ScrapingRunSummary
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


def _make_service(threshold=70.0):
    from laughtrack.core.services.scraping import ScrapingService
    with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
        svc = ScrapingService.__new__(ScrapingService)
        svc.success_rate_threshold = threshold
    return svc


def _summary(metrics):
    s = ScrapingRunSummary()
    s.per_club.extend(metrics)
    return s


def _ok(name="OK Club"):
    return DomainRequestMetrics(club_name=name, total=1, ok=1)


def _failing(name="Broken Club"):
    return DomainRequestMetrics(club_name=name, total=1, error=1, fetches_failed=1)


def _empty_calendar(name="Empty Club"):
    # fetches completed cleanly, parser reached, zero items before filter →
    # ScrapeOutcome.EMPTY_CALENDAR (below threshold but not actionable).
    return DomainRequestMetrics(
        club_name=name, total=1, none_resp=1, fetches_ok=12, items_before_filter=0,
    )


def _parser_rejected(name="Parser Rejected Club"):
    # items existed before filter but all were rejected → CLASSIFIER_REJECTED_ALL
    # (below threshold and actionable).
    return DomainRequestMetrics(
        club_name=name, total=1, none_resp=1, fetches_ok=1, items_before_filter=3,
    )


def _db_result():
    return DatabaseOperationResult(total=10, inserts=8, updates=2)


def _dispatch(svc, summary):
    """Run _send_run_summary with discord configured, returning the discord mock."""
    mock_config = MagicMock()
    mock_config.get_configured_channels.return_value = ["discord"]
    with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
         patch.object(svc, '_send_discord_run_summary') as mock_discord:
        MockConfig.default.return_value = mock_config
        svc._send_run_summary(summary, _db_result())
    return mock_discord


class TestIsHealthyRun:
    def test_all_ok_is_healthy(self):
        svc = _make_service()
        assert svc._is_healthy_run(_summary([_ok()])) is True

    def test_failing_club_is_unhealthy(self):
        svc = _make_service()
        assert svc._is_healthy_run(_summary([_ok(), _failing()])) is False

    def test_empty_calendar_only_is_healthy(self):
        """EMPTY_CALENDAR venues are below threshold but non-actionable, so a run
        containing only empty-calendar clubs is still healthy."""
        svc = _make_service()
        assert svc._is_healthy_run(_summary([_empty_calendar()])) is True

    def test_parser_rejected_is_unhealthy(self):
        """CLASSIFIER_REJECTED_ALL is actionable — the same outcome _check_and_alert
        routes to its parser bucket — so it makes a run unhealthy."""
        svc = _make_service()
        assert svc._is_healthy_run(_summary([_parser_rejected()])) is False

    def test_empty_summary_is_healthy(self):
        svc = _make_service()
        assert svc._is_healthy_run(ScrapingRunSummary()) is True


class TestHealthyRunSkipsDiscordSummary:
    def test_healthy_run_does_not_dispatch_discord_summary(self):
        svc = _make_service()
        mock_discord = _dispatch(svc, _summary([_ok()]))
        mock_discord.assert_not_called()

    def test_empty_calendar_only_run_does_not_dispatch_discord_summary(self):
        svc = _make_service()
        mock_discord = _dispatch(svc, _summary([_ok(), _empty_calendar()]))
        mock_discord.assert_not_called()

    def test_failing_run_still_dispatches_discord_summary(self):
        svc = _make_service()
        mock_discord = _dispatch(svc, _summary([_ok(), _failing()]))
        mock_discord.assert_called_once()

    def test_parser_rejected_run_still_dispatches_discord_summary(self):
        svc = _make_service()
        mock_discord = _dispatch(svc, _summary([_parser_rejected()]))
        mock_discord.assert_called_once()


class TestEmailWebhookRemainUnconditional:
    """The gate is Discord-specific: email and webhook still fire on healthy runs."""

    def _dispatch_channels(self, svc, summary, channels):
        mock_config = MagicMock()
        mock_config.get_configured_channels.return_value = channels
        with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig, \
             patch.object(svc, '_send_discord_run_summary') as mock_discord, \
             patch.object(svc, '_send_email_run_summary') as mock_email, \
             patch.object(svc, '_send_webhook_run_summary') as mock_webhook:
            MockConfig.default.return_value = mock_config
            svc._send_run_summary(summary, _db_result())
        return mock_discord, mock_email, mock_webhook

    def test_healthy_run_still_sends_email_and_webhook(self):
        svc = _make_service()
        mock_discord, mock_email, mock_webhook = self._dispatch_channels(
            svc, _summary([_ok()]), ["discord", "email", "webhook"]
        )
        mock_discord.assert_not_called()
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()

    def test_failing_run_sends_all_three(self):
        svc = _make_service()
        mock_discord, mock_email, mock_webhook = self._dispatch_channels(
            svc, _summary([_failing()]), ["discord", "email", "webhook"]
        )
        mock_discord.assert_called_once()
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()
