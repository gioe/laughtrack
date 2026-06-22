"""Academy of Music (Northampton, MA) scraper.

A mixed-use historic theater that books A-list touring stand-up (Ilana Glazer,
David Cross, Gary Gulman, Paula Poundstone, …) among mostly music/theater. The
venue exposes its calendar through the WordPress REST ``aom_event`` custom post
type; per-event pages carry no schema.org Event JSON-LD, so this venue-specific
parser reads the REST feed directly.

Because the calendar is mostly non-comedy, the source opts into comedy isolation
via ``scraping_sources.metadata.comedy_filter`` (same mechanism as etix /
seatengine mixed-use venues).

  source_url (club.scraping_url): https://aomtheatre.com/wp-json/wp/v2/aom_event?per_page=100
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)

from .data import AcademyOfMusicEvent, AcademyOfMusicPageData
from .extractor import AcademyOfMusicExtractor
from .transformer import AcademyOfMusicEventTransformer

_DEFAULT_SOURCE_URL = "https://aomtheatre.com/wp-json/wp/v2/aom_event?per_page=100"


class AcademyOfMusicScraper(BaseScraper):
    """WordPress-REST scraper for the Academy of Music (Northampton, MA)."""

    key = "academy_of_music"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(AcademyOfMusicEventTransformer(club))
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None

    async def collect_scraping_targets(self) -> List[str]:
        return [self.club.scraping_url or _DEFAULT_SOURCE_URL]

    async def get_data(self, url: str) -> Optional[AcademyOfMusicPageData]:
        records = await self.fetch_json(url)
        if not records:
            self._warn_empty_extraction(url, subject="data", payload=records)
            return None

        events = AcademyOfMusicExtractor.extract_events(records, tz=self.club.timezone or "America/New_York")
        if self._comedy_filter:
            events = await self._filter_comedy(events)
        if not events:
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} event(s) from {url}",
            self.logger_context,
        )
        return AcademyOfMusicPageData(event_list=events)

    async def _filter_comedy(self, events: List[AcademyOfMusicEvent]) -> List[AcademyOfMusicEvent]:
        """Keep only comedy-titled events (opt-in, mirrors etix/seatengine)."""
        titles = [e.title for e in events]
        loop = asyncio.get_running_loop()
        comedy_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                titles,
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                min_popularity=resolve_min_popularity(self.club.source_metadata),
                allowlist=resolve_allowlist(self.club.source_metadata),
            ),
        )
        kept = [e for e in events if e.title in comedy_titles]
        Logger.info(
            f"{self._log_prefix}: comedy filter kept {len(kept)}/{len(events)} event(s)",
            self.logger_context,
        )
        return kept
