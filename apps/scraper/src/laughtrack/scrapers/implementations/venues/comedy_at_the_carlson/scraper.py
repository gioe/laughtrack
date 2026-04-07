"""
Comedy @ The Carlson scraper.

Workflow:
1. Fetch the OvationTix calendar page (/trs/cal/35843) to discover production IDs.
   The venue's own website (carlsoncomedy.com) is behind Cloudflare, so we use the
   OvationTix calendar directly as the discovery source.
2. For each production ID, call the OvationTix REST API to get all upcoming
   performances: GET https://web.ovationtix.com/trs/api/rest/Production({id})/performance?
3. Build one ComedyAtTheCarlsonEvent per performance (past events filtered out).
4. Fetch per-performance pricing via Performance({id}) endpoint.
5. Return ComedyAtTheCarlsonPageData.

The org/client ID (35843) is embedded in the production URLs on the calendar page
and re-used in both the API clientId header and the per-performance ticket URLs.
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyAtTheCarlsonPageData
from .extractor import ComedyAtTheCarlsonExtractor
from .transformer import ComedyAtTheCarlsonEventTransformer

_OVATIONTIX_API_BASE = "https://web.ovationtix.com/trs/api/rest"
_OVATIONTIX_CAL_BASE = "https://web.ovationtix.com/trs/cal"
_DEFAULT_CLIENT_ID = "35843"
_PRICING_CONCURRENCY = 5


class ComedyAtTheCarlsonScraper(BaseScraper):
    """
    Scraper for Comedy @ The Carlson (Rochester, NY).

    Uses the OvationTix REST API. Production IDs are discovered from the
    OvationTix calendar page so that new productions are picked up automatically.
    """

    key = "comedy_at_the_carlson"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComedyAtTheCarlsonEventTransformer(club))

    async def discover_urls(self) -> List[str]:
        return [f"{_OVATIONTIX_CAL_BASE}/{_DEFAULT_CLIENT_ID}"]

    async def get_data(self, url: str) -> Optional[ComedyAtTheCarlsonPageData]:
        try:
            # Step 1: fetch the OvationTix calendar page and extract production IDs
            page_headers = BaseHeaders.get_headers(
                base_type="desktop_browser",
                domain="https://web.ovationtix.com",
                referer="https://web.ovationtix.com/",
            )
            html = await self.fetch_html(url, headers=page_headers)
            client_id, production_ids = ComedyAtTheCarlsonExtractor.extract_client_and_production_ids(html)

            if not production_ids:
                Logger.warn(f"{self._log_prefix}: No OvationTix production IDs found on calendar page", self.logger_context)
                return None

            client_id = client_id or _DEFAULT_CLIENT_ID
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
            semaphore = asyncio.Semaphore(_PRICING_CONCURRENCY)

            async def fetch_pricing(event, _session=session, _headers=api_headers) -> None:
                async with semaphore:
                    perf_detail_url = f"{_OVATIONTIX_API_BASE}/Performance({event.performance_id})"
                    try:
                        perf_resp = await _session.get(perf_detail_url, headers=_headers)
                        perf_resp.raise_for_status()
                        perf_data = perf_resp.json()
                        event.sections = perf_data.get("sections") or []
                    except Exception as e:
                        Logger.warn(
                            f"{self._log_prefix}: Could not fetch pricing for "
                            f"performance {event.performance_id}: {e}",
                            self.logger_context,
                        )

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
                        f"{self._log_prefix}: Failed to fetch production {prod_id}: {e}", self.logger_context
                    )
                    continue

                events = ComedyAtTheCarlsonExtractor.extract_events_from_production(
                    production_data, prod_id, client_id
                )

                # Filter past events
                upcoming = [
                    e for e in events
                    if not ComedyAtTheCarlsonExtractor.is_past_event(e.start_date, self.club.timezone)
                ]

                Logger.info(
                    f"{self._log_prefix}: Production {prod_id}: {len(upcoming)} upcoming event(s) "
                    f"(of {len(events)} total)",
                    self.logger_context,
                )

                # Fetch per-performance pricing concurrently (bounded by semaphore)
                await asyncio.gather(*[fetch_pricing(e) for e in upcoming])

                all_events.extend(upcoming)

            if not all_events:
                Logger.warn(f"{self._log_prefix}: No upcoming events found", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Extracted {len(all_events)} total event(s)", self.logger_context)
            return ComedyAtTheCarlsonPageData(event_list=all_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error in get_data: {e}", self.logger_context)
            return None
