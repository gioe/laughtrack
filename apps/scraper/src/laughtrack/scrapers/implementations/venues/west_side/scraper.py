"""
West Side Comedy Club scraper.

West Side Comedy Club's site (westsidecomedyclub.com) is built on the Punchup platform
using Next.js App Router. Show data is not exposed as JSON-LD but is embedded in
React Query hydration state inside self.__next_f.push() streaming script tags.

This scraper fetches the calendar page, parses the Punchup/Next.js hydration data,
and extracts upcoming shows with lineup and ticket info.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import WestSidePageData
from .extractor import WestSideExtractor
from .transformer import WestSideEventTransformer


class WestSideScraper(BaseScraper):
    """
    Scraper for West Side Comedy Club (Punchup platform, Next.js App Router).

    Fetches the calendar page and extracts shows from the React Query
    hydration state embedded in self.__next_f.push() streaming script tags.
    """

    key = "west_side"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformer = WestSideEventTransformer(club)

    async def get_data(self, url: str) -> Optional[WestSidePageData]:
        """
        Fetch the calendar page and extract shows from the Punchup hydration data.

        Args:
            url: The calendar page URL (from club.scraping_url).

        Returns:
            WestSidePageData with extracted shows, or None if none found.
        """
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)
            if not html_content:
                Logger.warn(f"West Side: received empty HTML from {url}", self.logger_context)
                return None

            shows = WestSideExtractor.extract_shows(html_content)
            if not shows:
                Logger.warn(
                    f"West Side: no shows found in Punchup hydration data at {url} — "
                    "site may have changed structure or have no upcoming events",
                    self.logger_context,
                )
                return None

            Logger.info(f"West Side: extracted {len(shows)} shows from {url}", self.logger_context)
            return WestSidePageData(event_list=shows)

        except Exception as e:
            Logger.error(f"West Side: error fetching data from {url}: {e}", self.logger_context)
            return None
