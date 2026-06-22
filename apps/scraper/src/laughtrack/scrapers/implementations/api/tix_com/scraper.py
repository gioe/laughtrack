"""Tix.com (tix.com) ticketing-platform scraper.

Reads a venue's Tix.com organization id from its public ticket-sales URL
(``https://www.tix.com/ticket-sales/<slug>/<org_id>``) and fetches that org's
on-sale events from the anonymous JSON endpoint
``https://www.tix.com/api_ots/onlinesales/events/organization/<org_id>``.

Mixed-use Tix.com venues (community theaters running a recurring comedy series
among musicals/plays) opt into comedy isolation via
``scraping_sources.metadata.comedy_filter`` (same mechanism as etix / seatengine /
academy_of_music).

  source_url (club.scraping_url): https://www.tix.com/ticket-sales/playhouseonpark/2704
"""

import asyncio
import re
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

from .data import TixComEvent, TixComPageData
from .extractor import TixComExtractor
from .transformer import TixComEventTransformer

_API_URL = "https://www.tix.com/api_ots/onlinesales/events/organization/{org_id}"
_ORG_ID_RE = re.compile(r"/(\d+)(?:/|$)")


class TixComScraper(BaseScraper):
    """Generic scraper for venues that sell tickets through Tix.com."""

    key = "tix_com"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TixComEventTransformer(club))
        self._org_id = self._extract_org_id()
        self._ticket_base = (self.club.scraping_url or "").rstrip("/")
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None

    def _extract_org_id(self) -> Optional[str]:
        """Pull the numeric organization id from the public ticket-sales URL."""
        matches = _ORG_ID_RE.findall(self.club.scraping_url or "")
        return matches[-1] if matches else None

    def validate_configuration(self) -> bool:
        if not self._org_id:
            Logger.error(
                f"{self._log_prefix}: could not extract a Tix.com org id from scraping_url "
                f"{self.club.scraping_url!r}",
                self.logger_context,
            )
            return False
        return True

    async def collect_scraping_targets(self) -> List[str]:
        return [_API_URL.format(org_id=self._org_id)]

    async def get_data(self, url: str) -> Optional[TixComPageData]:
        response = await self.fetch_json(url)
        payload = (response or {}).get("payload") if isinstance(response, dict) else None
        if not payload:
            self._warn_empty_extraction(url, subject="data", payload=response)
            return None

        events = TixComExtractor.extract_events(
            payload, ticket_base_url=self._ticket_base, tz=self.club.timezone or "America/New_York"
        )
        if self._comedy_filter:
            events = await self._filter_comedy(events)
        if not events:
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} event(s) from {url}",
            self.logger_context,
        )
        return TixComPageData(event_list=events)

    async def _filter_comedy(self, events: List[TixComEvent]) -> List[TixComEvent]:
        """Keep only comedy-titled events (opt-in, mirrors etix/seatengine)."""
        titles = [e.title for e in events]
        descriptions = {e.title: e.description for e in events if e.title}
        loop = asyncio.get_running_loop()
        comedy_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                titles,
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                descriptions=descriptions,
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
