"""Standing Room Only (SRO) box-office scraper.

Standing Room Only Tickets (standingroomonlytickets.com, "sromedia") is an
ASP.NET box-office platform. Each venue runs on its own SRO host; its full live
calendar is served by one Kendo-UI endpoint::

    POST {base}/Event/ReadLiveEvents        (empty body -> all live events)

which returns ``{"Data": [event, ...], "Total": N}``. Each event is a headliner
residency carrying a ``Shows`` array (one entry per showtime), so the scraper
fans every event out to one Show per showtime.

The scraper is generic across the platform: point a ``scraping_sources`` row's
``source_url`` at the venue's ReadLiveEvents endpoint
(``https://<sro-host>/Event/ReadLiveEvents``) and the scraper derives both the
POST target and each show's public event page
(``https://<sro-host>/WebOffice/EventList/{event_id}``) from it. No per-venue
metadata is required — the no-body POST returns exactly that host's events.

Currently used by: One Night Stans Comedy Club (Waterford Township, MI).
"""

import json
from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.standing_room_only import StandingRoomOnlyEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.standing_room_only.data import (
    StandingRoomOnlyPageData,
)
from laughtrack.scrapers.implementations.api.standing_room_only.extractor import (
    StandingRoomOnlyExtractor,
)
from laughtrack.scrapers.implementations.api.standing_room_only.transformer import (
    StandingRoomOnlyEventTransformer,
)

_READ_LIVE_EVENTS_PATH = "/Event/ReadLiveEvents"


class StandingRoomOnlyScraper(BaseScraper):
    """Scraper for Standing Room Only venue ReadLiveEvents feeds."""

    key = "standing_room_only"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/New_York"
        self.transformation_pipeline.register_transformer(
            StandingRoomOnlyEventTransformer(club)
        )

    def _base_origin(self) -> Optional[str]:
        """Return the SRO host origin (scheme://netloc) from the source URL."""
        parsed = urlparse(self.club.scraping_url or "")
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    async def collect_scraping_targets(self) -> List[str]:
        """Build the ReadLiveEvents POST target from the venue's SRO host."""
        origin = self._base_origin()
        if not origin:
            Logger.warn(
                f"{self._log_prefix}: invalid/empty SRO source_url "
                f"({self.club.scraping_url!r})",
                self.logger_context,
            )
            return []
        return [f"{origin}{_READ_LIVE_EVENTS_PATH}"]

    async def get_data(self, url: str) -> Optional[EventListContainer[StandingRoomOnlyEvent]]:
        """POST the (empty-body) ReadLiveEvents form and extract upcoming shows."""
        origin = self._base_origin()
        if not origin:
            return None

        try:
            body = await self.post_form(url, "")
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        if not body or not body.strip():
            Logger.warn(
                f"{self._log_prefix}: empty response from ReadLiveEvents ({url})",
                self.logger_context,
            )
            return None

        try:
            payload = json.loads(body)
        except (ValueError, TypeError) as e:
            Logger.warn(
                f"{self._log_prefix}: non-JSON ReadLiveEvents response ({url}): {e}",
                self.logger_context,
            )
            return None

        events = StandingRoomOnlyExtractor.extract_events(
            payload, origin, self.default_timezone
        )
        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming shows in ReadLiveEvents feed ({url})",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} SRO show(s) from {url}",
            self.logger_context,
        )
        return StandingRoomOnlyPageData(event_list=events)
