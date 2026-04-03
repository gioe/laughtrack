"""
Laugh Factory Covina scraper implementation.

Laugh Factory Covina (laughfactory.com/covina) lists upcoming shows on their
Tixr group page (tixr.com/groups/laughfactorycovina). The scraper:
1. Fetches the Tixr group page using DataDome-safe bare curl_cffi fetch
2. Parses the Organization JSON-LD block to find events Tixr has fully configured
   server-side (these reliably embed JSON-LD on their individual event pages)
3. Uses TixrClient to fetch full event details for each URL via JSON-LD parsing

Background: The group page lists 17+ event URLs in its HTML, but many use the
--{id} double-dash URL format where Tixr renders the page client-side without
embedding JSON-LD. Only events that appear in the group page's Organization
JSON-LD block are guaranteed to have server-rendered JSON-LD on their individual
pages. Attempting the others produces "11 failed" in the batch log with no
recoverable data — filtering them out before the batch pass eliminates that noise.
"""

import json
import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .extractor import LaughFactoryCovinaEventExtractor
from .page_data import LaughFactoryCovinaPageData
from .transformer import LaughFactoryCovinaEventTransformer


class LaughFactoryCovinaScraper(BaseScraper):
    """
    Scraper for Laugh Factory Covina comedy club.

    Extracts Tixr event URLs from the Laugh Factory Covina Tixr group page, then
    fetches full event details via TixrClient's JSON-LD parsing.

    The Tixr group page is fetched using TixrClient's bare curl_cffi session
    (no application headers) to avoid DataDome bot-detection.
    """

    key = "laugh_factory_covina"

    # Matches the --{numeric_id} double-dash suffix used by Tixr's client-side
    # rendered event template (e.g. "slug--182870").
    _DOUBLE_DASH_ID_RE = re.compile(r"--\d+(?:[/?#]|$)")

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LaughFactoryCovinaEventTransformer(club))
        self.tixr_client = create_monitored_tixr_client(club)
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

    @staticmethod
    def _extract_org_jsonld_event_urls(html_content: str) -> List[str]:
        """
        Extract event URLs from the Organization JSON-LD block on the Tixr group page.

        Tixr embeds an Organization schema block listing the group's featured events,
        each with a startDate.  These are the only events that also have server-rendered
        JSON-LD on their individual pages.

        Args:
            html_content: HTML of the Tixr group page

        Returns:
            List of event page URLs found in the Organization JSON-LD events array
        """
        urls: List[str] = []
        blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        for raw in blocks:
            try:
                parsed = json.loads(raw.strip())
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(parsed, dict) or parsed.get("@type") != "Organization":
                continue
            for event in parsed.get("events", []):
                if isinstance(event, dict) and event.get("url"):
                    urls.append(event["url"])
        return urls

    async def get_data(self, url: str) -> Optional[LaughFactoryCovinaPageData]:
        """
        Fetch the Laugh Factory Covina Tixr group page and extract TixrEvent objects.

        Args:
            url: The Tixr group page URL (tixr.com/groups/laughfactorycovina)

        Returns:
            LaughFactoryCovinaPageData containing TixrEvent objects, or None if no events found
        """
        try:
            # Fetch via DataDome-safe bare curl_cffi session (no application headers)
            html_content = await self.tixr_client._fetch_tixr_page(url)
            if not html_content:
                Logger.info(f"{self._log_prefix}: No HTML content returned from {url}", self.logger_context)
                return None

            all_tixr_urls = LaughFactoryCovinaEventExtractor.extract_tixr_urls(html_content)

            if not all_tixr_urls:
                Logger.info(f"{self._log_prefix}: No Tixr URLs found on {url}", self.logger_context)
                return None

            # Use the Organization JSON-LD block to filter down to only events that
            # Tixr has fully configured server-side.  These reliably embed JSON-LD
            # on their individual pages.  Events in the HTML list that aren't in the
            # Org JSON-LD use client-side rendering with no static date data and would
            # produce batch failures with no recoverable information.
            org_jsonld_urls = self._extract_org_jsonld_event_urls(html_content)

            if org_jsonld_urls:
                org_url_set = set(org_jsonld_urls)
                tixr_urls = [u for u in all_tixr_urls if u in org_url_set]
                skipped = len(all_tixr_urls) - len(tixr_urls)
                if skipped > 0:
                    Logger.info(
                        f"{self._log_prefix}: Skipping {skipped} of {len(all_tixr_urls)} URLs "
                        f"not in group JSON-LD (no server-side event data available)",
                        self.logger_context,
                    )
            else:
                # Org JSON-LD absent — fall back to all HTML-extracted URLs
                tixr_urls = all_tixr_urls

            if not tixr_urls:
                Logger.info(f"{self._log_prefix}: No processable Tixr URLs after filtering on {url}", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: Processing {len(tixr_urls)} Tixr URLs from {url}", self.logger_context)

            results = await self.batch_scraper.process_batch(
                tixr_urls,
                lambda u: self.tixr_client.get_event_detail_from_url(u),
                "Tixr event extraction",
            )
            tixr_events = [r for r in results if r is not None]

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
            return LaughFactoryCovinaPageData(event_list=tixr_events, tixr_urls=tixr_urls)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
