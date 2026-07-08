"""Scraping service package — thin re-export shim.

The implementation lives in service.py (TASK-3644 moved it out of this
__init__ so package imports stay cheap and diffs stay reviewable). Every
name the old monolithic __init__ defined — public API, private helpers that
tests import, and the collaborator imports — is re-exported here so
``from laughtrack.core.services.scraping import X`` keeps working unchanged.

NOTE for tests: ``patch("laughtrack.core.services.scraping.<name>")`` no
longer affects the implementation — module-level lookups resolve against
service.py's globals. Patch ``laughtrack.core.services.scraping.service.<name>``
instead.
"""

from laughtrack.core.services.scraping.service import (  # noqa: F401
    # Public API
    ScrapingService,
    # Collaborators re-exported for import-path compatibility
    BaseScraper,
    Club,
    ClubGeocodingResult,
    ClubHandler,
    ClubScrapingResult,
    ClubSelector,
    DatabaseOperationResult,
    DomainRequestMetrics,
    Logger,
    ProductionCompany,
    ProductionCompanyHandler,
    ProxyPool,
    ScrapeOutcome,
    ScraperResolver,
    ScrapingResultProcessor,
    ScrapingRunSummary,
    ScrapingSource,
    build_services,
    geocode_missing_clubs,
    serialized_db_call,
    # Module constants (several are imported directly by tests)
    _DB_WRITE_TIMEOUT,
    _DEFAULT_CROSS_HOST_REDIRECT_TUPLE_THRESHOLD,
    _DEFAULT_MAX_CONCURRENT_CLUBS,
    _DEFAULT_PER_CLUB_TIMEOUT,
    _DEFAULT_SUCCESS_RATE_THRESHOLD,
    _DISCORD_DESCRIPTION_LIMIT,
    _ERROR_EXCERPT_MAX_CHARS,
    _EVENTBRITE_ORG_ID_RES,
    _EXECUTOR_SHUTDOWN_TIMEOUT,
    _MAX_FAILING_CLUBS_LISTED,
    _OUTAGE_THRESHOLD,
    _PER_SCRAPER_TIMEOUT_OVERRIDES,
    _TEXT_CHANNEL_BODY_LIMIT,
    _UNREGISTERED_SCRAPER_KEY_CAUSE_HINT,
    # Module helpers (several are imported directly by tests)
    _build_proxy_club,
    _build_source_proxy_club,
    _build_synthetic_proxy_for_company,
    _copy_diagnostics_into_metrics,
    _extract_eventbrite_organizer_id,
    _extract_tickettailor_account,
    _format_failing_club_line,
    _format_per_club_line,
    _gha_run_url,
    _is_next_stop_comedy_url,
    _per_club_timeout_for,
    _run_summary_metadata,
    _scrape_with_context,
    _synthetic_source_for_company,
    _truncate_description_lines,
)

__all__ = ["ScrapingService"]
