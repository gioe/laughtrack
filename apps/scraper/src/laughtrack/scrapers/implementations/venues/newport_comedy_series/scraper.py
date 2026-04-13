"""
Newport Comedy Series scraper.

Newport Comedy Series (formerly Southcoast Comedy Series) is a comedy production
company in Newport, Rhode Island. Their site (newportcomedyseries.punchup.live) is
built on the Punchup platform using Next.js App Router. Show data is embedded in
React Query hydration state inside self.__next_f.push() streaming script tags.

This scraper fetches the venue page, parses the Punchup/Next.js hydration data,
and extracts upcoming shows with lineup and ticket info.
"""

from typing import Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import NewportComedySeriesPageData
from .extractor import NewportComedySeriesExtractor
from .transformer import NewportComedySeriesEventTransformer


class NewportComedySeriesScraper(BaseScraper):
    """
    Scraper for Newport Comedy Series (Punchup platform, Next.js App Router).

    Fetches the venue page and extracts shows from the React Query
    hydration state embedded in self.__next_f.push() streaming script tags.
    """

    key = "newport_comedy_series"

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            NewportComedySeriesEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[NewportComedySeriesPageData]:
        """
        Fetch the venue page and extract shows from the Punchup hydration data.

        Args:
            url: The venue page URL (from club.scraping_url).

        Returns:
            NewportComedySeriesPageData with extracted shows, or None if none found.
        """
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html_bare(normalized_url)
            if not html_content:
                Logger.warn(
                    f"{self._log_prefix}: received empty HTML from {url}",
                    self.logger_context,
                )
                return None

            shows = NewportComedySeriesExtractor.extract_shows(html_content)
            if not shows:
                Logger.warn(
                    f"{self._log_prefix}: no shows found in Punchup hydration data at {url} — "
                    "site may have changed structure or have no upcoming events",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
                self.logger_context,
            )
            return NewportComedySeriesPageData(event_list=shows)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching data from {url}: {e}",
                self.logger_context,
            )
            return None
