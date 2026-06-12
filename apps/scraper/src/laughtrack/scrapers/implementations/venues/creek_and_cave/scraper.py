"""
Creek and The Cave scraper following the 5-component architecture.

The Creek and The Cave (Austin, TX) rebuilt its site on the Punchup platform
(Next.js App Router). The old creekandcaveevents.s3.amazonaws.com monthly JSON
bucket no longer exists (NoSuchBucket); show data now ships server-rendered in
the /calendar page as React state inside self.__next_f.push() streaming script
chunks. Ticket links are Tixologi URLs (https://event.tixologi.com/event/<id>/tickets)
instead of the old Showclix listing_url values.

Fetch strategy:
- The page is plain-HTTP accessible (no bot blocking observed); fetched via
  fetch_html_bare() like the other Punchup venues (west_side, comedy_key_west).
- /calendar embeds the full upcoming-event list (~200 rows); the homepage only
  embeds ~25, so the calendar URL is the scraping target.

Pipeline:
  1. collect_scraping_targets() → [/calendar URL]
  2. get_data(url)              → fetches HTML, extracts CreekAndCaveShow objects
  3. transformation_pipeline    → CreekAndCaveShow.to_show() → Show objects
"""

import asyncio
from typing import List, Optional

from laughtrack.core.clients.tixologi import TixologiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import CreekAndCavePageData, CreekAndCaveShow
from .extractor import CreekAndCaveEventExtractor
from .transformer import CreekAndCaveEventTransformer

# Fixed calendar URL: the DB scraping_sources row may still point at the
# retired S3 feed (or the venue's old domain — thecreekandthecave.com 301s
# here), so the target is pinned the same way the old S3 base URL was.
_CALENDAR_URL = "https://www.creekandcave.com/calendar"


class CreekAndCaveScraper(BaseScraper):
    """Scraper for The Creek and The Cave (Austin, TX) via Punchup calendar page."""

    key = "creek_and_cave"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.tixologi_client = TixologiClient(club)
        self.transformation_pipeline.register_transformer(
            CreekAndCaveEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the single /calendar page URL (full upcoming-event embed)."""
        Logger.info(
            f"{self._log_prefix}: using calendar target {_CALENDAR_URL}",
            self.logger_context,
        )
        return [_CALENDAR_URL]

    async def get_data(self, url: str) -> Optional[CreekAndCavePageData]:
        """Fetch the calendar page and extract shows from the embedded React state.

        Args:
            url: The calendar page URL (from collect_scraping_targets()).

        Returns:
            :class:`CreekAndCavePageData` with extracted shows, or ``None``
            when the page is unavailable or contains no parseable events.
        """
        # Fetch errors deliberately propagate (no broad try/except): the
        # BaseScraper retry/diagnostics layer records them as fetch_failed,
        # matching the Gotham feed scraper. Creek is single-target, so a
        # swallowed fetch error here would misclassify a full site outage as
        # an empty calendar. Extraction-level errors are already contained
        # inside CreekAndCaveEventExtractor.extract_shows.
        html_content = await self.fetch_html_bare(url)
        if not html_content:
            self._warn_empty_extraction(url, subject="html", html=html_content)
            return None

        shows = CreekAndCaveEventExtractor.extract_shows(html_content)
        if not shows:
            self._warn_empty_extraction(
                url,
                html=html_content,
                note="site may have changed structure or have no upcoming events",
            )
            return None

        shows = await self._enrich_tixologi_tickets(shows)

        Logger.info(
            f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
            self.logger_context,
        )
        return CreekAndCavePageData(event_list=shows)

    async def _enrich_tixologi_tickets(
        self, shows: List[CreekAndCaveShow]
    ) -> List[CreekAndCaveShow]:
        """Attach Tixologi ticket-type payloads to shows before transformation.

        Mirrors the west_side enrichment (TASK-2840): each show's
        tixologi_event_id is resolved against the public no-auth
        api-v2.tixologi.com endpoint so PunchupShow._build_tickets emits
        priced tickets from ticket_types[].initial_price. Unlike west_side,
        get_data here has no outer try/except, so a per-show failure is
        contained — an enrichment error degrades that show to the priceless
        fallback ticket instead of dropping the whole calendar.
        """

        async def enrich(show: CreekAndCaveShow) -> CreekAndCaveShow:
            if not show.tixologi_event_id:
                return show
            try:
                ticket_types = await self.tixologi_client.fetch_event_ticket_types(
                    show.tixologi_event_id
                )
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: tixologi enrichment failed for event "
                    f"{show.tixologi_event_id}: {e}",
                    self.logger_context,
                )
                return show
            if not ticket_types:
                return show
            return show.with_tixologi_ticket_types(ticket_types)

        return list(await asyncio.gather(*(enrich(show) for show in shows)))
