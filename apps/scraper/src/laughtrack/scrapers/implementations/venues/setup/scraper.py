"""
The Setup scraper — multi-city Google Sheets CSV.

The Setup (setupcomedy.com) is a speakeasy comedy show producer that runs
shows in multiple cities (SF, LA, Seattle, Chicago, Vancouver, etc.). Their
show calendar is maintained in a single Google Sheets spreadsheet with one
tab per city, each published as CSV via a unique gid parameter:

  https://docs.google.com/spreadsheets/d/e/2PACX-1v.../pub?gid=<city_gid>&single=true&output=csv

The CSV contains columns: date,day,time,title,venue,city,ticket_url,urgency_tag,sold_out

Each city's club row stores the full published CSV URL (with the city-specific
gid) in the scraping_url field. No code changes are needed to add a new city —
just insert a club row with the correct scraping_url.

curl_cffi follows the Google Sheets 307 redirect automatically.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import SetupPageData
from .extractor import SetupExtractor
from .transformer import SetupEventTransformer


class SetupScraper(BaseScraper):
    """
    Scraper for The Setup — fetches shows from a published Google Sheets CSV.

    Reads club.scraping_url for the CSV endpoint. Each city location has its
    own gid in the URL. curl_cffi follows the Google Sheets 307 redirect to
    googleusercontent.com automatically.
    """

    key = "setup"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SetupEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the Google Sheets CSV URL stored on the club row."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[SetupPageData]:
        """
        Fetch the Google Sheets CSV and return extracted SetupEvents.

        Args:
            url: The published Google Sheets CSV URL.

        Returns:
            SetupPageData containing upcoming events, or None if none found.
        """
        try:
            await self.rate_limiter.await_if_needed(url)

            csv_text = await self.fetch_html(url)
            if not csv_text:
                Logger.info(f"{self._log_prefix}: no response from {url}", self.logger_context)
                return None

            events = SetupExtractor.extract_events(csv_text)

            if not events:
                Logger.info(f"{self._log_prefix}: no upcoming events found at {url}", self.logger_context)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SetupPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None
