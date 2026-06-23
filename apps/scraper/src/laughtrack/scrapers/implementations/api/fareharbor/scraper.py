"""Generic FareHarbor scraper.

FareHarbor exposes an unauthenticated company items endpoint and public monthly
calendar endpoints for bookable items:

``/api/v1/companies/{shortname}/items/``
``/api/v1/companies/{shortname}/items/{item_pk}/calendar/{year}/{month}/``

Wiring: set ``scraper_key='fareharbor'``, ``platform='custom'``, and either
``metadata.shortname`` or a FareHarbor source URL containing the shortname.
Optional metadata:

- ``exclude_item_pks``: item IDs to skip, useful for gift cards/donations/classes
- ``allow_item_pks``: item IDs to include, overriding keyword exclusion
- ``months_ahead``: number of calendar months to scan, default 12
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import FareHarborPageData
from .extractor import (
    extract_events_from_calendar,
    extract_items,
    item_is_operational,
)
from .transformer import FareHarborEventTransformer

_BASE_URL = "https://fareharbor.com"
_DEFAULT_MONTHS_AHEAD = 12


@dataclass(frozen=True)
class FareHarborConfig:
    shortname: str
    months_ahead: int = _DEFAULT_MONTHS_AHEAD
    exclude_item_pks: tuple[int, ...] = ()
    allow_item_pks: Optional[tuple[int, ...]] = None


class FareHarborScraper(BaseScraper):
    """Public JSON scraper for venues ticketed through FareHarbor."""

    key = "fareharbor"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            FareHarborEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        config = self._config()
        if config is None:
            Logger.warn(
                f"{self._log_prefix}: missing FareHarbor shortname in source_url or metadata",
                self.logger_context,
            )
            return []
        return [self._items_url(config.shortname)]

    async def get_data(self, target: ScrapingTarget) -> Optional[FareHarborPageData]:
        config = self._config()
        if config is None:
            return None

        items_payload = await self._fetch_json_or_none(str(target))
        items = extract_items(items_payload)
        if not items:
            self._warn_empty_extraction(str(target), subject="items", payload=items_payload)
            return None

        show_items = [
            item
            for item in items
            if not item_is_operational(
                item,
                excluded_item_pks=config.exclude_item_pks,
                allowed_item_pks=config.allow_item_pks,
            )
        ]
        if not show_items:
            Logger.warn(
                f"{self._log_prefix}: all {len(items)} FareHarbor items were filtered",
                self.logger_context,
            )
            return None

        events = []
        seen_event_urls: set[str] = set()
        for item in show_items:
            item_pk = item.get("pk")
            if item_pk is None:
                continue
            for year, month in _month_window(config.months_ahead):
                calendar_url = self._calendar_url(config.shortname, item_pk, year, month)
                calendar_payload = await self._fetch_json_or_none(calendar_url, allow_404=True)
                if not calendar_payload:
                    continue
                for event in extract_events_from_calendar(
                    calendar_payload, item=item, base_url=_BASE_URL
                ):
                    if event.show_page_url in seen_event_urls:
                        continue
                    seen_event_urls.add(event.show_page_url)
                    events.append(event)

        if not events:
            Logger.warn(
                f"{self._log_prefix}: no FareHarbor availabilities extracted",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} FareHarbor availability event(s)",
            self.logger_context,
        )
        return FareHarborPageData(events)

    async def _fetch_json_or_none(self, url: str, *, allow_404: bool = False) -> Any:
        """Fetch JSON, treating selected 404s as empty month/item responses."""
        session = await self.get_session()
        response = await session.get(
            url,
            headers={
                "accept": "application/json, text/plain, */*",
                "referer": self.club.scraping_url or _BASE_URL,
            },
        )
        if response.status_code == 404 and allow_404:
            return None
        if response.status_code != 200:
            Logger.warn(
                f"{self._log_prefix}: FareHarbor returned HTTP {response.status_code} for {url}",
                self.logger_context,
            )
            response.raise_for_status()
        return response.json()

    def _config(self) -> Optional[FareHarborConfig]:
        metadata = self.club.source_metadata or {}
        shortname = _clean(metadata.get("shortname")) or _shortname_from_url(
            self.club.scraping_url
        )
        if not shortname:
            return None
        return FareHarborConfig(
            shortname=shortname,
            months_ahead=_positive_int(metadata.get("months_ahead"), _DEFAULT_MONTHS_AHEAD),
            exclude_item_pks=tuple(_int_list(metadata.get("exclude_item_pks"))),
            allow_item_pks=_optional_int_tuple(metadata.get("allow_item_pks")),
        )

    @staticmethod
    def _items_url(shortname: str) -> str:
        return f"{_BASE_URL}/api/v1/companies/{shortname}/items/"

    @staticmethod
    def _calendar_url(shortname: str, item_pk: Any, year: int, month: int) -> str:
        return (
            f"{_BASE_URL}/api/v1/companies/{shortname}/items/{item_pk}"
            f"/calendar/{year}/{month:02d}/"
        )


def _month_window(months_ahead: int) -> list[tuple[int, int]]:
    start = date.today().replace(day=1)
    return [
        (
            start.year + (start.month + offset - 1) // 12,
            (start.month + offset - 1) % 12 + 1,
        )
        for offset in range(max(1, months_ahead))
    ]


def _shortname_from_url(url: str) -> str:
    parsed = urlparse(url or "")
    parts = [part for part in parsed.path.split("/") if part]
    if "companies" in parts:
        idx = parts.index("companies")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if len(parts) >= 2 and parts[0] == "embeds" and parts[1] == "book":
        return parts[2] if len(parts) >= 3 else ""
    return ""


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _int_list(value: Any) -> list[int]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    parsed = []
    for raw in raw_values:
        try:
            parsed.append(int(raw))
        except (TypeError, ValueError):
            continue
    return parsed


def _optional_int_tuple(value: Any) -> Optional[tuple[int, ...]]:
    parsed = tuple(_int_list(value))
    return parsed or None
