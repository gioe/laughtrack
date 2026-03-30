"""
Creek and The Cave scraper following the 5-component architecture.

The Creek and The Cave (Austin, TX) publishes event data as monthly JSON files
hosted on an S3 bucket:

  https://creekandcaveevents.s3.amazonaws.com/events/month/YYYY-MM.json

Each month's file is a dict keyed by day-of-month (as a string), where each
value is a list of event objects.  Every event object contains a ``shows``
array with individual time slots (7 pm, 9 pm, etc.).  One
:class:`CreekAndCaveEvent` is created per time slot.

Ticket links are Showclix URLs already present in the S3 data.

Pipeline:
  1. collect_scraping_targets() → monthly S3 JSON URLs (current + next N months)
  2. get_data(url)              → fetches JSON, extracts CreekAndCaveEvent objects
  3. transformation_pipeline    → CreekAndCaveEvent.to_show() → Show objects
"""

from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import CreekAndCavePageData
from .extractor import CreekAndCaveEventExtractor
from .transformer import CreekAndCaveEventTransformer

_S3_BASE_URL = "https://creekandcaveevents.s3.amazonaws.com/events/month/"
_NUM_MONTHS = 6


class CreekAndCaveScraper(BaseScraper):
    """Scraper for The Creek and The Cave (Austin, TX) via S3 monthly JSON."""

    key = "creek_and_cave"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            CreekAndCaveEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Generate S3 monthly JSON URLs for the current and next N months."""
        now = datetime.now()
        targets: List[str] = []
        for i in range(_NUM_MONTHS):
            year = now.year
            month = now.month + i
            while month > 12:
                month -= 12
                year += 1
            targets.append(f"{_S3_BASE_URL}{year:04d}-{month:02d}.json")

        Logger.info(
            f"{self._log_prefix}: generated {len(targets)} monthly S3 targets",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[CreekAndCavePageData]:
        """Fetch and parse one monthly S3 JSON file.

        Args:
            url: Monthly S3 JSON URL (e.g., ``.../2026-04.json``).

        Returns:
            :class:`CreekAndCavePageData` with extracted show slots, or ``None``
            when the file is unavailable (expected for future months with no events)
            or contains no events.
        """
        try:
            data = await self.fetch_json(url)
            if not data:
                Logger.info(
                    f"{self._log_prefix}: no data at {url} (future month or empty)",
                    self.logger_context,
                )
                return None

            events = CreekAndCaveEventExtractor.parse_monthly_json(
                data, self.logger_context
            )
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events parsed from {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: {len(events)} show slots from {url}",
                self.logger_context,
            )
            return CreekAndCavePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
