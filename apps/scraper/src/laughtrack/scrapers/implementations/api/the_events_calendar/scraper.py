"""Generic scraper for venues using The Events Calendar (Tribe) WordPress plugin.

"The Events Calendar" is a widely-used WordPress plugin that exposes a public
REST API at:
  /wp-json/tribe/events/v1/events

This is a generic, reusable scraper: any venue running the plugin can be
onboarded by pointing its scraping_sources.source_url at the events endpoint
above — no per-venue code required.

Pipeline:
  1. collect_scraping_targets() → returns [scraping_url] (default base behaviour)
  2. get_data(url)              → fetches all API pages, extracts TribeEvents
  3. transformation_pipeline    → TribeEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TribeEventsPageData
from .extractor import TribeEventExtractor
from .transformer import TribeEventTransformer

_PER_PAGE = 50
_MAX_PAGES = 20


class TheEventsCalendarScraper(BaseScraper):
    """Scraper for venues using The Events Calendar (Tribe) REST API."""

    key = "the_events_calendar"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TribeEventTransformer(club))

    async def get_data(self, url: str) -> Optional[TribeEventsPageData]:
        """
        Fetch all pages from a Tribe Events REST API.

        Args:
            url: The Tribe Events API base URL (from club.scraping_url)

        Returns:
            TribeEventsPageData containing all TribeEvent objects, or None
        """
        try:
            all_events = []
            page = 1
            while True:
                api_url = f"{url}?per_page={_PER_PAGE}&status=publish&page={page}"
                response = await self.fetch_json(api_url)
                if not response:
                    break

                events = TribeEventExtractor.extract_events(response)
                all_events.extend(events)

                total_pages = TribeEventExtractor.get_total_pages(response)
                Logger.debug(
                    f"{self._log_prefix}: page {page}/{total_pages}, "
                    f"{len(events)} events",
                    self.logger_context,
                )
                if page >= total_pages:
                    break
                if page >= _MAX_PAGES:
                    Logger.warn(
                        f"{self._log_prefix}: reached max pages ({_MAX_PAGES}), stopping early",
                        self.logger_context,
                    )
                    break
                page += 1

            if not all_events:
                self._warn_empty_extraction(url, extra={"pages_fetched": page})
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(all_events)} events total",
                self.logger_context,
            )
            return TribeEventsPageData(event_list=all_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: error fetching events: {e}", self.logger_context)
            return None
