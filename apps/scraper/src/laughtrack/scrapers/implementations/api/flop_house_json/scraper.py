"""Scraper for Flop House static venue/event JSON feeds."""

import asyncio
from collections import defaultdict
from typing import Dict, List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.flop_house_json.data import (
    FlopHouseJsonPageData,
)
from laughtrack.scrapers.implementations.api.flop_house_json.extractor import (
    FlopHouseJsonExtractor,
)
from laughtrack.scrapers.implementations.api.flop_house_json.transformer import (
    FlopHouseJsonEventTransformer,
)
from .pricing import eventbrite_id, extract_admission

_DETAIL_TIMEOUT = 10
_DETAIL_BUDGET = 30
_DETAIL_CONCURRENCY = 4


class FlopHouseJsonScraper(BaseScraper):
    """Scrape Flop House's `/venues.json` and `/venues/{id}_events.json` feeds."""

    key = "flop_house_json"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.base_domain = self._base_domain(club.scraping_url)
        self.venues_by_id: Dict[str, dict] = {}
        self.transformation_pipeline.register_transformer(FlopHouseJsonEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Fetch venues.json and return each venue's event-feed URL."""
        venues_url = f"{self.base_domain}/venues.json"
        try:
            response = await self.fetch_json(venues_url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch {venues_url}: {e}", self.logger_context)
            return []

        if not isinstance(response, list):
            return []

        self.venues_by_id = {
            str(venue["id"]): venue
            for venue in response
            if isinstance(venue, dict) and venue.get("id")
        }
        return [
            f"{self.base_domain}/venues/{venue_id}_events.json"
            for venue_id in self.venues_by_id
        ]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """Fetch one venue event feed and return parsed events."""
        try:
            response = await self.fetch_json(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        events = FlopHouseJsonExtractor.extract_events(
            response,
            venues_by_id=self.venues_by_id,
        )
        if not events:
            Logger.info(f"{self._log_prefix}: no events parsed from {url}", self.logger_context)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} Flop House JSON event(s)",
            self.logger_context,
        )
        await self._enrich_admissions(events)
        return FlopHouseJsonPageData(event_list=events)

    async def _enrich_admissions(self, events) -> None:
        groups = defaultdict(list)
        for event in events:
            identity = eventbrite_id(event.show_page_url)
            if identity:
                groups[identity].append(event)
        # Per invocation, so no asyncio primitive crosses the per-club loops.
        semaphore = asyncio.Semaphore(_DETAIL_CONCURRENCY)

        async def enrich(identity, group):
            async with semaphore:
                try:
                    url = f"https://www.eventbrite.com/e/tickets-{identity}"
                    html = await asyncio.wait_for(
                        self.fetch_html(url, skip_js_fallback=True), _DETAIL_TIMEOUT
                    )
                    for event in group:
                        admission = extract_admission(html, event)
                        if admission is not None:
                            event.admission_price, event.admission_label = admission
                except Exception as exc:
                    Logger.warn(f"{self._log_prefix}: optional Eventbrite price fetch failed for {identity}: {exc}")

        try:
            await asyncio.wait_for(
                asyncio.gather(*(enrich(identity, group) for identity, group in groups.items())), _DETAIL_BUDGET
            )
        except asyncio.TimeoutError:
            Logger.warn(f"{self._log_prefix}: Eventbrite price budget exhausted; retaining feed performances")

    @staticmethod
    def _base_domain(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else url.rstrip("/")
