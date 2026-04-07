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

from urllib.parse import urlparse
from typing import ClassVar, List, Optional, Type

from laughtrack.core.clients.ovationtix.extractor import (
    extract_client_and_production_ids,
    extract_events_from_production,
    is_past_event,
)
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
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
            client_id, production_ids = extract_client_and_production_ids(html)

            if not production_ids:
                Logger.warn(
                    f"{self._log_prefix}: No OvationTix production IDs found on discovery page",
                    self.logger_context,
                )
                return None

            client_id = client_id or self.default_client_id
            Logger.info(
                f"{self._log_prefix}: Discovered {len(production_ids)} production(s)",
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
