"""Generic scraper for Tugoz-hosted events.

Tugoz embeds load a site-owned config.js that maps friendly event keys to
Tugoz event IDs:

    SITE_CONFIG.LIVE_EVENTS = { openmic: 112933 }

The scraper fetches that config, expands event IDs into Tugoz static event JSON
URLs, and transforms future events into standard Show objects.
"""

from typing import Any, Iterable, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TugozPageData
from .extractor import TugozExtractor
from .transformer import TugozEventTransformer

_STATIC_EVENT_BASE = "https://static.tugoz.com/api/json/www/v4/e-"


class TugozScraper(BaseScraper):
    """Generic scraper for venues using Tugoz ticket widgets."""

    key = "tugoz"

    def __init__(self, club: Club, **kwargs: Any):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TugozEventTransformer(club))

    def validate_configuration(self) -> bool:
        return bool(self.club.scraping_url or self._metadata_event_ids())

    async def collect_scraping_targets(self) -> List[str]:
        event_ids = await self._collect_event_ids()
        urls = [f"{_STATIC_EVENT_BASE}{event_id}" for event_id in event_ids]
        Logger.info(
            f"{self._log_prefix}: generated {len(urls)} Tugoz event JSON URL(s)",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[TugozPageData]:
        try:
            payload = await self.fetch_json(url)
            if not isinstance(payload, dict):
                return None

            event = TugozExtractor.event_from_payload(payload)
            if event is None:
                return None
            if event.is_stale():
                Logger.info(
                    f"{self._log_prefix}: skipping stale Tugoz event {event.event_id} ({event.title})",
                    self.logger_context,
                )
                return None
            return TugozPageData(event_list=[event])
        except Exception as exc:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {exc}", self.logger_context)
            return None

    async def _collect_event_ids(self) -> list[int]:
        event_ids: list[int] = []
        if self.club.scraping_url:
            try:
                config_js = await self.fetch_html(self.club.scraping_url)
                event_ids = TugozExtractor.extract_live_event_ids(config_js, self._metadata_event_keys())
            except Exception as exc:
                Logger.warn(
                    f"{self._log_prefix}: failed to parse Tugoz config {self.club.scraping_url}: {exc}",
                    self.logger_context,
                )

        if not event_ids:
            event_ids = self._metadata_event_ids()

        return list(dict.fromkeys(event_ids))

    def _metadata_event_keys(self) -> list[str]:
        return [str(value) for value in self._metadata_list("event_keys")]

    def _metadata_event_ids(self) -> list[int]:
        event_ids = []
        for raw in self._metadata_list("event_ids"):
            try:
                event_ids.append(int(raw))
            except (TypeError, ValueError):
                continue
        return event_ids

    def _metadata_list(self, key: str) -> Iterable[Any]:
        raw = self.club.source_metadata.get(key)
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, tuple):
            return list(raw)
        if isinstance(raw, str):
            return [part.strip() for part in raw.split(",") if part.strip()]
        return [raw]

