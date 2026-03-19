"""
Comedy Key West scraper.

Comedy Key West (comedykeywest.com) is built on the Punchup platform using
Next.js App Router. Show data is not exposed as JSON-LD but is embedded in
React Query hydration state inside self.__next_f.push() streaming script tags.

The site uses Tixologi for ticketing; each show has a tixologi_event_id and a
ticket link of the form https://event.tixologi.com/event/<id>/tickets.

Fetch strategy:
- The Punchup RSC stream is server-side rendered and accessible via a plain HTTP
  GET (no browser execution required). curl_cffi impersonation alone is sufficient.
- Show data lives in the "venuePageCarousel" → "items" key of the RSC payload.
- The PunchupExtractor handles both direct JSON and JS-escaped push([1, "..."]) formats.
"""

from typing import List, Optional

from laughtrack.core.clients.punchup.extractor import PunchupExtractor, PunchupShow
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import ComedyKeyWestPageData


class ComedyKeyWestEventTransformer(DataTransformer[PunchupShow]):
    """Transforms PunchupShow objects into Show entities for Comedy Key West."""


class ComedyKeyWestScraper(BaseScraper):
    """
    Scraper for Comedy Key West (Punchup platform, Next.js App Router).

    Fetches the shows page and extracts events from the React Query
    hydration state embedded in self.__next_f.push() streaming script tags.
    Uses Tixologi for ticket purchase links.
    """

    key = "comedy_key_west"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformer = ComedyKeyWestEventTransformer(club)

    async def get_data(self, url: str) -> Optional[ComedyKeyWestPageData]:
        """
        Fetch the shows page and extract events from the Punchup hydration data.

        Args:
            url: The shows page URL (from club.scraping_url).

        Returns:
            ComedyKeyWestPageData with extracted shows, or None if none found.
        """
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)
            if not html_content:
                Logger.warn(
                    f"Comedy Key West: received empty HTML from {url}",
                    self.logger_context,
                )
                return None

            shows = PunchupExtractor.extract_shows(html_content)
            if not shows:
                Logger.warn(
                    f"Comedy Key West: no shows found in Punchup hydration data at {url} — "
                    "site may have changed structure or have no upcoming events",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"Comedy Key West: extracted {len(shows)} shows from {url}",
                self.logger_context,
            )
            return ComedyKeyWestPageData(event_list=shows)

        except Exception as e:
            Logger.error(
                f"Comedy Key West: error fetching data from {url}: {e}",
                self.logger_context,
            )
            return None
