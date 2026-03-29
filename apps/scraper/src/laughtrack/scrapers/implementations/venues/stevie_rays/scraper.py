"""
Stevie Ray's Improv Company scraper (Chanhassen, MN).

Stevie Ray's performs at Chanhassen Dinner Theatres and sells tickets through
the venue's proprietary AudienceView/Theatre Manager ticketing system. The show
listing page requires JavaScript execution — curl_cffi returns the page shell
without event data, so this scraper uses PlaywrightBrowser directly:

  https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays

Each upcoming show is listed as a div.result-box-item with:
- div.item-name   — "Stevie Ray's Comedy Cabaret"
- span.start-date — "Friday, April 03, 2026 @ 7:30 PM"

No per-event ticket URLs exist (Buy buttons open a JS modal). The listing page
URL is used as the ticket URL for all shows.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML via Playwright, extract StevieRaysEvents
  3. transformation_pipeline    → StevieRaysEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import StevieRaysPageData
from .extractor import StevieRaysExtractor
from .transformer import StevieRaysEventTransformer


class StevieRaysScraper(BaseScraper):
    """Scraper for Stevie Ray's Improv Company (Chanhassen, MN)."""

    key = "stevie_rays"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            StevieRaysEventTransformer(club)
        )

    async def _fetch_html_with_js(self, url: str) -> Optional[str]:
        """Fetch page HTML using PlaywrightBrowser (required for JS-rendered content)."""
        try:
            from laughtrack.foundation.infrastructure.http.playwright_browser import (
                PlaywrightBrowser,
            )
            browser = PlaywrightBrowser()
            return await browser.fetch_html(url)
        except Exception as e:
            Logger.warn(
                f"StevieRaysScraper: Playwright fetch failed for {url}: {e}",
                self.logger_context,
            )
            return None

    async def get_data(self, url: str) -> Optional[StevieRaysPageData]:
        """
        Fetch the ticketing listing page via Playwright and extract all upcoming events.

        The tickets.chanhassendt.com page requires JavaScript execution — curl_cffi
        returns only the page shell without event rows, so Playwright is used directly.

        Args:
            url: The ticketing listing URL (from club.scraping_url).

        Returns:
            StevieRaysPageData with extracted events, or None on failure.
        """
        try:
            html = await self._fetch_html_with_js(url)
            if not html:
                Logger.warn(
                    f"StevieRaysScraper: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = StevieRaysExtractor.extract_events(html, listing_url=url)
            if not events:
                Logger.info(
                    f"StevieRaysScraper: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"StevieRaysScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return StevieRaysPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"StevieRaysScraper: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
