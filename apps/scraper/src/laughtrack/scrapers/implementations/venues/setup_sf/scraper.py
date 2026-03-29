"""
The Setup SF scraper.

The Setup SF (setupcomedy.com) is a speakeasy comedy show producer that runs
shows at The Palace Theater and The Lost Church in San Francisco. Their show
calendar is maintained in a Google Sheets spreadsheet published as CSV:

  https://docs.google.com/spreadsheets/d/e/2PACX-1v.../pub?gid=495747966&single=true&output=csv

The CSV contains columns: date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out

Each row's ticket_url links to a Squarespace commerce product page at
setupcomedy.com/tickets-3/{slug} where tickets can be purchased directly.

The scraping_url on the club row stores the full published CSV URL.
curl_cffi follows the Google Sheets 307 redirect automatically.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import SetupSFPageData
from .extractor import SetupSFExtractor
from .transformer import SetupSFEventTransformer


class SetupSFScraper(BaseScraper):
    """
    Scraper for The Setup SF — fetches shows from a published Google Sheets CSV.

    Reads club.scraping_url for the CSV endpoint. curl_cffi follows the
    Google Sheets 307 redirect to googleusercontent.com automatically.
    """

    key = "setup_sf"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SetupSFEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the Google Sheets CSV URL stored on the club row."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[SetupSFPageData]:
        """
        Fetch the Google Sheets CSV and return extracted SetupSFEvents.

        Args:
            url: The published Google Sheets CSV URL.

        Returns:
            SetupSFPageData containing upcoming events, or None if none found.
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            csv_text = await self.fetch_html(url)
            if not csv_text:
                Logger.info(f"{self.__class__.__name__} [{self._club.name}]: no response from {url}", self.logger_context)
                return None

            events = SetupSFExtractor.extract_events(csv_text)

            if not events:
                Logger.info(f"{self.__class__.__name__} [{self._club.name}]: no upcoming events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"{self.__class__.__name__} [{self._club.name}]: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SetupSFPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self.__class__.__name__} [{self._club.name}]: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
