"""
The Auricle scraper (Canton, OH).

The Auricle is primarily a live-music/variety venue that also hosts a recurring
comedy open mic. It runs on Square Online and surfaces its event calendar from
its Facebook Page via a SociableKit widget, backed by a public JSON feed:

  GET https://data.accentapi.com/feed/<widgetId>.json  → {"events": [...]}

The feed URL (carrying the venue's widget id) is the club's scraping_url. The
extractor keeps only comedy events (e.g. "Comedy Open Mic"); music, drag,
karaoke, etc. are excluded so the venue contributes only its comedy programming.

Pipeline:
  1. collect_scraping_targets() → [accentapi feed URL]
  2. get_data(url)             → fetch JSON, extract comedy events
  3. transformation_pipeline   → TheAuricleEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TheAuriclePageData
from .extractor import TheAuricleEventExtractor
from .transformer import TheAuricleEventTransformer


class TheAuricleScraper(BaseScraper):
    """Scraper for The Auricle (Canton, OH) via its SociableKit/accentapi feed."""

    key = "the_auricle"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            TheAuricleEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the accentapi feed URL from the club's scraping_url."""
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[TheAuriclePageData]:
        """Fetch the accentapi JSON feed and extract comedy events."""
        payload = await self.fetch_json(url)
        if not payload:
            Logger.warn(
                f"{self._log_prefix}: empty accentapi feed response",
                self.logger_context,
            )
            return None

        events = TheAuricleEventExtractor.extract_shows(payload, self.logger_context)
        if not events:
            self._warn_empty_extraction(url, note="no comedy events in accentapi feed")
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} comedy event(s)",
            self.logger_context,
        )
        return TheAuriclePageData(event_list=events)
