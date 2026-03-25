"""
HAHA Comedy Club scraper implementation.

HAHA Comedy Club (North Hollywood, CA) lists shows at hahacomedyclub.com/calendar.
Each show links to a Tixr short URL (tixr.com/e/{id}). This scraper:

1. Fetches the calendar page
2. Extracts all tixr.com/e/{id} short URLs
3. Fetches full event details from each Tixr page via JSON-LD structured data
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.foundation.utilities.url import URLUtils

from .extractor import HaHaComedyClubExtractor
from .page_data import HaHaComedyClubPageData
from .transformer import HaHaComedyClubEventTransformer


class HaHaComedyClubScraper(BaseScraper):
    """
    Scraper for HAHA Comedy Club (hahacomedyclub.com).

    The calendar page embeds Tixr short-form ticket links (tixr.com/e/{id}).
    This scraper extracts those links and resolves each to a full TixrEvent
    via JSON-LD structured data on the Tixr event page.
    """

    key = "haha_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(HaHaComedyClubEventTransformer(club))
        self.tixr_client = create_monitored_tixr_client(club)
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the single calendar page URL."""
        url = self.club.scraping_url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return [url]

    async def get_data(self, url: str) -> Optional[HaHaComedyClubPageData]:
        """
        Fetch the HAHA calendar page, extract Tixr short URLs, and resolve
        each to a TixrEvent via the Tixr page JSON-LD data.

        Args:
            url: HAHA Comedy Club calendar page URL

        Returns:
            HaHaComedyClubPageData containing TixrEvent objects, or None if no events found
        """
        try:
            html_content = await self.fetch_html(URLUtils.normalize_url(url))
            tixr_urls = HaHaComedyClubExtractor.extract_tixr_urls(html_content)

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
            return HaHaComedyClubPageData(event_list=tixr_events)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
