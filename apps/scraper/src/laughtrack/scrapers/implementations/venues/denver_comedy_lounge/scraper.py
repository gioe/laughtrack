"""
Denver Comedy Lounge scraper (RiNo Arts District, Denver, CO).

The venue runs a custom Next.js site (Vercel + Sanity CMS) and sells every show
through on-site Stripe checkout — there is no ticketing-platform feed (Eventbrite
is used only for occasional guest events). The venue-owned ``/shows`` page
server-renders a schema.org ``ItemList`` of upcoming shows; each item carries a
title plus a detail URL whose slug encodes the date and start time
(e.g. ``/shows/friday-7pm-2026-06-26``).

Pipeline:
  1. collect_scraping_targets() -> [/shows URL from scraping_sources.source_url]
  2. get_data(url)              -> fetch HTML, extract DenverComedyLoungeShow rows
  3. transformation_pipeline    -> DenverComedyLoungeShow.to_show() -> Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DenverComedyLoungePageData
from .extractor import DenverComedyLoungeExtractor
from .transformer import DenverComedyLoungeTransformer

# Canonical upcoming-shows listing; used when the source row has no source_url.
_SHOWS_URL = "https://denvercomedylounge.com/shows"


class DenverComedyLoungeScraper(BaseScraper):
    """Scraper for Denver Comedy Lounge via its venue-owned /shows ItemList page."""

    key = "denver_comedy_lounge"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            DenverComedyLoungeTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the single /shows listing page (full upcoming-show ItemList)."""
        return [self.club.scraping_url or _SHOWS_URL]

    async def get_data(self, url: str) -> Optional[DenverComedyLoungePageData]:
        """Fetch the /shows page and extract its ItemList into show rows."""
        html_content = await self.fetch_html(url)
        if not html_content:
            self._warn_empty_extraction(url, subject="html", html=html_content)
            return None

        shows = DenverComedyLoungeExtractor.extract_shows(html_content)
        if not shows:
            self._warn_empty_extraction(
                url,
                html=html_content,
                note="no parseable ItemList shows; site structure may have changed",
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
            self.logger_context,
        )
        return DenverComedyLoungePageData(event_list=shows)
