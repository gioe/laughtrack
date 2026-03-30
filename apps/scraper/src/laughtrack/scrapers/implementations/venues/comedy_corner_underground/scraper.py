"""
The Comedy Corner Underground scraper (Minneapolis, MN).

The Comedy Corner Underground is an artist-run comedy room inside Whitey's
Old Town Saloon in NE Minneapolis. It uses the StageTime platform
(https://ccu.stageti.me) for ticketing.

StageTime is a Next.js app; all event data is embedded in the server-rendered
HTML as React Server Component (RSC) wire format payloads.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (https://ccu.stageti.me/)
  2. get_data(url):
       a. Fetch the venue listing page → extract event slugs
       b. For each slug (skipping open mics / no-advance-sales):
          - Fetch https://ccu.stageti.me/e/{slug}
          - Parse RSC payload → name, occurrences, timezone, performers, ticket URL
          - Expand into one ComedyCornerEvent per occurrence
  3. transformation_pipeline → ComedyCornerEvent.to_show() → Show objects
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_corner_underground import ComedyCornerEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyCornerPageData
from .extractor import ComedyCornerExtractor
from .transformer import ComedyCornerEventTransformer

_BASE_URL = "https://ccu.stageti.me"


class ComedyCornerScraper(BaseScraper):
    """Scraper for The Comedy Corner Underground (Minneapolis) via StageTime."""

    key = "comedy_corner_underground"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyCornerEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[ComedyCornerPageData]:
        """
        Fetch the StageTime venue listing page and then each individual event
        page to extract all upcoming show occurrences.

        Args:
            url: The StageTime venue listing URL (from club.scraping_url).

        Returns:
            ComedyCornerPageData with extracted events, or None on failure.
        """
        try:
            # Step 1: Fetch listing page to get event slugs
            listing_html = await self.fetch_html(url)
            if not listing_html:
                Logger.warn(
                    f"{self._log_prefix}: empty listing page for {url}",
                    self.logger_context,
                )
                return None

            slugs = ComedyCornerExtractor.extract_event_slugs(listing_html)
            if not slugs:
                Logger.info(
                    f"{self._log_prefix}: no event slugs found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: found {len(slugs)} event slugs on listing page",
                self.logger_context,
            )

            # Step 2: Fetch each individual event page concurrently and expand occurrences
            all_events: List[ComedyCornerEvent] = []
            semaphore = asyncio.Semaphore(5)

            async def _fetch_slug(slug: str) -> List[ComedyCornerEvent]:
                event_url = f"{_BASE_URL}/e/{slug}"
                async with semaphore:
                    event_html = await self.fetch_html(event_url)
                if not event_html:
                    Logger.warn(
                        f"{self._log_prefix}: empty response for event {slug}",
                        self.logger_context,
                    )
                    return []

                data = ComedyCornerExtractor.extract_event_data(event_html)
                if data is None:
                    Logger.warn(
                        f"{self._log_prefix}: failed to extract data for {slug}",
                        self.logger_context,
                    )
                    return []

                # Skip open mic events and events with no advance sales
                if data.get("is_open_mic") or data.get("admission_type") == "no_advance_sales":
                    Logger.debug(
                        f"{self._log_prefix}: skipping open mic / no-advance-sales event: {slug}"
                    )
                    return []

                name = data.get("name", "")
                ticket_url = data.get("ticket_url", "")
                timezone = data.get("timezone", "America/Chicago")
                performers = data.get("performers", [])
                occurrences = data.get("occurrences", [])

                if not name or not occurrences:
                    Logger.debug(
                        f"{self._log_prefix}: skipping {slug} — missing name or occurrences"
                    )
                    return []

                return [
                    ComedyCornerEvent(
                        title=name,
                        start_time_utc=start_time_utc,
                        timezone=timezone,
                        ticket_url=ticket_url,
                        performers=list(performers),
                    )
                    for start_time_utc in occurrences
                ]

            slug_results = await asyncio.gather(*(_fetch_slug(slug) for slug in slugs))
            for events in slug_results:
                all_events.extend(events)

            if not all_events:
                Logger.info(
                    f"{self._log_prefix}: no ticketed events found",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(all_events)} show occurrences",
                self.logger_context,
            )
            return ComedyCornerPageData(event_list=all_events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
