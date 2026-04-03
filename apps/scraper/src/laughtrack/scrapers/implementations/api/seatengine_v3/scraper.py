"""
SeatEngine v3 scraper.

Fetches shows for venues that use the SeatEngine v3 GraphQL API
(services.seatengine.com/api/v3/public).

These venues expose a UUID-based venue identifier (stored in
clubs.seatengine_id) rather than the numeric IDs used by the v1 REST API.
The v3 API requires no authentication — requests are scoped to the venue
UUID in the query variables.

DB column: clubs.scraper = 'seatengine_v3'
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url.utils import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.ports.scraping import EventListContainer

from .extractor import SeatEngineV3Extractor
from .data import SeatEngineV3PageData
from .transformer import SeatEngineV3EventTransformer

_V3_API_URL = "https://services.seatengine.com/api/v3/public"


class SeatEngineV3Scraper(BaseScraper):
    """
    Scraper for venues on the SeatEngine v3 platform.

    Venues are identified by a UUID (stored in clubs.seatengine_id).
    Events are fetched via a single GraphQL query; each (event, show)
    pair becomes one Show in the pipeline.

    DB column: clubs.scraper = 'seatengine_v3'
    """

    key = "seatengine_v3"

    def __init__(self, club: Club, **kwargs):
        if not club.seatengine_id:
            raise ValueError(
                f"Club {club.name!r} is missing seatengine_id (venue UUID)"
            )

        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            SeatEngineV3EventTransformer(club)
        )

        self.venue_uuid = club.seatengine_id
        self.base_url = URLUtils.normalize_url(club.scraping_url)

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target: the venue UUID."""
        return [self.venue_uuid]

    async def get_data(self, target: str) -> Optional[EventListContainer]:
        """
        POST the GraphQL query to the v3 endpoint and return page data.

        Returns:
            SeatEngineV3PageData with one dict per (event, show) pair,
            or an empty container on failure.
        """
        payload = SeatEngineV3Extractor.build_query_payload(self.venue_uuid)
        headers = {
            "Content-Type": "application/json",
            "Origin": self.base_url,
        }
        try:
            response = await self.post_json(_V3_API_URL, data=payload, headers=headers)
        except Exception as exc:
            Logger.warn(
                f"{self._log_prefix}: GraphQL request failed for venue {self.venue_uuid}: {exc}",
                self.logger_context,
            )
            return SeatEngineV3PageData(event_list=[])

        if not response:
            Logger.warn(
                f"{self._log_prefix}: no response from GraphQL API for venue {self.venue_uuid}",
                self.logger_context,
            )
            return SeatEngineV3PageData(event_list=[])

        if "errors" in response:
            Logger.warn(
                f"{self._log_prefix}: GraphQL errors for venue {self.venue_uuid}: {response['errors']}",
                self.logger_context,
            )
            return SeatEngineV3PageData(event_list=[])

        records = SeatEngineV3Extractor.flatten_events(response, self.base_url)
        Logger.info(
            f"{self._log_prefix}: extracted {len(records)} (event, show) pairs for venue {self.venue_uuid}",
            self.logger_context,
        )
        return SeatEngineV3PageData(event_list=records)

    def transform_data(self, raw_data: EventListContainer, source_url: str) -> List[Show]:
        return super().transform_data(raw_data, source_url)
