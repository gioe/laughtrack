"""
Base scraper for OvationTix venues that use production-list discovery.

Shared workflow:
1. Fetch a discovery page (calendar or buy-tickets page) to extract production IDs.
2. For each production ID, call the OvationTix REST API to get all upcoming
   performances: GET https://web.ovationtix.com/trs/api/rest/Production({id})/performance?
3. Build one event per performance (past events filtered out).
4. Fetch per-performance pricing via Performance({id}) endpoint using BatchScraper.
5. Return page data.

Subclasses specify:
- key: scraper registry key
- default_client_id: OvationTix org/client ID
- event_cls: dataclass type for events (must be OvationTixEvent subclass)
- page_data_cls: dataclass type for page data container
- transformer_cls: DataTransformer subclass for the event type
- default_name: fallback production name
- discover_urls(): how to find the discovery page URL
"""

import re
from urllib.parse import urlparse
from typing import ClassVar, List, Optional, Type

from laughtrack.core.clients.ovationtix.extractor import (
    extract_client_and_production_ids,
    extract_events_from_production,
    is_past_event,
    merge_production_ids,
    series_calendar_url,
)
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
)
from laughtrack.utilities.domain.show.factory import is_comedy_event
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

_OVATIONTIX_API_BASE = "https://web.ovationtix.com/trs/api/rest"

# Match existing inline semaphore concurrency — no delay between requests
_PRICING_BATCH_CONFIG = BatchScrapingConfig(
    max_concurrent=5,
    delay_between_requests=0,
    enable_logging=False,
)


