"""
Comedy Key West scraper.

Comedy Key West (comedykeywest.com) is built on the Punchup platform using
Next.js App Router. Show data is not exposed as JSON-LD but is embedded in
React Query hydration state inside self.__next_f.push() streaming script tags.

The site uses Tixologi for ticketing; each show has a tixologi_event_id and a
ticket link of the form https://event.tixologi.com/event/<id>/tickets. Ticket
prices (TASK-2851): each show's tixologi_event_id is resolved against the
public no-auth api-v2.tixologi.com ticket-types endpoint — the same guarded
enrichment creek_and_cave ships (TASK-2840) — so PunchupShow._build_tickets
emits per-tier priced tickets from initial_price. A per-show failure degrades
that show to the priceless fallback ticket.

Fetch strategy:
- The Punchup RSC stream is server-side rendered and accessible via a plain HTTP
  GET (no browser execution required). The page is fetched via BaseScraper.fetch_html()
  which sends curl_cffi impersonation headers. If the site adds DataDome protection
  in the future, switch to a bare AsyncSession.get(url) with no application headers
  (see CLAUDE.md DataDome section).
- Show data lives in the "venuePageCarousel" → "items" key of the RSC payload.
- The PunchupExtractor handles both direct JSON and JS-escaped push([1, "..."]) formats.
"""

import asyncio
import dataclasses
from typing import List, Optional

from laughtrack.core.clients.punchup.extractor import PunchupExtractor
from laughtrack.core.clients.tixologi import TixologiClient
from laughtrack.core.clients.tixologi.extractor import TixologiExtractor
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyKeyWestPageData, ComedyKeyWestShow
from .transformer import ComedyKeyWestEventTransformer

# Cap on concurrent Tixologi ticket-type fetches during enrichment — the
# public API has no caller-side rate limiting, so an unbounded gather would
# burst one request per show (mirrors creek_and_cave, TASK-2840).
_TIXOLOGI_MAX_CONCURRENT_FETCHES = 10


class ComedyKeyWestScraper(BaseScraper):
    """
    Scraper for Comedy Key West (Punchup platform, Next.js App Router).

    Fetches the shows page and extracts events from the React Query
    hydration state embedded in self.__next_f.push() streaming script tags.
    Uses Tixologi for ticket purchase links.
    """

    key = "comedy_key_west"

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.tixologi_client = TixologiClient(club)
        self.transformation_pipeline.register_transformer(ComedyKeyWestEventTransformer(club))

    async def get_data(self, url: str) -> Optional[ComedyKeyWestPageData]:
        """
        Fetch the shows page and extract events from the Punchup hydration data.

        Args:
            url: The shows page URL (from club.scraping_url).

        Returns:
            ComedyKeyWestPageData with extracted shows, or None if none found.
        """
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html_bare(normalized_url)
            if not html_content:
                Logger.warn(
                    f"{self._log_prefix}: received empty HTML from {url}",
                    self.logger_context,
                )
                return None

            punchup_shows = PunchupExtractor.extract_shows(html_content)
            if not punchup_shows:
                Logger.warn(
                    f"{self._log_prefix}: no shows found in Punchup hydration data at {url} — "
                    "site may have changed structure or have no upcoming events",
                    self.logger_context,
                )
                return None

            shows = [
                self._build_show(s)
                for s in punchup_shows
            ]

            shows = await self._enrich_tixologi_tickets(shows)

            Logger.info(
                f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
                self.logger_context,
            )
            return ComedyKeyWestPageData(event_list=shows)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching data from {url}: {e}",
                self.logger_context,
            )
            return None

    async def _enrich_tixologi_tickets(
        self, shows: List[ComedyKeyWestShow]
    ) -> List[ComedyKeyWestShow]:
        """Attach Tixologi ticket-type payloads to shows before transformation.

        Mirrors the creek_and_cave enrichment (TASK-2840): each show's
        tixologi_event_id is resolved against the public no-auth
        api-v2.tixologi.com endpoint so PunchupShow._build_tickets emits
        priced tickets from ticket_types[].initial_price. Each show is
        individually guarded — an enrichment error degrades that show to the
        priceless fallback ticket instead of dropping the whole page.
        """
        semaphore = asyncio.Semaphore(_TIXOLOGI_MAX_CONCURRENT_FETCHES)

        async def enrich(show: ComedyKeyWestShow) -> ComedyKeyWestShow:
            if not show.tixologi_event_id:
                return show
            try:
                async with semaphore:
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

        return await asyncio.gather(*(enrich(show) for show in shows))

    @staticmethod
    def _build_show(punchup_show) -> ComedyKeyWestShow:
        """Wrap a Punchup show while delegating Tixologi ticket fields to the shared client."""
        values = {f.name: getattr(punchup_show, f.name) for f in dataclasses.fields(punchup_show)}
        ticket_reference = TixologiExtractor.normalize_ticket_reference(
            values.get("ticket_link"),
            values.get("tixologi_event_id"),
        )
        values["ticket_link"] = ticket_reference.ticket_url
        values["tixologi_event_id"] = ticket_reference.event_id
        return ComedyKeyWestShow(**values)
