"""EventPrime platform scraper.

EventPrime is a common WordPress events plugin. Venues running it expose a
public, unauthenticated REST endpoint at
``<site>/wp-json/eventprime/v1/get_events`` that returns every event as JSON.
This generic scraper fetches that endpoint and maps each upcoming event to a
Show — no per-venue code needed.

Wiring (``scraping_sources``): set ``scraper_key='eventprime'``,
``platform='custom'``, and ``source_url`` to the full ``get_events`` endpoint
(``https://<site>/wp-json/eventprime/v1/get_events``). Optional
``metadata.comedy_filter=true`` for mixed-use venues.
"""

from __future__ import annotations

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.eventprime.data import EventPrimePageData
from laughtrack.scrapers.implementations.eventprime.extractor import (
    extract_eventprime_events,
)
from laughtrack.scrapers.implementations.eventprime.transformer import (
    EventPrimeTransformer,
)
from laughtrack.scrapers.utils.comedy_filter import is_comedy_filter_enabled
from laughtrack.shared.types import ScrapingTarget


class EventPrimeScraper(BaseScraper):
    """Scraper for WordPress venues running the EventPrime events plugin."""

    key = "eventprime"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EventPrimeTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        source_url = self.club.scraping_url
        if not source_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no EventPrime source_url configured "
                f"(expected the /wp-json/eventprime/v1/get_events endpoint)",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(source_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[EventPrimePageData]:
        try:
            payload = await self.fetch_json(str(target))
            if not payload:
                self._warn_empty_extraction(str(target), subject="payload", payload=payload)
                return None

            events = extract_eventprime_events(
                payload,
                timezone=self.club.timezone,
                comedy_filter=is_comedy_filter_enabled(self.club.source_metadata),
            )
            if not events:
                count = payload.get("count") if isinstance(payload, dict) else None
                self._warn_empty_extraction(
                    str(target), subject="events", n_items=count
                )
                return None
            return EventPrimePageData(events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error fetching EventPrime events from {target}: {e}",
                self.logger_context,
            )
            return None
