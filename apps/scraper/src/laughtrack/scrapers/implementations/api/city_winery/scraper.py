"""Reusable City Winery API scraper."""

from typing import Any, Optional
from urllib.parse import urlencode

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import CityWineryPageData
from .extractor import CityWineryExtractor
from .transformer import CityWineryEventTransformer

_EVENTS_URL = "https://awsapi.citywinery.com/events"
_PAGE_SIZE = 16
_MAX_PAGES = 25


class CityWineryScraper(BaseScraper):
    """Generic City Winery scraper configured by scraping_sources metadata."""

    key = "city_winery"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(CityWineryEventTransformer(club))
        self._location = (club.metadata_value("location") or "").strip()
        self._genre = (club.metadata_value("genre") or "").strip()
        if not self._location:
            raise ValueError(f"Club {club.name} is missing City Winery metadata.location")

    async def collect_scraping_targets(self) -> list[str]:
        """Return the configured location as the logical API target."""
        return [self._location]

    async def _fetch_events_page(self, *, location: str, skip: int) -> Optional[dict[str, Any]]:
        params: dict[str, Any] = {
            "location": location,
            "top": _PAGE_SIZE,
            "skip": skip,
        }
        if self._genre:
            params["genre"] = self._genre

        url = f"{_EVENTS_URL}?{urlencode(params)}"
        try:
            async with AsyncSession(impersonate="chrome124") as session:
                return await HttpClient.fetch_json(
                    session=session,
                    url=url,
                    headers=None,
                    logger_context=self.logger_context,
                )
        except Exception as exc:
            Logger.warning(
                f"{self._log_prefix}: City Winery API page failed for "
                f"location={location!r} skip={skip}: {exc}",
                self.logger_context,
            )
            return None

    async def get_data(self, target: str) -> Optional[CityWineryPageData]:
        """Fetch and paginate all configured City Winery events."""
        all_events = []
        seen_ids: set[str] = set()
        total_events: Optional[int] = None

        for page_index in range(_MAX_PAGES):
            skip = page_index * _PAGE_SIZE
            if total_events is not None and skip >= total_events:
                break

            payload = await self._fetch_events_page(location=target, skip=skip)
            if not payload:
                break

            data = payload.get("data") or {}
            if not isinstance(data, dict):
                break

            if total_events is None:
                total_events = _safe_int(data.get("total_events"))

            raw_events = data.get("event_data") or []
            if not isinstance(raw_events, list) or not raw_events:
                break

            events = CityWineryExtractor.extract_events(
                [event for event in raw_events if isinstance(event, dict)]
            )
            for event in events:
                dedupe_key = event.event_id or event.slug
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)
                all_events.append(event)

        if not all_events:
            Logger.info(
                f"{self._log_prefix}: no City Winery events found for location={target!r}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: fetched {len(all_events)} City Winery events "
            f"for location={target!r}",
            self.logger_context,
        )
        return CityWineryPageData(event_list=all_events)


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
