"""Tests for ScrapingService per-club metrics, summary emission, and alerting."""

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
        with patch.object(svc, '_send_slack_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_not_called()

    def test_alert_fired_when_club_below_threshold(self):
        svc = self._make_service(threshold=70.0)
        summary = _make_summary(error=1)  # 0% success rate
        with patch.object(svc, '_send_slack_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_called_once()
            failing = mock_alert.call_args[0][0]
            assert len(failing) == 1
            assert failing[0].club_name == "Test Club"

    def test_alert_not_fired_when_exactly_at_threshold(self):
        svc = self._make_service(threshold=70.0)
        # exactly 70% success — should NOT fire (below_threshold uses strict <)
        summary = _make_summary(ok=7, error=3)
        with patch.object(svc, '_send_slack_alert') as mock_alert:
            svc._check_and_alert(summary)
            mock_alert.assert_not_called()


class TestSendSlackAlertSkipsWhenNotConfigured:
    def _make_service(self):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
        return svc

    def test_skips_when_slack_not_configured(self):
        svc = self._make_service()
        failing = [DomainRequestMetrics(club_name="X", total=1, error=1)]

        mock_config = MagicMock()
        mock_config.is_slack_configured.return_value = False
        mock_config.slack_webhook_url = None

        with patch('laughtrack.core.services.scraping.MonitoringConfig', create=True), \
             patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
            MockConfig.default.return_value = mock_config
            # Should not raise; just logs a warning
            svc._send_slack_alert(failing)  # Would fail at asyncio.run if alert was sent


class TestScrapeClubsWithMetrics:
    """Test that _scrape_clubs_with_metrics correctly classifies outcomes."""

    def _make_service(self):
        from laughtrack.core.services.scraping import ScrapingService
        with patch.object(ScrapingService, '__init__', lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc.success_rate_threshold = 70.0
            svc._scraping_resolver = MagicMock()
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
        svc._scraping_resolver.get.return_value = lambda club: mock_scraper

        club = self._make_club()
        _, summary = svc._scrape_clubs_with_metrics([club])

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
        svc._scraping_resolver.get.return_value = lambda club: mock_scraper

        club = self._make_club()
        _, summary = svc._scrape_clubs_with_metrics([club])

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
        svc._scraping_resolver.get.return_value = lambda club: mock_scraper

        club = self._make_club()
        _, summary = svc._scrape_clubs_with_metrics([club])

        m = summary.per_club[0]
        assert m.error == 1
        assert m.ok == 0
        assert m.none_resp == 0
