"""
Generic Tixr scraper for venues whose calendar page links to Tixr events.

Any venue that lists shows by embedding tixr.com/e/{id} short URLs or
tixr.com/groups/*/events/* long-form URLs can be onboarded with only a
DB row (scraper='tixr', scraping_url=<calendar page>) — no Python changes needed.

Pipeline:
1. Fetch club.scraping_url as HTML.
2. Extract all Tixr event URLs (short and long form) via TixrExtractor.
2.5. If the page embeds an Organization JSON-LD block, filter to only URLs whose
     event ID appears in that block — these are the events Tixr has fully configured
     server-side (reliable JSON-LD on individual event pages).  Falls back to all
     HTML-extracted URLs when the Org JSON-LD block is absent.
3. Batch-resolve each URL to a TixrEvent via TixrClient.get_event_detail_from_url().
4. Return TixrPageData containing the resolved events.
"""

from typing import List, Optional

from laughtrack.core.clients.tixr import TixrVenueEventTransformer
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .extractor import TixrExtractor
from .data import TixrPageData


class TixrScraper(BaseScraper):
    """
    Generic scraper for venues that list Tixr event links on a calendar page.

    Supports both short-form (tixr.com/e/{id}) and long-form
    (tixr.com/groups/*/events/*-{id}) Tixr URLs. A new venue can be onboarded
    by inserting a DB row with scraper='tixr' and scraping_url set to its
    calendar page — no code changes required.
    """

    key = "tixr"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TixrVenueEventTransformer(club))
        self.tixr_client = create_monitored_tixr_client(club)
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the venue calendar page URL."""
        url = self.club.scraping_url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return [url]

    async def get_data(self, url: str) -> Optional[TixrPageData]:
        """
        Fetch the calendar page, extract Tixr URLs, and resolve each to a TixrEvent.

        Args:
            url: Venue calendar page URL (from scraping_url)

        Returns:
            TixrPageData containing resolved TixrEvent objects, or None if no events found
        """
        try:
            normalized = URLUtils.normalize_url(url)
            # Tixr group pages (tixr.com/groups/*) are behind DataDome WAF and
            # require a bare curl_cffi session to bypass bot detection.  Non-Tixr
            # calendar pages (venue's own domain) are fetched via the standard
            # HttpClient path which includes Playwright fallback.
            if "tixr.com" in normalized:
                html_content = await self.tixr_client._fetch_tixr_page(normalized)
            else:
                html_content = await self.fetch_html(normalized)

            if not html_content:
                Logger.info(f"{self._log_prefix}: No HTML content returned from {url}", self.logger_context)
                return None

            all_tixr_urls = TixrExtractor.extract_tixr_urls(html_content)

            if not all_tixr_urls:
                Logger.warn(
                    f"{self._log_prefix}: 0 Tixr URLs extracted from 200-response page {url} "
                    f"(html_len={len(html_content)}) — either a bot-block interstitial that "
                    f"bypassed DataDome classification or a genuinely-empty calendar",
                    self.logger_context,
                )
                return None

            # Filter to only events listed in the Organization JSON-LD block — these
            # are the ones Tixr has fully configured server-side and reliably embed
            # JSON-LD on their individual event pages.  Fall back to all HTML URLs
            # when the Org JSON-LD block is absent (non-group-page calendars).
            #
            # Match by numeric event ID rather than URL string: the JSON-LD block may
            # list long-form URLs while the calendar page HTML contains short-form URLs
            # for the same events (or vice versa).  A string-equality check would
            # produce an empty intersection even when the event sets overlap perfectly.
            org_jsonld_urls = TixrExtractor.extract_org_jsonld_event_urls(html_content)
            if org_jsonld_urls:
                org_event_ids = {
                    TixrExtractor.get_event_id(u) for u in org_jsonld_urls
                } - {None}
                tixr_urls = [
                    u for u in all_tixr_urls
                    if TixrExtractor.get_event_id(u) in org_event_ids
                ]
                skipped = len(all_tixr_urls) - len(tixr_urls)
                if skipped > 0:
                    Logger.info(
                        f"{self._log_prefix}: Skipping {skipped} of {len(all_tixr_urls)} URLs "
                        f"not in group JSON-LD (no server-side event data available)",
                        self.logger_context,
                    )
            else:
                tixr_urls = all_tixr_urls

            if not tixr_urls:
                Logger.info(f"{self._log_prefix}: No processable Tixr URLs after filtering on {url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Extracted {len(tixr_urls)} Tixr URLs from {url}", self.logger_context)

            results = await self.batch_scraper.process_batch(
                tixr_urls,
                lambda u: self.tixr_client.get_event_detail_from_url(u),
                "Tixr event extraction",
            )
            tixr_events = results

            if not tixr_events:
                Logger.info(
                    f"{self._log_prefix}: No TixrEvents returned from {len(tixr_urls)} URLs on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: Successfully processed {len(tixr_events)} TixrEvents from {len(tixr_urls)} URLs",
                self.logger_context,
            )
            return TixrPageData(event_list=tixr_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
