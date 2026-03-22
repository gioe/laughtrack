"""
Laugh Boston scraper implementation.

Laugh Boston (laughboston.com) lists upcoming shows directly on its homepage
as Tixr links (tixr.com/groups/laughboston/events/*). The scraper:
1. Fetches the homepage and extracts all Tixr event URLs
2. Uses TixrClient to fetch full event details for each URL via JSON-LD parsing
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .extractor import LaughBostonEventExtractor
from .page_data import LaughBostonPageData
from .transformer import LaughBostonEventTransformer


class LaughBostonScraper(BaseScraper):
    """
    Scraper for Laugh Boston comedy club.

    Extracts Tixr event URLs from the Laugh Boston homepage, then fetches
    full event details via TixrClient's JSON-LD parsing.
    """

    key = "laugh_boston"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LaughBostonEventTransformer(club))
        self.tixr_client = create_monitored_tixr_client(club)
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

    async def get_data(self, url: str) -> Optional[LaughBostonPageData]:
        """
        Fetch the Laugh Boston homepage and extract TixrEvent objects.

        Args:
            url: The Laugh Boston homepage URL

        Returns:
            LaughBostonPageData containing TixrEvent objects, or None if no events found
        """
        try:
            html_content = await self.fetch_html(URLUtils.normalize_url(url))
            tixr_urls = LaughBostonEventExtractor.extract_tixr_urls(html_content)

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
            return LaughBostonPageData(event_list=tixr_events, tixr_urls=tixr_urls)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
