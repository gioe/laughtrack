"""Generic scraper for DICE partner event-list widgets."""

from __future__ import annotations

from typing import Any, List, Optional
from urllib.parse import urlsplit, urlencode

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.dice import DiceEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DicePageData
from .transformer import DiceEventTransformer

_API_BASE_URL = "https://partners-endpoint.dice.fm/api/v2/events"
_DEFAULT_PAGE_SIZE = 24


def _csv_values(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _partner_endpoint_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    query = urlsplit(url).query
    return f"{_API_BASE_URL}?{query}" if query else url


class DiceScraper(BaseScraper):
    """Generic DICE scraper configured from ``scraping_sources.metadata``."""

    key = "dice"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(DiceEventTransformer(club))
        self._api_key = club.metadata_value("dice_api_key") or ""
        if not self._api_key:
            raise ValueError(
                f"DiceScraper requires metadata.dice_api_key for club_id={club.id} "
                f"('{club.name}')"
            )
        self._page_size = int(club.metadata_value("dice_page_size") or _DEFAULT_PAGE_SIZE)

    async def collect_scraping_targets(self) -> List[str]:
        params: list[tuple[str, str]] = [
            ("page[size]", str(self._page_size)),
            ("types", "linkout,event"),
            ("filter[flags][]", "going_ahead"),
            ("filter[flags][]", "rescheduled"),
        ]

        metadata = self.club.source_metadata
        venue_ids = _csv_values(self.club.metadata_value("dice_venue_id"))
        promoter_ids = _csv_values(self.club.metadata_value("dice_promoter_id"))
        venue_names = _csv_values(self.club.metadata_value("dice_venue_name"))
        promoter_names = _csv_values(self.club.metadata_value("dice_promoter_name"))
        tags = _csv_values(self.club.metadata_value("dice_tags"))

        for venue_id in venue_ids:
            params.append(("filter[venue_ids][]", venue_id))
        for promoter_id in promoter_ids:
            params.append(("filter[promoter_ids][]", promoter_id))
        for venue_name in venue_names:
            params.append(("filter[venues][]", venue_name))
        for promoter_name in promoter_names:
            params.append(("filter[promoters][]", promoter_name))
        for tag in tags:
            params.append(("filter[tags][]", tag))

        if not any(key.startswith("dice_") for key in metadata):
            raise ValueError(
                f"DiceScraper requires DICE filter metadata for club_id={self.club.id} "
                f"('{self.club.name}')"
            )
        if not any(name.startswith("filter[venue") or name.startswith("filter[promoter") for name, _ in params):
            raise ValueError(
                f"DiceScraper requires at least one venue/promoter filter for club_id={self.club.id} "
                f"('{self.club.name}')"
            )

        url = f"{_API_BASE_URL}?{urlencode(params)}"
        Logger.info(f"{self._log_prefix}: generated DICE API URL", self.logger_context)
        return [url]

    async def get_data(self, url: str) -> Optional[DicePageData]:
        try:
            current_url: Optional[str] = url
            events: list[DiceEvent] = []
            visited: set[str] = set()

            while current_url and current_url not in visited:
                visited.add(current_url)
                response = await self.fetch_json(current_url, headers={"x-api-key": self._api_key})
                if response is None:
                    Logger.info(
                        f"{self._log_prefix}: empty response from DICE API ({current_url})",
                        self.logger_context,
                    )
                    break

                raw_events = response.get("data", [])
                for item in raw_events:
                    if not isinstance(item, dict):
                        continue
                    if not self._is_allowed_event(item):
                        continue
                    events.append(DiceEvent.from_api_response(item))

                links: dict[str, Any] = response.get("links") or {}
                current_url = _partner_endpoint_url(links.get("next"))

            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events in DICE response ({url})",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} DICE event(s)",
                self.logger_context,
            )
            return DicePageData(event_list=events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

    @staticmethod
    def _is_allowed_event(item: dict[str, Any]) -> bool:
        flags = set(item.get("flags") or [])
        if "cancelled" in flags or "postponed" in flags:
            return False
        return bool(item.get("name") and item.get("date"))
