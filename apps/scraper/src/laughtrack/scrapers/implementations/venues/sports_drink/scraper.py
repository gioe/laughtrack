"""
Sports Drink scraper (New Orleans, LA).

Sports Drink (1042 Toledano St) is a hybrid café/comedy club that sells
tickets through OpenDate. All upcoming shows are listed on a single
server-rendered page with per_page parameter:

  https://app.opendate.io/v/sports-drink-1939?per_page=500

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (single page)
  2. get_data(url)              → fetch HTML, extract SportsDrinkEvents
  3. transformation_pipeline    → SportsDrinkEvent.to_show() → Show objects

Ticket prices (TASK-2839): the listing page renders no price strings, but each
card's detail page (event_url) embeds schema.org JSON-LD with offers.price.
get_data dispatches every distinct detail URL via asyncio.gather; the shared
rate limiter serializes app.opendate.io at its default 1 req/s, so the ~143
extra fetches add about 2.5 minutes to this venue's scrape — acceptable for a
nightly job, and memoization per run means a get_data retry refetches only
failures, never successes.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.base.detail_price_mixin import DetailPagePriceMixin

from .data import SportsDrinkPageData
from .extractor import SportsDrinkExtractor
from .transformer import SportsDrinkEventTransformer


class SportsDrinkScraper(DetailPagePriceMixin, BaseScraper):
    """Scraper for Sports Drink (New Orleans) via OpenDate.

    Detail-page prices are attached from each event's OpenDate page JSON-LD
    via DetailPagePriceMixin.
    """

    key = "sports_drink"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            SportsDrinkEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[SportsDrinkPageData]:
        """
        Fetch the OpenDate listing page and extract all upcoming events.

        Args:
            url: The OpenDate venue listing URL (from club.scraping_url).

        Returns:
            SportsDrinkPageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = SportsDrinkExtractor.extract_events(html)
            if not events:
                self._warn_empty_extraction(url, html=html)
                return None

            await self._attach_detail_page_prices(
                events, lambda event: event.event_url or None
            )

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SportsDrinkPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
