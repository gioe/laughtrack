"""
Laugh Factory Reno scraper implementation.

Laugh Factory Reno (laughfactory.com/reno) uses Tixologi (partner ID 690) as its
ticketing platform.  Unlike most venues, Tixologi does not expose a public events
API — shows are server-rendered as `.show-sec.jokes` HTML divs on the Laugh Factory
CMS page.  The scraper:

1. Fetches the CMS page (www.laughfactory.com/reno) via TixologiClient
2. Parses `.show-sec.jokes` divs into TixologiEvent objects via the extractor
3. Returns a LaughFactoryRenoPageData for the transformation pipeline
"""

from typing import Optional

from laughtrack.core.clients.tixologi import TixologiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import LaughFactoryRenoEventExtractor
from .page_data import LaughFactoryRenoPageData
from .transformer import LaughFactoryRenoEventTransformer


class LaughFactoryRenoScraper(BaseScraper):
    """
    Scraper for Laugh Factory Reno comedy club.

    Fetches the Laugh Factory Reno CMS page and parses server-rendered show
    listings into TixologiEvent objects for the transformation pipeline.
    """

    key = "laugh_factory_reno"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LaughFactoryRenoEventTransformer(club))
        self.tixologi_client = TixologiClient(club)

    async def get_data(self, url: str) -> Optional[LaughFactoryRenoPageData]:
        """
        Fetch the Laugh Factory Reno CMS page and extract TixologiEvent objects.

        Args:
            url: The CMS page URL (https://www.laughfactory.com/reno)

        Returns:
            LaughFactoryRenoPageData containing TixologiEvent objects,
            or None if no shows are found.
        """
        try:
            html_content = await self.tixologi_client.fetch_shows_page(url)
            if not html_content:
                Logger.info(f"No HTML content returned from {url}", self.logger_context)
                return None

            events = LaughFactoryRenoEventExtractor.extract_shows(
                html_content,
                club_id=self.club.id,
                timezone=self.club.timezone,
            )

            if not events:
                Logger.info(f"No shows found on {url}", self.logger_context)
                return None

            Logger.info(
                f"Extracted {len(events)} shows from {url}",
                self.logger_context,
            )
            return LaughFactoryRenoPageData(event_list=events)

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
