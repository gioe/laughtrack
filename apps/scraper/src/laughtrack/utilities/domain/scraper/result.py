"""
Scraping Result Processor

This module processes and saves scraping results, coordinating between
metrics collection, show saving, and result reporting.
"""

from datetime import datetime, timezone
from typing import List, Optional

from laughtrack.core.entities.show.service import ShowService
from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.metrics import MetricsService
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ScrapingResultProcessor:
    """Processes and saves scraping results."""

    def __init__(self):
        """Initialize with required services."""
        self.show_service = ShowService()
        self.metrics_service = MetricsService()

    def start_run(self) -> None:
        """Mark the start of a scraping run before any per-club writes begin."""
        self.metrics_service.start_session()

    def insert_club_result(self, club_result: ClubScrapingResult) -> DatabaseOperationResult:
        """Persist shows for a single completed club immediately, then reconcile
        stale future shows whose source event was cancelled/delisted (TASK-2847).

        Must be called while holding the caller's db_lock to ensure thread safety.
        """
        # Capture the reconciliation cutoff BEFORE persisting: Show.to_tuple()
        # stamps last_scraped_date=now() at upsert time, so shows re-seen this
        # run land strictly after this instant while stale rows keep their older
        # timestamp. This must precede insert_shows for the delete predicate to
        # separate touched from stale rows.
        reconcile_cutoff = datetime.now(timezone.utc)

        db_result = DatabaseOperationResult()
        if club_result.shows:
            Logger.info(f"Persisting {len(club_result.shows)} shows for '{club_result.club_name}'...")
            db_result = self.show_service.insert_shows(
                club_result.shows,
                club_name=club_result.club_name,
                scraper_key=club_result.scraper_key,
            )

        self._reconcile_stale_future_shows(club_result, reconcile_cutoff)
        return db_result

    def _reconcile_stale_future_shows(
        self, club_result: ClubScrapingResult, cutoff: datetime
    ) -> None:
        """Delete future shows this scraper stopped seeing on a CLEAN scrape.

        Gated on :meth:`_is_clean_for_reconciliation` so a failed, errored, or
        bot-blocked scrape never deletes real inventory (TASK-2847 criterion 2).
        Scoped to the club + scraper_key that just ran; the upsert re-creates a
        show on a later clean scrape if the source brings it back (self-healing).
        """
        if not self._is_clean_for_reconciliation(club_result):
            return
        if club_result.club_id is None or not club_result.scraper_key:
            # Without a club_id + scraper_key we cannot scope the delete safely.
            return
        try:
            deleted = self.show_service.delete_stale_future_shows(
                club_result.club_id, club_result.scraper_key, cutoff
            )
        except Exception as e:  # pragma: no cover - defensive; never fail the run
            Logger.error(
                f"Stale-show reconciliation failed for '{club_result.club_name}': {e}"
            )
            return
        if deleted:
            titles = ", ".join(
                f"{row.get('name') or '(untitled)'} @ {row.get('date')}" for row in deleted
            )
            Logger.warn(
                f"Reconciled {len(deleted)} stale future show(s) for "
                f"'{club_result.club_name}' (scraper={club_result.scraper_key}, "
                f"source event cancelled/delisted): {titles}"
            )

    @staticmethod
    def _is_clean_for_reconciliation(club_result: ClubScrapingResult) -> bool:
        """Is this scrape trustworthy enough to delete shows it didn't re-emit?

        Mirrors the safe subset of ``ScrapeOutcome`` (domain_metrics): only
        HEALTHY (shows present) and EMPTY_CALENDAR (the fetch layer reached the
        source and the parser found zero events) qualify. A scrape that errored,
        was bot-blocked, had a failed fetch, or never completed a fetch is
        DEGRADED and must NOT trigger deletion (criterion 2). CLASSIFIER_REJECTED_ALL
        (parser saw candidates but dropped them all) is also excluded — a parser
        bug there could wrongly delete live inventory.
        """
        if club_result.error is not None or club_result.bot_block_detected:
            return False
        if (club_result.fetches_failed or 0) > 0:
            return False
        if (club_result.fetches_ok or 0) <= 0:
            # No successful fetch → DEGRADED fallback; absence is not trustworthy.
            return False
        if club_result.shows:
            return True  # HEALTHY
        # Zero shows is only safe when the parser genuinely saw no candidates
        # (EMPTY_CALENDAR); items_before_filter > 0 means CLASSIFIER_REJECTED_ALL.
        return (club_result.items_before_filter or 0) == 0

    def process_results(
        self,
        club_scraping_results: List[ClubScrapingResult],
        db_result: Optional[DatabaseOperationResult] = None,
    ) -> DatabaseOperationResult:
        """Finalize scraping run: close metrics session.

        Shows are already persisted per-club by insert_club_result(); this method
        only runs the metrics/dashboard pipeline using the accumulated db_result.
        """
        Logger.info("Finalizing scraping results...")
        if db_result is None:
            db_result = DatabaseOperationResult()
        self.metrics_service.end_session(club_scraping_results, db_result)
        return db_result
