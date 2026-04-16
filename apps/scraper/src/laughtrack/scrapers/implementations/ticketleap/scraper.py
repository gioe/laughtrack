"""TicketLeap platform scraper (Path B, listing → detail).

TicketLeap org listing pages (events.ticketleap.com/events/{org_slug}) do not
embed per-event JSON-LD — only event IDs inside window.dataLayer.push. Each
event detail page (events.ticketleap.com/event/{id}) carries a standard
schema.org Event JSON-LD block we can reuse the shared extractor on.

The listing page is client-rendered: curl-cffi receives a 17 KB shell without
the dataLayer.push payload, so we go straight to the Playwright browser for
that one fetch. Detail pages are server-rendered and work with plain
fetch_html (curl-cffi with automatic Playwright fallback on block pages).

Pipeline:
    1. collect_scraping_targets(): fetch listing with Playwright,
       regex-extract event IDs, return a list of per-event detail URLs.
    2. get_data(url): fetch detail page, run the shared JSON-LD EventExtractor,
       wrap the resulting JsonLdEvent in TicketleapPageData.

Multi-location policy (Mesquite St. 'funny' org):
    The 'funny' TicketLeap listing covers both the 617 Mesquite St. downtown
    venue and a 4535 S. Padre Island Dr. southside venue. Every event on the
    feed at onboarding time (all 7 upcoming shows, 2026-04 through 2026-07)
    was tagged `location.name == "MESQUITE ST COMEDY CLUB DOWNTOWN"`, so we
    model club 837 as the single downtown row. If future events for the
    southside location appear, split them off into a second club row and
    filter this scraper by JsonLdEvent.location.name. We did not add that
    filter now because there is no active southside inventory to drop —
    filtering pre-emptively would mask legitimate downtown shows if TicketLeap
    ever renames the downtown location label.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.shared.types import ScrapingTarget

from .data import TicketleapPageData
from .extractor import build_event_detail_url, extract_event_ids
from .transformer import TicketleapTransformer


class TicketleapScraper(BaseScraper):
    """Two-step scraper for venues hosted on events.ticketleap.com."""

    key = "ticketleap"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TicketleapTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Fetch the listing page and return event detail URLs."""
        listing_url = self.club.scraping_url
        if not listing_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no scraping_url configured",
                self.logger_context,
            )
            return []

        normalized_url = URLUtils.normalize_url(listing_url)

        # Listing page is client-rendered; the dataLayer.push payload only
        # appears after JS evaluation, so skip curl-cffi and go straight to
        # Playwright for this fetch.
        try:
            html = await self._fetch_html_with_js(normalized_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch TicketLeap listing {normalized_url}: {e}",
                self.logger_context,
            )
            return []

        if not html:
            Logger.warn(
                f"{self._log_prefix}: TicketLeap listing returned empty HTML: {normalized_url}",
                self.logger_context,
            )
            return []

        event_ids = extract_event_ids(html)
        if not event_ids:
            Logger.warn(
                f"{self._log_prefix}: No event IDs found in TicketLeap listing {normalized_url}",
                self.logger_context,
            )
            return []

        Logger.info(
            f"{self._log_prefix}: Discovered {len(event_ids)} TicketLeap event IDs",
            self.logger_context,
        )

        return [build_event_detail_url(eid) for eid in event_ids]

    async def get_data(self, target: ScrapingTarget) -> Optional[TicketleapPageData]:
        """Fetch one TicketLeap event detail page and extract the JSON-LD Event."""
        try:
            html = await self.fetch_html(target)
            events = EventExtractor.extract_events(html)

            if not events:
                Logger.warn(
                    f"{self._log_prefix}: No JSON-LD Event on TicketLeap detail page {target}",
                    self.logger_context,
                )
                return None

            return TicketleapPageData(events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting TicketLeap detail page {target}: {e}",
                self.logger_context,
            )
            return None
