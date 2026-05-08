"""World Stage scraper.

The Lounge at World Stage (and the venue's other rooms — Main Hall, XPN
Studios) publishes its full calendar through the public Ciright booking-tool
API at https://www.myciright.com/Ciright/api/worldcafelive/m3203760. The
endpoint is unauthenticated, returns structured JSON, and is hosted off the
DataDome-protected Etix path that previously broke the upstream scraper. This
scraper queries that API, filters to the room(s) configured for the club, and
emits one WorldStageEvent per confirmed booking.

Configuration lives in ``scraping_sources.metadata`` so other rooms (and any
future room-id rotation) can be onboarded with a DB-only change:

    metadata = {
        "subscription_id": 8990189,
        "vertical_id":     2851,
        "type_id":         1662515,
        "app_id":          2949,
        "status_id":       1851385,         # 'Confirmed'
        "room_ids":        [3131060],       # The Lounge
        "lookahead_days":  120,
        "api_url":         "https://www.myciright.com/Ciright/api/worldcafelive/m3203760"
    }

If a key is omitted the scraper falls back to the values observed live on
2026-05-07 against worldstage.live.
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import WorldStagePageData
from .extractor import WorldStageExtractor
from .transformer import WorldStageTransformer

_DEFAULT_API_URL = "https://www.myciright.com/Ciright/api/worldcafelive/m3203760"
_DEFAULT_SOURCE_URL = "https://worldstage.live/shows"
_DEFAULT_SUBSCRIPTION_ID = 8990189
_DEFAULT_VERTICAL_ID = 2851
_DEFAULT_TYPE_ID = 1662515
_DEFAULT_APP_ID = 2949
_DEFAULT_STATUS_ID = 1851385  # 'Confirmed'
_DEFAULT_LOOKAHEAD_DAYS = 120

# Headers observed on the live worldstage.live → myciright.com call.
# Ciright rejects requests that lack the X-Requested-With XMLHttpRequest hint.
_API_HEADERS = {
    "content-type": "application/json",
    "x-requested-with": "XMLHttpRequest",
    "referer": "https://worldstage.live/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
}


class WorldStageScraper(BaseScraper):
    """Hit the Ciright calendar API for World Stage and emit confirmed events."""

    key = "world_stage"
    default_source_url = _DEFAULT_SOURCE_URL

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(WorldStageTransformer(club))

    @property
    def _source_url(self) -> str:
        return self.club.scraping_url or self.default_source_url

    def _config(self) -> Dict[str, Any]:
        return self.club.source_metadata or {}

    def _api_url(self) -> str:
        return str(self._config().get("api_url") or _DEFAULT_API_URL)

    def _room_ids(self) -> List[int]:
        raw = self._config().get("room_ids")
        if isinstance(raw, list):
            return [int(r) for r in raw if r is not None]
        # Allow a single-value alias for ergonomic single-room rows.
        single = self._config().get("room_id")
        if single is not None:
            return [int(single)]
        return []

    def _build_payload(self) -> Dict[str, Any]:
        cfg = self._config()
        lookahead = int(cfg.get("lookahead_days", _DEFAULT_LOOKAHEAD_DAYS))
        today = date.today()
        end = today + timedelta(days=lookahead)
        # Ciright's room filter is buggy when populated (returns status:false),
        # so we always send room_ids=null and filter client-side in the extractor.
        return {
            "subscriptionId": int(cfg.get("subscription_id", _DEFAULT_SUBSCRIPTION_ID)),
            "verticalId": int(cfg.get("vertical_id", _DEFAULT_VERTICAL_ID)),
            "typeId": int(cfg.get("type_id", _DEFAULT_TYPE_ID)),
            "loginEmployeeId": 0,
            "appId": int(cfg.get("app_id", _DEFAULT_APP_ID)),
            "roomIds": None,
            "subStatusId": -1,
            "startDate": today.strftime("%m/%d/%Y"),
            "endDate": end.strftime("%m/%d/%Y"),
            "searchString": "",
            "statusIds": [int(cfg.get("status_id", _DEFAULT_STATUS_ID))],
        }

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return [self._api_url()]

    async def get_data(self, target: ScrapingTarget) -> Optional[WorldStagePageData]:
        api_url = str(target or self._api_url())
        room_ids = self._room_ids()
        if not room_ids:
            Logger.warn(
                f"{self._log_prefix}: scraping_sources.metadata is missing room_id(s); "
                f"refusing to scrape so unrelated rooms aren't ingested under this club",
                self.logger_context,
            )
            return None

        payload = self._build_payload()
        response = await self.post_json(api_url, payload, headers=_API_HEADERS)
        if not response:
            Logger.warn(
                f"{self._log_prefix}: empty Ciright response from {api_url}",
                self.logger_context,
            )
            return None
        if not response.get("status"):
            Logger.warn(
                f"{self._log_prefix}: Ciright returned status=false: "
                f"{response.get('message') or '(no message)'}",
                self.logger_context,
            )
            return None

        events = WorldStageExtractor.extract_events(
            response,
            room_ids=room_ids,
            source_url=self._source_url,
        )
        if not events:
            Logger.warn(
                f"{self._log_prefix}: no confirmed events for room_ids={room_ids} in Ciright response",
                self.logger_context,
            )
            return WorldStagePageData(event_list=[])

        Logger.info(
            f"{self._log_prefix}: {len(events)} confirmed event(s) from Ciright "
            f"(room_ids={room_ids})",
            self.logger_context,
        )
        return WorldStagePageData(event_list=events)
