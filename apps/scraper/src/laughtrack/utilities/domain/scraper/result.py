"""
Scraping Result Processor

This module processes and saves scraping results, coordinating between
metrics collection, show saving, and result reporting.
"""

import os
from datetime import datetime, timezone
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.organizer_venue.handler import OrganizerVenueHandler
from laughtrack.core.entities.show.service import ShowService
from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.metrics import MetricsService
from laughtrack.foundation.infrastructure.logger.logger import Logger


# Safety cap for stale-show reconciliation (TASK-2847). A single clean scrape
# that would drop more than this many future shows for one club at once is far
# more likely a silent parser break (upstream format change yielding zero/near-
# zero events on an HTTP 200) than that many genuine same-day cancellations, so
# the reconciler refuses and logs for human review rather than wiping inventory.
# Read at use-time so it can be retuned via env without a redeploy (convention
# #134); 0 or negative disables the cap.
_DEFAULT_RECONCILE_DELETE_CAP = 10


class ScrapingResultProcessor:
    """Processes and saves scraping results."""

    def __init__(self):
        """Initialize with required services."""
        self.show_service = ShowService()
        self.metrics_service = MetricsService()
        self.organizer_venue_handler = OrganizerVenueHandler()

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

        Single-venue scrapes reconcile against ``club_result.club_id``. Organizer
        / production-company proxy scrapes (``is_synthetic``) fan one feed out to
        many per-venue club_ids while ``club_result.club_id`` is the single proxy
        id, so they reconcile per distinct venue club_id present in this run's
        shows (TASK-2856) — see :meth:`_reconcile_organizer_venues`.

        Either way the delete is scoped to the club + scraper_key that just ran;
        the upsert re-creates a show on a later clean scrape if the source brings
        it back (self-healing).
        """
        if not self._is_clean_for_reconciliation(club_result):
            return
        if not club_result.scraper_key:
            # Without a scraper_key we cannot scope the delete safely.
            return
        if club_result.is_synthetic:
            self._reconcile_organizer_venues(club_result, cutoff)
            return
        if club_result.club_id is None:
            # Without a club_id we cannot scope the delete safely.
            return
        self._reconcile_one_venue(
            club_result.club_id,
            club_result.scraper_key,
            club_result.club_name,
            cutoff,
        )

    def _reconcile_organizer_venues(
        self, club_result: ClubScrapingResult, cutoff: datetime
    ) -> None:
        """Reconcile an organizer-mode scrape's present AND dropped venues.

        An Eventbrite organizer feed (source URL with ``/o/``) fans one fetch out
        to many physical venues via ``ClubHandler.upsert_for_eventbrite_venue``,
        persisting each show under its own venue club_id while
        ``club_result.club_id`` is the synthetic proxy id.

        Present venues (TASK-2856): every distinct venue club_id that produced a
        show this run is reconciled scoped to (venue club_id, scraper_key, cutoff)
        under the same clean-scrape gate (already checked by the caller) and the
        same per-venue RECONCILE_DELETE_CAP. A venue still in the feed keeps its
        re-seen shows (stamped after ``cutoff``); only its cancelled/delisted
        future shows are removed.

        Dropped venues (TASK-2859): the organizer's prior venue set is persisted
        in ``eventbrite_organizer_venues`` keyed by ``production_company_id``.
        Diffing this run's venue set against that prior set surfaces venues that
        dropped ENTIRELY from the feed (zero shows this run); their now-stale
        future shows are reconciled too. The history table is then updated to this
        run's venue set.

        Cross-organizer safety (TASK-2859 criterion 9184): because every Eventbrite
        show shares ``last_scraped_by='eventbrite'``, a venue covered by a second
        organizer feed — or by its own enabled direct Eventbrite scraping source —
        should not have its shows deleted by this organizer's reconcile. Both the
        present- and dropped-venue paths skip any venue
        :meth:`OrganizerVenueHandler.is_venue_covered_elsewhere` reports as owned
        elsewhere. The trade-off is that cancelled shows at a genuinely
        multi-organizer venue are not auto-reconciled (they age out when the
        owning source rescrapes).

        Bootstrap gap (residual of the conservative-skip design): the
        other-organizer probe only sees a sibling once that sibling has recorded
        the venue in ``eventbrite_organizer_venues``. During first rollout — or
        any window before a sibling organizer has run a clean scrape this cycle —
        a shared venue that lacks a direct Eventbrite source is NOT yet seen as
        covered, so this organizer can still reconcile the sibling's shows there.
        The clean-scrape gate and per-venue RECONCILE_DELETE_CAP bound the blast
        radius, and the gap closes once every covering organizer has recorded its
        set. Fully closing it would need per-show organizer attribution (a
        ``scraped_by_organizer_id`` on shows), which scopes the delete precisely
        rather than skipping shared venues — deferred as a heavier follow-up.

        When ``production_company_id`` is absent we cannot key the history or run
        the cross-organizer check, so only the present-venue reconcile runs
        (the TASK-2856 behaviour).
        """
        venue_club_ids = sorted(
            {
                show.club_id
                for show in club_result.shows
                if getattr(show, "club_id", None) is not None
                and show.club_id != Club.SYNTHETIC_PROXY_PLACEHOLDER_ID
            }
        )
        pc_id = club_result.production_company_id
        scraper_key = club_result.scraper_key

        for club_id in venue_club_ids:
            if pc_id is not None and self._venue_covered_elsewhere(pc_id, club_id):
                # A sibling organizer/source still maintains this venue — leave it.
                continue
            self._reconcile_one_venue(
                club_id,
                scraper_key,
                f"{club_result.club_name} (venue club_id={club_id})",
                cutoff,
            )

        if pc_id is None:
            # No organizer identity → cannot persist or diff a venue set, so the
            # present-venue reconcile above is all we can safely do.
            return

        self._reconcile_dropped_organizer_venues(
            pc_id, scraper_key, venue_club_ids, club_result.club_name, cutoff
        )

    def _reconcile_dropped_organizer_venues(
        self,
        production_company_id: int,
        scraper_key: str,
        current_club_ids: List[int],
        club_name: str,
        cutoff: datetime,
    ) -> None:
        """Reconcile venues that vanished from this organizer's feed (TASK-2859).

        Diffs the persisted prior venue set against this run's set; a venue in the
        prior set but absent now dropped entirely and has its stale future shows
        reconciled (unless a sibling source owns it). The history table is then
        rewritten to this run's venue set. Never raises — bookkeeping errors are
        logged so the run continues.
        """
        try:
            prior = set(
                self.organizer_venue_handler.get_venue_club_ids(production_company_id)
            )
        except Exception as e:
            Logger.error(
                f"Organizer venue-history read failed for "
                f"production_company={production_company_id}: {e}"
            )
            return

        current = set(current_club_ids)
        for club_id in sorted(prior - current):
            try:
                if not self._venue_covered_elsewhere(production_company_id, club_id):
                    self._reconcile_one_venue(
                        club_id,
                        scraper_key,
                        f"{club_name} (dropped venue club_id={club_id})",
                        cutoff,
                    )
                # Reconciled or owned by a sibling source, this organizer no longer
                # produces the venue — drop the stale history claim either way.
                self.organizer_venue_handler.forget_venue(
                    production_company_id, club_id
                )
            except Exception as e:
                Logger.error(
                    f"Dropped-venue reconciliation failed for "
                    f"production_company={production_company_id}, club_id={club_id}: {e}"
                )

        try:
            self.organizer_venue_handler.record_venues(
                production_company_id, sorted(current)
            )
        except Exception as e:
            Logger.error(
                f"Organizer venue-history write failed for "
                f"production_company={production_company_id}: {e}"
            )

    def _venue_covered_elsewhere(
        self, production_company_id: int, club_id: int
    ) -> bool:
        """Is this venue maintained by a sibling Eventbrite source? (criterion 9184)

        On a lookup error, return True (conservative): never delete a venue's
        shows when we cannot confirm this organizer exclusively owns it.
        """
        try:
            return self.organizer_venue_handler.is_venue_covered_elsewhere(
                production_company_id, club_id
            )
        except Exception as e:
            Logger.error(
                f"Cross-organizer coverage check failed for "
                f"production_company={production_company_id}, club_id={club_id}; "
                f"skipping reconcile to stay safe: {e}"
            )
            return True

    def _reconcile_one_venue(
        self, club_id: int, scraper_key: str, label: str, cutoff: datetime
    ) -> None:
        """Count → cap-check → delete stale future shows for one (club, scraper).

        Shared by the single-venue and organizer-mode paths. Scoping to
        ``scraper_key`` keeps a multi-source club's other scrapers' shows
        untouched; the ``cutoff`` excludes rows re-stamped this run. Never raises
        — a DB error is logged and swallowed so the run continues (the shows are
        already persisted).
        """
        try:
            stale_count = self.show_service.count_stale_future_shows(
                club_id, scraper_key, cutoff
            )
            if stale_count == 0:
                return
            cap = self._reconcile_delete_cap()
            if cap > 0 and stale_count > cap:
                Logger.warn(
                    f"Stale-show reconciliation SKIPPED for '{label}' "
                    f"(scraper={scraper_key}): {stale_count} future shows "
                    f"would be deleted, exceeding the safety cap of {cap}. This is the "
                    f"signature of a silent parser break, not normal cancellations — "
                    f"investigate the source before any manual cleanup."
                )
                return
            deleted = self.show_service.delete_stale_future_shows(
                club_id, scraper_key, cutoff
            )
        except Exception as e:  # pragma: no cover - defensive; never fail the run
            Logger.error(
                f"Stale-show reconciliation failed for '{label}': {e}"
            )
            return
        if deleted:
            titles = ", ".join(
                f"{row.get('name') or '(untitled)'} @ {row.get('date')}" for row in deleted
            )
            Logger.warn(
                f"Reconciled {len(deleted)} stale future show(s) for "
                f"'{label}' (scraper={scraper_key}, "
                f"source event cancelled/delisted): {titles}"
            )

    @staticmethod
    def _reconcile_delete_cap() -> int:
        """Max future shows one clean scrape may reconcile-delete for a club.

        Read at use-time (convention #134) so it can be retuned via
        ``RECONCILE_DELETE_CAP`` without a redeploy. Falls back to
        :data:`_DEFAULT_RECONCILE_DELETE_CAP`; a malformed value uses the
        default; 0 or negative disables the cap.
        """
        raw = os.environ.get("RECONCILE_DELETE_CAP")
        if raw is None or raw.strip() == "":
            return _DEFAULT_RECONCILE_DELETE_CAP
        try:
            return int(raw)
        except ValueError:
            Logger.warn(
                f"Invalid RECONCILE_DELETE_CAP={raw!r}; using default "
                f"{_DEFAULT_RECONCILE_DELETE_CAP}"
            )
            return _DEFAULT_RECONCILE_DELETE_CAP

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
