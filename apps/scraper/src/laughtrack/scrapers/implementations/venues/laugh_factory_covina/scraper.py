"""
Laugh Factory Covina scraper implementation.

Laugh Factory Covina (laughfactory.com/covina) lists upcoming shows on their
Tixr group page (tixr.com/groups/laughfactorycovina). The scraper:
1. Fetches the Tixr group page using DataDome-safe bare curl_cffi fetch
2. Extracts all Tixr event URLs for the laughfactorycovina group
3. Uses TixrClient to fetch full event details for each URL via JSON-LD parsing
"""

from typing import Optional

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

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LaughFactoryCovinaEventTransformer(club))
        self.tixr_client = create_monitored_tixr_client(club)
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

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
                Logger.info(f"No HTML content returned from {url}", self.logger_context)
                return None

            tixr_urls = LaughFactoryCovinaEventExtractor.extract_tixr_urls(html_content)

            if not tixr_urls:
                Logger.info(f"No Tixr URLs found on {url}", self.logger_context)
                return None

            Logger.info(f"Extracted {len(tixr_urls)} Tixr URLs from {url}", self.logger_context)

            results = await self.batch_scraper.process_batch(
                tixr_urls,
                lambda u: self.tixr_client.get_event_detail_from_url(u),
                "Tixr event extraction",
            )
            tixr_events = [r for r in results if r is not None]

            if not tixr_events:
                Logger.info(
                    f"No TixrEvents returned from {len(tixr_urls)} URLs on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"Successfully processed {len(tixr_events)} TixrEvents from {len(tixr_urls)} URLs",
                self.logger_context,
            )
            return LaughFactoryCovinaPageData(event_list=tixr_events, tixr_urls=tixr_urls)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
