"""Lesher Center scraper using the public Spektrix Link event catalog."""

from __future__ import annotations

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import LesherCenterPageData
from .extractor import LesherCenterExtractor
from .transformer import LesherCenterTransformer

_DEFAULT_EVENTS_URL = "https://app.spektrix-link.com/clients/lesherartscenter/eventsView.json"


class LesherCenterScraper(BaseScraper):
    """Scrape Lesher Center comedy/improv events from Spektrix Link."""

    key = "lesher_center"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LesherCenterTransformer(club))

    async def collect_scraping_targets(self) -> list[str]:
        return [URLUtils.normalize_url(self.club.scraping_url or _DEFAULT_EVENTS_URL)]

    async def get_data(self, url: str) -> Optional[LesherCenterPageData]:
        try:
            payload = await self.fetch_json(
                url,
                headers={"Accept": "application/json, text/plain, */*"},
            )
            events = LesherCenterExtractor.extract_events(payload)
            if not events:
                Logger.info(f"{self._log_prefix}: no Lesher comedy events found in {url}")
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} Lesher comedy event instances from {url}",
                self.logger_context,
            )
            return LesherCenterPageData(event_list=events)
        except Exception as exc:
            Logger.error(
                f"{self._log_prefix}: error fetching Lesher Spektrix catalog {url}: {exc}",
                self.logger_context,
            )
            return None
