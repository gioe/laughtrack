from unittest.mock import MagicMock, patch

from laughtrack.core.models.domain_metrics import ScrapingRunSummary
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


def test_geocoding_outage_does_not_fail_scrape_all_clubs_run_summary_still_posts():
    from laughtrack.core.services.scraping import ScrapingService

    with patch.object(ScrapingService, "__init__", lambda self, *a, **kw: None):
        svc = ScrapingService.__new__(ScrapingService)
        svc.success_rate_threshold = 70.0
        svc.proxy_pool = None

    svc.club_handler = MagicMock()
    svc.club_handler.get_all_clubs.return_value = [MagicMock()]
    svc.club_handler.refresh_club_total_shows.return_value = None
    svc.production_company_handler = MagicMock()
    svc._result_processor = MagicMock()
    svc._result_processor.process_results.return_value = None

    summary = ScrapingRunSummary()
    db_result = DatabaseOperationResult(total=1, inserts=1)

    with patch.object(svc, "_try_validate_scraper_keys"), \
         patch.object(svc, "_scrape_clubs_with_metrics", return_value=([], summary, db_result)), \
         patch.object(svc, "_scrape_production_companies", return_value=([], ScrapingRunSummary(), DatabaseOperationResult())), \
         patch.object(svc, "_emit_summary"), \
         patch.object(svc, "_check_and_alert"), \
         patch("laughtrack.core.services.scraping.geocode_missing_clubs", side_effect=RuntimeError("nominatim down")), \
         patch("laughtrack.core.services.scraping.Logger.warn") as mock_warn, \
         patch.object(svc, "_send_run_summary") as mock_summary:
        svc.scrape_all_clubs()

    mock_summary.assert_called_once_with(summary, db_result)
    assert any("Club geocoding post-run failed" in call.args[0] for call in mock_warn.call_args_list)