class OvationTixProductionsScraper(BaseScraper):
    """
    Base scraper for OvationTix venues using production-list discovery.

    Subclasses must set the class-level attributes and implement discover_urls().
    """

    # --- Subclass configuration (must be overridden) ---
    default_client_id: ClassVar[str]
    event_cls: ClassVar[Type[OvationTixEvent]]
    page_data_cls: ClassVar[type]
    transformer_cls: ClassVar[type]
    default_name: ClassVar[str] = "Comedy Show"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(self.transformer_cls(club))
        self.batch_scraper = BatchScraper(self.logger_context, config=_PRICING_BATCH_CONFIG)
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._exclude_title_patterns = _compiled_metadata_patterns(
            self.club.source_metadata,
            "exclude_title_patterns",
        )

    async def _fetch_series_production_ids(self, discovery_url: str, client_id: Optional[str]):
        """Fetch the OvationTix series view and return its production IDs.

        The series view (web.ovationtix.com/trs/series/{client_id}) lists every
        upcoming production for a client on one static page — unlike the "/cal/"
        month view, which only shows the current month. Returns an empty list
        when the client ID is unknown, the discovery URL already targets the
        series view, or the fetch fails (so the configured discovery page's
        productions are still used).
        """
        if not client_id:
            return []

        series_url = series_calendar_url(client_id)
        if URLUtils.normalize_url(discovery_url) == URLUtils.normalize_url(series_url):
            # Discovery page is already the series view — avoid a redundant fetch.
            return []

        try:
            series_headers = BaseHeaders.get_headers(
                base_type="desktop_browser",
                domain="https://web.ovationtix.com",
                referer="https://web.ovationtix.com/",
            )
            series_html = await self.fetch_html(series_url, headers=series_headers)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: Could not fetch OvationTix series view "
                f"{series_url}: {e}",
                self.logger_context,
            )
            return []

        _, series_ids = extract_client_and_production_ids(series_html or "")
        return series_ids

    async def get_data(self, url: str):
        try:
            # Step 1: fetch discovery page and extract production IDs
            parsed = urlparse(url)
            page_origin = f"{parsed.scheme}://{parsed.netloc}"
            page_headers = BaseHeaders.get_headers(
                base_type="desktop_browser",
                domain=page_origin,
                referer=f"{page_origin}/",
            )
            html = await self.fetch_html(url, headers=page_headers)
            page_client_id, page_production_ids = extract_client_and_production_ids(html)

            # Resolve the client ID from the discovery page, falling back to the
            # per-venue configured ID. The "/cal/" discovery page only shows the
            # current month, so augment with the series view, which lists every
            # upcoming production on one page (TASK-2937 / convention #188).
            client_id = page_client_id or self.default_client_id
            series_production_ids = await self._fetch_series_production_ids(url, client_id)
            production_ids = merge_production_ids(page_production_ids, series_production_ids)

            if not production_ids:
                Logger.warn(
                    f"{self._log_prefix}: No OvationTix production IDs found on discovery "
                    f"page or series view",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: Discovered {len(production_ids)} unique production(s) "
                f"(discovery page contributed {len(page_production_ids)}, series view "
                f"contributed {len(series_production_ids)} before cross-source dedup)",
                self.logger_context,
            )

            # Step 2: query the OvationTix API for each production
            api_headers = BaseHeaders.get_headers(
                base_type="json",
                domain="https://web.ovationtix.com",
                origin="https://ci.ovationtix.com",
                referer="https://ci.ovationtix.com/",
                clientId=client_id,
                newCIRequest="true",
            )

            session = await self.get_session()
            all_events = []

            for prod_id in production_ids:
                prod_url = f"{_OVATIONTIX_API_BASE}/Production({prod_id})/performance?"
                try:
                    response = await session.get(prod_url, headers=api_headers)
                    if response.status_code == 404:
                        Logger.debug(
                            f"{self._log_prefix}: Production {prod_id} returned 404 — skipping",
                            self.logger_context,
                        )
                        continue
                    response.raise_for_status()
                    production_data = response.json()
                except Exception as e:
                    Logger.error(
                        f"{self._log_prefix}: Failed to fetch production {prod_id}: {e}",
                        self.logger_context,
                    )
                    continue

                events = extract_events_from_production(
                    production_data,
                    prod_id,
                    client_id,
                    default_name=self.default_name,
                    event_cls=self.event_cls,
                )

                # Filter past events
                upcoming = [
                    e for e in events
                    if not is_past_event(e.start_date, self.club.timezone)
                ]

                # Apply title-exclusion independently of comedy_filter (TASK-3480):
                # an all-comedy venue that only needs to drop class/camp/workshop
                # titles can set exclude_title_patterns WITHOUT enabling comedy_filter,
                # so real shows whose titles lack a comedy keyword are not lost to the
                # is_comedy_event keyword gate.
                if self._exclude_title_patterns and upcoming:
                    upcoming = self._apply_title_exclusions(upcoming)

                if self._comedy_filter and upcoming:
                    upcoming = await self._filter_comedy(upcoming)

                Logger.info(
                    f"{self._log_prefix}: Production {prod_id}: {len(upcoming)} upcoming event(s) "
                    f"(of {len(events)} total)",
                    self.logger_context,
                )

                # Step 3: fetch per-performance pricing via BatchScraper
                async def _fetch_pricing(perf_id: str) -> None:
                    perf_detail_url = f"{_OVATIONTIX_API_BASE}/Performance({perf_id})"
                    try:
                        perf_resp = await session.get(perf_detail_url, headers=api_headers)
                        perf_resp.raise_for_status()
                        perf_data = perf_resp.json()
                        # Find the event with this performance_id and set sections
                        for ev in upcoming:
                            if ev.performance_id == perf_id:
                                ev.sections = perf_data.get("sections") or []
                                break
                    except Exception as e:
                        Logger.warn(
                            f"{self._log_prefix}: Could not fetch pricing for "
                            f"performance {perf_id}: {e}",
                            self.logger_context,
                        )

                perf_ids = [e.performance_id for e in upcoming]
                await self.batch_scraper.process_batch(
                    perf_ids, _fetch_pricing, description="pricing enrichment"
                )

                all_events.extend(upcoming)

            if not all_events:
                Logger.warn(f"{self._log_prefix}: No upcoming events found", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Extracted {len(all_events)} total event(s)", self.logger_context)
            return self.page_data_cls(event_list=all_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error in get_data: {e}", self.logger_context)
            return None

    def _apply_title_exclusions(
        self, events: List[OvationTixEvent]
    ) -> List[OvationTixEvent]:
        """Drop events whose title matches any ``exclude_title_patterns`` entry.

        Runs independently of ``comedy_filter`` (TASK-3480) so an all-comedy
        venue can exclude class/camp/workshop titles without subjecting its real
        shows to the ``is_comedy_event`` keyword gate. When ``comedy_filter`` is
        also enabled this pass runs first, so :meth:`_filter_comedy` no longer
        needs to re-apply the exclusion list.
        """
        kept = [
            event
            for event in events
            if not any(
                pattern.search(event.production_name or "")
                for pattern in self._exclude_title_patterns
            )
        ]
        dropped = len(events) - len(kept)
        if dropped:
            Logger.info(
                f"{self._log_prefix}: exclude_title_patterns dropped "
                f"{dropped}/{len(events)} event(s)",
                self.logger_context,
            )
        return kept

    async def _filter_comedy(self, events: List[OvationTixEvent]) -> List[OvationTixEvent]:
        """Keep only comedy events when a mixed-use OvationTix source opts in.

        ``exclude_title_patterns`` is applied upstream by
        :meth:`_apply_title_exclusions` (independent of ``comedy_filter``), so
        this pass only runs the allowlist + keyword gate.
        """
        allow_subs = [
            value.strip().lower()
            for value in resolve_allowlist(self.club.source_metadata)
            if value.strip()
        ]
        kept = [
            event for event in events
            if _is_comedy_ovationtix_event(event, allow_subs)
        ]
        Logger.info(
            f"{self._log_prefix}: comedy filter kept {len(kept)}/{len(events)} event(s)",
            self.logger_context,
        )
        return kept


def _is_comedy_ovationtix_event(
    event: OvationTixEvent,
    allow_subs: List[str],
) -> bool:
    title = event.production_name or ""
    if allow_subs and any(value in title.lower() for value in allow_subs):
        return True
    return is_comedy_event(title, event.description)


def _compiled_metadata_patterns(metadata: Optional[dict], key: str) -> List[re.Pattern]:
    raw = (metadata or {}).get(key)
    if not raw:
        return []
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, list):
        values = [str(value) for value in raw if str(value).strip()]
    else:
        return []
    return [re.compile(value, re.IGNORECASE) for value in values]
