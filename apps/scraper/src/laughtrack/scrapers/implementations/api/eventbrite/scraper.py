"""
EventbriteScraper for venues using Eventbrite's API.

This scraper has two operating modes:

- **Single-venue mode** — the configured Eventbrite source URL points at a venue
  (no ``/o/`` segment). Every event in the feed belongs to that venue, so the
  standard BaseScraper pipeline applies: fetch events, transform each one with
  the configured ``EventbriteEventTransformer`` whose ``club`` is the scraping
  Club, and produce one Show per event.

- **Organizer mode** — the source URL contains ``/o/`` (an Eventbrite organizer
  feed). A single organizer can run shows at many different venues, so the
  scraper bypasses the standard transformer pipeline and instead:
    1. fetches the organizer's events with ``expand=venue`` already applied by
       the client,
    2. groups events by ``venue.id``,
    3. upserts a per-venue ``clubs`` row via
       ``ClubHandler.upsert_for_eventbrite_venue`` for each distinct venue,
    4. produces a Show per event whose ``club_id`` is the per-venue club id.
  Production-company stamping (``production_company_id``) is applied later by
  the scraping orchestrator on every Show in the result, regardless of which
  per-venue club each Show points at.
"""

import asyncio
import os
from collections import defaultdict
from typing import List, Optional, Tuple

from laughtrack.core.clients.eventbrite.client import EventbriteClient
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.database.write_lock import (
    LockHeldError,
    serialized_db_call,
)
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from .extractor import EventbriteExtractor
from .transformer import EventbriteEventTransformer


# Per-venue upsert deadline inside _upsert_one. The organizer-mode pipeline
# dispatches one _upsert_one coroutine per distinct venue via asyncio.gather;
# each coroutine awaits loop.run_in_executor(None, serialized_db_call, ...).
# Without a bounded wait, a stuck upsert would block the gather forever and
# leave the EB scraper hanging until the orchestrator's per-club asyncio.wait_for
# fired — at which point the orchestrator only sees ONE row (the organizer
# scrape) and cannot name which venue inside the feed stalled.
#
# TASK-2554 design decision: bound the await at the EB call site rather than
# pushing a hold-time timeout into the write_lock layer. CPython threads are
# not safely cancelable, so a lock-layer hold-time bound can't actually
# interrupt a stuck DB call — it can only bound the *wait* side (which
# TASK-2553 already does via _LOCK_HOLD_TIMEOUT=30s + LockHeldError). The
# wait-side bound here is the missing piece: when an EB upsert hangs, the
# asyncio.wait_for cancels _upsert_one's await so the gather() can complete
# and the venue name lands in the error log. The executor thread keeps
# running and may still hold _DB_WRITE_LOCK, but TASK-2553's fail-fast
# converts that into LockHeldError for subsequent serialized_db_call callers
# instead of unbounded waits.
#
# 60s = comfortably above the 30s _LOCK_HOLD_TIMEOUT (so legitimate sibling
# contention doesn't trip it) and well under the orchestrator's 180s default
# per-club scrape budget (so the EB scraper finishes its own gather() before
# its parent timeout cancels it).
_EB_UPSERT_TIMEOUT = 60


# TASK-2626: retry semantics for a single LockHeldError on the per-venue upsert.
# The 30s _LOCK_HOLD_TIMEOUT is the cascade-detection threshold; a retry after
# a short backoff often succeeds because the stuck prior writer's outermost
# timeout (asyncio.wait_for at 300s, or the platform's own statement_timeout)
# eventually fires and releases the lock. We retry once — empirically, if a
# second attempt also hits LockHeldError, the lock-holder is stuck for the
# remainder of the run and further retries would only consume the EB
# scraper's parent budget without changing the outcome.
#
# Backoff is read at use-time from EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS so
# nightly runs can tune without code change (mirrors LOCK_HOLD_TIMEOUT and
# MAX_CONCURRENT_CLUBS). 2s default = enough headroom for a typical Neon
# statement_timeout (30s) cascade to clear without making the slow-path
# branch dominate the EB scraper's per-club budget.
_EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS = 2.0


