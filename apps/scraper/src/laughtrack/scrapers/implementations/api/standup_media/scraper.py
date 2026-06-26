"""StandUp Media reservation-platform scraper.

StandUp Media (apireservation.standupmedia.com) is the self-hosted ASP.NET
ticketing platform behind the Funny Bone national comedy-club chain and other
Levity Entertainment venues. Each venue site (stlouisfunnybone.com,
{city}funnybone.com, ...) is a thin front-end over the same JSON API:

    GET https://apireservation.standupmedia.com/api/Show/GetAllShows/{location_id}/false/{dbname}

which returns one record per price section (multiple rows share a ``ShowID``).
The scraper is generic across the chain — point a ``scraping_sources`` row at
the venue's events page (``source_url``, the ticket fallback) and supply the
per-venue API coordinates via ``metadata``:

    {"standup_media_location_id": "718bd264-...", "standup_media_dbname": "stlouis_prod"}

``location_id`` is the venue GUID embedded in the site's ``var locationid``;
``dbname`` is the site's ``var dbname`` (e.g. ``stlouis_prod``). The ``false``
path segment is the ``isprivate`` flag — public shows only.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.standup_media import StandUpMediaEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.standup_media.data import StandUpMediaPageData
from laughtrack.scrapers.implementations.api.standup_media.extractor import StandUpMediaExtractor
from laughtrack.scrapers.implementations.api.standup_media.transformer import (
    StandUpMediaEventTransformer,
)

_API_BASE = "https://apireservation.standupmedia.com/api/Show/GetAllShows"


class StandUpMediaScraper(BaseScraper):
    """Scraper for StandUp Media venue reservation feeds (Funny Bone chain)."""

    key = "standup_media"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/Chicago"
        self.transformation_pipeline.register_transformer(StandUpMediaEventTransformer(club))

    def _location_id(self) -> Optional[str]:
        val = (self.club.source_metadata or {}).get("standup_media_location_id")
        return str(val).strip() if val else None

    def _dbname(self) -> Optional[str]:
        val = (self.club.source_metadata or {}).get("standup_media_dbname")
        return str(val).strip() if val else None

    def _api_url(self) -> Optional[str]:
        location_id = self._location_id()
        dbname = self._dbname()
        if not location_id or not dbname:
            return None
        return f"{_API_BASE}/{location_id}/false/{dbname}"

    async def collect_scraping_targets(self) -> List[str]:
        """Build the GetAllShows API URL from the venue's metadata coordinates."""
        api_url = self._api_url()
        if not api_url:
            Logger.warn(
                f"{self._log_prefix}: missing standup_media_location_id / "
                "standup_media_dbname metadata",
                self.logger_context,
            )
            return []
        return [api_url]

    async def get_data(self, url: str) -> Optional[EventListContainer[StandUpMediaEvent]]:
        """Fetch the GetAllShows feed and return de-duplicated upcoming shows."""
        try:
            response = await self.fetch_json(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        if not response:
            Logger.warn(
                f"{self._log_prefix}: empty response from StandUp Media API ({url})",
                self.logger_context,
            )
            return None
        if not isinstance(response, list):
            Logger.warn(
                f"{self._log_prefix}: unexpected StandUp Media payload type "
                f"{type(response).__name__} ({url})",
                self.logger_context,
            )
            return None

        events = StandUpMediaExtractor.extract_events(
            response, self.club.scraping_url, self.default_timezone
        )
        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming shows in StandUp Media feed "
                f"({len(response)} record(s)) ({url})",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} StandUp Media show(s) "
            f"from {len(response)} section record(s)",
            self.logger_context,
        )
        return StandUpMediaPageData(event_list=events)
