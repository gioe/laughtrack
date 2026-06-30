"""
Patchogue Theatre — OvationTix scraper, discovered via the Bowery Presents page.

The generic ``OvationTixScraper`` discovers production IDs from
``web.ovationtix.com/trs/cal/{clientId}``. For Patchogue (client 34780) that
calendar feed is incomplete — it returns a few production cards and omits known
Bowery-listed comedy shows such as Leslie Jones and Ben Bankas.

Discovery therefore runs off the Bowery Presents venue page
(``https://www.bowerypresents.com/venues/patchogue-theatre``). In 2026 Bowery
migrated that page off inline OvationTix deep-links to an AEG/AXS
``aegwebprod.blob.core.windows.net/.../events.json`` feed; each AEG event still
carries the underlying ``ci.ovationtix.com/34780/performance/<id>`` link in
``ticketing.ticketURL``. We extract the AEG feed URL(s) from the page, pull the
performance IDs whose embedded client id matches this venue, then hit the
per-performance endpoint (``Performance({id})``) for each — which returns
production identity, start date, availability, and pricing sections in a single
call. A legacy inline-link scrape remains as a fallback.

A keyword filter on production name + description narrows the output to
stand-up comedy so the multi-purpose theatre does not flood the catalogue
with concerts and musicals.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from laughtrack.core.clients.ovationtix.extractor import is_past_event

from .data import OvationTixPageData
from .extractor import (
    event_from_performance_response,
    extract_aeg_feed_urls,
    extract_performance_ids,
    is_comedy_relevant,
    performance_ids_from_aeg_feed,
)
from .transformer import OvationTixEventTransformer


_OVATIONTIX_API_BASE = "https://web.ovationtix.com/trs/api/rest"

_PERFORMANCE_BATCH_CONFIG = BatchScrapingConfig(
    max_concurrent=5,
    delay_between_requests=0,
    enable_logging=False,
)


class PatchogueTheatreScraper(BaseScraper):
    """Scraper for Patchogue Theatre using the Bowery Presents discovery path."""

    key = "patchogue_theatre"
    default_name = "Comedy Show"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(OvationTixEventTransformer(club))
        self.batch_scraper = BatchScraper(
            self.logger_context, config=_PERFORMANCE_BATCH_CONFIG
        )

        client_id = club.ovationtix_client_id
        if not client_id:
            raise ValueError(
                f"PatchogueTheatreScraper requires ovationtix_id on the active "
                f"scraping_sources row for club id={club.id} name='{club.name}'"
            )
        self._client_id = str(client_id)

    async def discover_urls(self) -> List[str]:
        if not self.club.scraping_url:
            raise ValueError(
                f"PatchogueTheatreScraper requires source_url on the active "
                f"scraping_sources row for club id={self.club.id} "
                f"name='{self.club.name}'"
            )
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def _discover_performance_ids(self, html: str, session) -> List[str]:
        """Resolve OvationTix performance IDs for this venue.

        Primary discovery is the AEG/AXS event feed(s) referenced on the Bowery
        venue page — Bowery dropped inline ``ci.ovationtix.com`` links in 2026,
        but each AEG event still carries the OvationTix purchase link in
        ``ticketing.ticketURL``, filtered to this venue by the embedded client
        id. Fallback is any legacy inline OvationTix deep-link still present in
        the HTML, so a future Bowery reversion keeps working.
        """
        feed_urls = extract_aeg_feed_urls(html)
        feed_headers = BaseHeaders.get_headers(base_type="json")

        seen: set = set()
        performance_ids: List[str] = []
        for feed_url in feed_urls:
            try:
                response = await session.get(feed_url, headers=feed_headers)
                response.raise_for_status()
                feed = response.json()
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: failed to fetch AEG feed {feed_url}: {e}",
                    self.logger_context,
                )
                continue
            for perf_id in performance_ids_from_aeg_feed(feed, self._client_id):
                if perf_id not in seen:
                    seen.add(perf_id)
                    performance_ids.append(perf_id)

        if performance_ids:
            Logger.info(
                f"{self._log_prefix}: discovered {len(performance_ids)} "
                f"performance(s) across {len(feed_urls)} AEG feed(s)",
                self.logger_context,
            )
            return performance_ids

        legacy_ids = extract_performance_ids(html, client_id=self._client_id)
        if legacy_ids:
            Logger.info(
                f"{self._log_prefix}: discovered {len(legacy_ids)} performance(s) "
                f"via legacy inline OvationTix links",
                self.logger_context,
            )
        return legacy_ids

    async def get_data(self, url: str) -> Optional[OvationTixPageData]:
        try:
            page_headers = BaseHeaders.get_headers(
                base_type="desktop_browser",
                domain="https://www.bowerypresents.com",
                referer="https://www.bowerypresents.com/",
            )
            html = await self.fetch_html(url, headers=page_headers)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty HTML from {url}",
                    self.logger_context,
                )
                return None

            api_headers = BaseHeaders.get_headers(
                base_type="json",
                domain="https://web.ovationtix.com",
                origin="https://ci.ovationtix.com",
                referer="https://ci.ovationtix.com/",
                clientId=self._client_id,
                newCIRequest="true",
            )

            session = await self.get_session()

            performance_ids = await self._discover_performance_ids(html, session)
            if not performance_ids:
                Logger.warn(
                    f"{self._log_prefix}: no OvationTix performances discovered "
                    f"on {url} (client_id={self._client_id})",
                    self.logger_context,
                )
                return None

            events: List[OvationTixEvent] = []

            async def _fetch_one(perf_id: str) -> None:
                detail_url = f"{_OVATIONTIX_API_BASE}/Performance({perf_id})"
                try:
                    response = await session.get(detail_url, headers=api_headers)
                    if response.status_code == 404:
                        Logger.debug(
                            f"{self._log_prefix}: performance {perf_id} 404 — "
                            f"likely cancelled, skipping",
                            self.logger_context,
                        )
                        return
                    response.raise_for_status()
                    payload = response.json()
                except Exception as e:
                    Logger.error(
                        f"{self._log_prefix}: failed to fetch performance "
                        f"{perf_id}: {e}",
                        self.logger_context,
                    )
                    return

                event = event_from_performance_response(
                    payload,
                    client_id=self._client_id,
                    default_name=self.default_name,
                )
                if event is None:
                    Logger.warn(
                        f"{self._log_prefix}: performance {perf_id} payload "
                        f"missing required fields",
                        self.logger_context,
                    )
                    return

                if is_past_event(event.start_date, self.club.timezone):
                    return
                if not is_comedy_relevant(event.production_name, event.description):
                    return

                events.append(event)

            await self.batch_scraper.process_batch(
                performance_ids,
                _fetch_one,
                description="patchogue performance fetch",
            )

            if not events:
                Logger.warn(
                    f"{self._log_prefix}: no comedy-relevant upcoming events "
                    f"found among {len(performance_ids)} performance(s)",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} comedy event(s) "
                f"from {len(performance_ids)} performance link(s)",
                self.logger_context,
            )
            return OvationTixPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error in get_data: {e}",
                self.logger_context,
            )
            return None
