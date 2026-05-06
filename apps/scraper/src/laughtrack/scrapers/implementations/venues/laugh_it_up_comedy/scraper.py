"""
LAUGH IT UP COMEDY CLUB scraper.

LAUGH IT UP COMEDY CLUB (laughitupcomedy.com) migrated from the WordPress
TicketWeb plugin to a Punchup-powered Next.js calendar. Show data is embedded
in React Query hydration state on the public calendar page.
"""

import dataclasses
from typing import Optional

from laughtrack.core.clients.punchup.extractor import PunchupExtractor
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import LaughItUpComedyPageData, LaughItUpComedyShow
from .transformer import LaughItUpComedyEventTransformer


class LaughItUpComedyScraper(BaseScraper):
    """
    Scraper for LAUGH IT UP COMEDY CLUB (Punchup platform, Next.js App Router).

    Fetches the calendar page and extracts shows from Punchup hydration data.
    """

    key = "laugh_it_up_comedy"

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LaughItUpComedyEventTransformer(club))

    async def get_data(self, url: str) -> Optional[LaughItUpComedyPageData]:
        """
        Fetch the calendar page and extract events from Punchup hydration data.

        Args:
            url: The calendar page URL from the active scraping source.

        Returns:
            LaughItUpComedyPageData with extracted shows, or None if none found.
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

            punchup_shows = PunchupExtractor.extract_shows(html_content)
            if not punchup_shows:
                Logger.warn(
                    f"{self._log_prefix}: no shows found in Punchup hydration data at {url} -- "
                    "site may have changed structure or have no upcoming events",
                    self.logger_context,
                )
                return None

            shows = [
                LaughItUpComedyShow(**{f.name: getattr(s, f.name) for f in dataclasses.fields(s)})
                for s in punchup_shows
            ]
            Logger.info(
                f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
                self.logger_context,
            )
            return LaughItUpComedyPageData(event_list=shows)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching data from {url}: {e}",
                self.logger_context,
            )
            return None
