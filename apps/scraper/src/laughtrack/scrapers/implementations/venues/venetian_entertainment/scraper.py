"""Venetian entertainment scraper implementation."""

from datetime import date
from typing import Optional
from urllib.parse import quote

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import VenetianEntertainmentPageData
from .extractor import VenetianEntertainmentExtractor
from .transformer import VenetianEntertainmentTransformer

_GRAPHQL_BASE_URL = "https://www.venetianlasvegas.com/graphql/execute.json/venetian/allEntertainment"


class VenetianEntertainmentScraper(BaseScraper):
    """Scraper for comedy listings from Venetian's venue-owned entertainment page."""

    key = "venetian_entertainment"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(VenetianEntertainmentTransformer(club))

    async def get_data(self, url: str) -> Optional[VenetianEntertainmentPageData]:
        try:
            graphql_url = self._graphql_url()
            payload = await self.fetch_json(graphql_url)
            if not isinstance(payload, dict):
                return None

            venue_category = self._venue_category()
            event_list = VenetianEntertainmentExtractor.extract_events(payload, venue_category=venue_category)
            Logger.info(
                f"{self._log_prefix}: extracted {len(event_list)} Venetian event(s) for {venue_category}",
                self.logger_context,
            )
            return VenetianEntertainmentPageData(event_list=event_list)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to scrape Venetian entertainment from {url}: {e}")
            return None

    def _graphql_url(self) -> str:
        today = date.today().isoformat()
        return f"{_GRAPHQL_BASE_URL}{quote(f';today={today}', safe='')}"

    def _venue_category(self) -> str:
        source = self.club.scraping_source
        metadata = source.metadata if source else {}
        configured = metadata.get("venue_category") if isinstance(metadata, dict) else None
        if isinstance(configured, str) and configured.strip():
            return configured.strip().lower()

        name = (self.club.name or "").lower()
        if "palazzo" in name:
            return "the-palazzo-theatre"
        return "the-venetian-theatre"