def _lock_timeout_retry_backoff() -> float:
    """Resolve the LockHeldError retry backoff at use-time.

    Reads ``EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS`` from env, falling back to
    ``_EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS``. Use-time read so monkeypatched
    env in tests applies without a re-import.

    Falls back to the module default on a malformed value (e.g. ``"2s"`` or
    an empty string). Without this, a misconfigured env var would raise
    ``ValueError`` inside ``_upsert_one`` and propagate out through
    ``asyncio.gather`` — crashing the entire organizer scrape rather than
    just slowing the retry. The fail-soft is the safer operational
    contract for a tunable knob that's only consulted on the rare
    LockHeldError path.
    """
    raw = os.environ.get("EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS")
    if raw is None:
        return _EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS
    try:
        return float(raw)
    except ValueError:
        Logger.warn(
            f"EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS={raw!r} is not a valid float; "
            f"falling back to {_EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS}s default"
        )
        return _EB_LOCK_TIMEOUT_RETRY_BACKOFF_SECS


class EventbriteScraper(BaseScraper):
    """
    Scraper for venues that use Eventbrite for event management.

    Reads the club's eventbrite_id field and uses :class:`EventbriteClient` to
    fetch events. When the configured source URL is an organizer feed (contains
    ``/o/``), per-event venue routing is enabled via :meth:`_scrape_organizer_async`.
    """

    key = 'eventbrite'

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EventbriteEventTransformer(club))

        # Validate that club has eventbrite_id
        if not club.eventbrite_id:
            raise ValueError(f"Club {club.name} does not have an eventbrite_id configured")

        # Initialize the Eventbrite client
        self.eventbrite_client = EventbriteClient(club, proxy_pool=self.proxy_pool)

        self.logger_context = club.as_context()

        self._club_handler = ClubHandler()

    @property
    def _is_organizer_mode(self) -> bool:
        """True when the configured source URL targets an Eventbrite organizer feed.

        Organizer feeds (``eventbrite.com/o/...``) span many venues; per-event
        venue routing is required so each Show is attached to its own ``clubs``
        row. The substring check mirrors ``_extract_eventbrite_organizer_id`` in
        services/scraping so a URL that activates organizer mode here is the
        same one the orchestrator's synthetic-proxy builder accepts.
        """
        return "eventbrite.com/o/" in (self.club.scraping_url or "")

    async def collect_scraping_targets(self) -> List[str]:
        """API-based: single logical target representing the venue/organizer ID."""
        return [self.club.eventbrite_id] if self.club.eventbrite_id else []

    async def get_data(self, target: str) -> Optional[EventListContainer]:
        """Fetch Eventbrite events and wrap into PageData container.

        Only used by the standard pipeline in single-venue mode. In organizer
        mode :meth:`scrape_async` is overridden so this method is never reached.
        """
        try:
            if not target:
                return None
            Logger.info(f"{self._log_prefix}: Fetching Eventbrite events for venue {target}", self.logger_context)
            events = await self.eventbrite_client.fetch_all_events()
            if events is None:
                Logger.warn(f"{self._log_prefix}: Network failure fetching Eventbrite events for {target}", self.logger_context)
                return None
            return EventbriteExtractor.to_page_data(events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error fetching Eventbrite data: {e}", self.logger_context)
            return None

    async def scrape_async(self) -> List[Show]:
        """Dispatch to organizer-mode routing when the source URL is a ``/o/`` feed."""
        if not self._is_organizer_mode:
            return await super().scrape_async()
        try:
            shows = await self._scrape_organizer_async()
            Logger.info(
                f"{self._log_prefix}: Scraped {len(shows)} total shows",
                self.logger_context,
            )
            return shows
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Scraping failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    @staticmethod
    def _venue_dedupe_key(api_venue) -> Optional[Tuple[str, str, str]]:
        """Build a (name, city, state) dedupe key for the per-organizer upsert pass.

        Returns ``None`` for events whose ``_api_venue`` is missing or has no
        usable name — those events can't be routed to a per-venue club and are
        dropped upstream with a single aggregate warning. Name is required
        because the SQL UPSERT in ``upsert_for_eventbrite_venue`` keys on
        ``clubs.name``; city/state default to empty strings when absent so two
        events that share a name and have nothing else fill in still collapse
        to one group rather than splitting on missing-vs-present address data.
        """
        if api_venue is None:
            return None
        name = getattr(api_venue, "name", None)
        if not name or not str(name).strip():
            return None
        address = getattr(api_venue, "address", None)
        city = getattr(address, "city", None) if address is not None else None
        region = getattr(address, "region", None) if address is not None else None
        return (
            str(name).strip().lower(),
            str(city or "").strip().lower(),
            str(region or "").strip().lower(),
        )

    async def _scrape_organizer_async(self) -> List[Show]:
        """Organizer-mode pipeline: group events by venue, upsert per-venue clubs.

        Mirrors the per-venue routing pattern previously used by the retired
        EventbriteNationalScraper — each distinct venue triggers one
        ``upsert_for_eventbrite_venue`` call, and every event at that venue
        becomes a Show whose ``club_id`` points at the per-venue club.
        """
        events = await self.eventbrite_client.fetch_all_events()
        if not events:
            Logger.info(f"{self._log_prefix}: organizer feed returned no events", self.logger_context)
            return []

        # Group events by normalized (name, city, state). Eventbrite emits
        # multiple distinct venue.id values for the same physical venue
        # (TASK-1900: production_company id=2's organizer feed returned 4
        # events with 4 distinct venue_ids but only 2 distinct physical
        # venues), so grouping by venue.id over-fragments and triggers one
        # redundant upsert_for_eventbrite_venue call per duplicate id —
        # each acquiring the process-wide serialized_db_call write lock.
        # The SQL UPSERT keys on clubs.name as a backstop, but the dedupe
        # avoids the redundant lock acquisitions entirely.
        venue_groups: dict = defaultdict(list)
        events_without_venue = 0
        for event in events:
            api_venue = event._api_venue
            key = self._venue_dedupe_key(api_venue)
            if key is None:
                events_without_venue += 1
                continue
            venue_groups[key].append(event)

        if events_without_venue:
            Logger.warn(
                f"{self._log_prefix}: {events_without_venue} event(s) had no venue data — skipping",
                self.logger_context,
            )

        if not venue_groups:
            return []

        loop = asyncio.get_running_loop()

        def _record_lock_timeout(venue_label: str, dropped_events: int) -> None:
            """Record a venue's persist-layer lock timeout on the current
            ScrapeDiagnostics (no-op when nothing is bound — e.g. ad-hoc
            invocations outside the scrape-with-result context).

            TASK-2626: the recorder is the signal scrape_with_result reads to
            populate ClubScrapingResult.error with a 'lock_timeout:' prefix,
            converting the historical silent-drop outcome (organizer feed's
            num_shows=0 with error=null) into a Grafana-actionable error
            metric without losing the successful sibling venues' shows.
            """
            diagnostics = current_diagnostics()
            if diagnostics is not None:
                diagnostics.record_persist_lock_timeout(venue_label, dropped_events)

        async def _await_upsert(api_venue):
            """One bounded upsert attempt. Raises asyncio.TimeoutError on
            wait_for expiry or LockHeldError when the write lock's cascade
            fail-fast fires. Other exceptions propagate untouched."""
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    serialized_db_call,
                    self._club_handler.upsert_for_eventbrite_venue,
                    api_venue,
                ),
                timeout=_EB_UPSERT_TIMEOUT,
            )

        async def _upsert_one(venue_key, group) -> List[Show]:
            api_venue = group[0]._api_venue
            venue_label = getattr(api_venue, "name", None) or str(venue_key)
            try:
                venue_club = await _await_upsert(api_venue)
            except LockHeldError as exc:
                # TASK-2626: retry once after a brief backoff. A stuck prior
                # writer is usually held by a hung DB call whose outermost
                # timeout (asyncio.wait_for at 300s, or the platform's
                # statement_timeout) eventually fires; sleeping
                # _lock_timeout_retry_backoff() seconds gives that cleanup a
                # chance to release the lock before we conclude the events
                # are lost. We retry exactly once — if the second attempt
                # also fails, the holder is stuck for the run.
                Logger.warn(
                    f"{self._log_prefix}: upsert for venue '{venue_label}' hit "
                    f"LockHeldError ({exc}) — retrying once after backoff",
                    self.logger_context,
                )
                await asyncio.sleep(_lock_timeout_retry_backoff())
                try:
                    venue_club = await _await_upsert(api_venue)
                except LockHeldError as retry_exc:
                    _record_lock_timeout(venue_label, len(group))
                    Logger.error(
                        f"{self._log_prefix}: upsert for venue '{venue_label}' hit "
                        f"LockHeldError on retry ({retry_exc}) — venue skipped "
                        f"({len(group)} event(s) lost)",
                        self.logger_context,
                    )
                    return []
                except asyncio.TimeoutError:
                    _record_lock_timeout(venue_label, len(group))
                    Logger.error(
                        f"{self._log_prefix}: upsert for venue '{venue_label}' timed out "
                        f"after {_EB_UPSERT_TIMEOUT}s on retry — venue skipped "
                        f"({len(group)} event(s) lost)",
                        self.logger_context,
                    )
                    return []
                except Exception as retry_exc:
                    # Intentionally NOT recorded as a lock_timeout incident
                    # — the lock-class branches (LockHeldError, TimeoutError)
                    # above do record, but a generic exception on retry is a
                    # different failure class (transient DB error, malformed
                    # venue payload, etc.) that surfaces as a per-venue ERROR
                    # log and is the same shape as the outer 'failed to upsert
                    # club' branch below. Recording it under lock_timeout:
                    # would attribute the wrong incident class to the Grafana
                    # alert and dilute the signal the prefix is meant to carry.
                    Logger.error(
                        f"{self._log_prefix}: failed to upsert club for venue "
                        f"'{venue_label}' on retry: {retry_exc}",
                        self.logger_context,
                    )
                    return []
            except asyncio.TimeoutError:
                # The await is cancelled but the executor thread keeps running
                # and may still hold _DB_WRITE_LOCK — see _EB_UPSERT_TIMEOUT's
                # module-level note. Record the venue to diagnostics so the
                # silent drop surfaces on ClubScrapingResult.error (TASK-2626);
                # the aggregate "yielded 0 shows from N event(s)" WARN below
                # the gather() still fires, but operators now also see the
                # incident on the metric row's error field.
                _record_lock_timeout(venue_label, len(group))
                Logger.error(
                    f"{self._log_prefix}: upsert for venue '{venue_label}' timed out after "
                    f"{_EB_UPSERT_TIMEOUT}s — venue skipped ({len(group)} event(s) lost)",
                    self.logger_context,
                )
                return []
            except Exception as exc:
                Logger.error(
                    f"{self._log_prefix}: failed to upsert club for venue '{venue_label}': {exc}",
                    self.logger_context,
                )
                return []

            if venue_club is None:
                Logger.warn(
                    f"{self._log_prefix}: upsert returned None for venue '{venue_label}' — skipping {len(group)} event(s)",
                    self.logger_context,
                )
                return []

            # to_show is wrapped in try/except so an unexpected raise on a
            # single event does not propagate out of asyncio.gather and
            # cancel sibling _upsert_one tasks — the previous sequential
            # for-loop completed already-iterated venues, and that
            # regression surface is preserved here.
            group_shows: List[Show] = []
            for event in group:
                try:
                    show = event.to_show(venue_club)
                except Exception as exc:
                    Logger.error(
                        f"{self._log_prefix}: to_show failed for venue '{venue_label}' event "
                        f"'{getattr(event, 'name', '?')}': {exc}",
                        self.logger_context,
                    )
                    continue
                if show:
                    group_shows.append(show)
            return group_shows

        # Run per-venue upserts concurrently. serialized_db_call still serializes
        # the actual writes through the process-wide DB lock, so concurrency
        # only parallelizes the executor dispatch and Show construction —
        # overlapping clubs upserts are still impossible. Each _upsert_one
        # await is bounded by _EB_UPSERT_TIMEOUT so a single hung executor
        # thread cannot pin this gather() open past the EB scraper's parent
        # per-club timeout.
        per_venue_shows = await asyncio.gather(
            *[_upsert_one(key, group) for key, group in venue_groups.items()]
        )

        # Aggregate warn whenever a venue group produced 0 shows from N>0
        # input events. _upsert_one already logs each per-event failure
        # (upsert error, venue_club None, to_show error), but the aggregate
        # outcome was previously silent — making nightly silent-drop
        # incidents (TASK-1927: 'Big Couch' produced clubs row + source
        # but 0 shows with no aggregate warning) hard to detect at log
        # read. Mirrors the events_without_venue pattern above.
        for (venue_key, group), group_shows in zip(venue_groups.items(), per_venue_shows):
            if group and not group_shows:
                api_venue = group[0]._api_venue
                venue_label = getattr(api_venue, "name", None) or str(venue_key)
                Logger.warn(
                    f"{self._log_prefix}: venue group '{venue_label}' yielded 0 shows from {len(group)} event(s)",
                    self.logger_context,
                )

        shows: List[Show] = [show for group_shows in per_venue_shows for show in group_shows]

        Logger.info(
            f"{self._log_prefix}: organizer feed produced {len(shows)} show(s) across {len(venue_groups)} venue(s)",
            self.logger_context,
        )
        return shows
