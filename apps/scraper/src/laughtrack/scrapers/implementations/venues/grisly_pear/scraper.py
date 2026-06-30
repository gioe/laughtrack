"""Scraper for the Grisly Pear calendar listing."""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import GrislyPearPageData
from .extractor import GrislyPearExtractor
from .transformer import GrislyPearTransformer


class GrislyPearScraper(BaseScraper):
    """Extract dated event anchors from grislypearstandup.com/calendar."""

    key = "grisly_pear"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._register_host_rps(2.0)
        self.transformation_pipeline.register_transformer(GrislyPearTransformer(club))

    async def collect_scraping_targets(self) -> list[ScrapingTarget]:
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[GrislyPearPageData]:
        html = await self.fetch_html(url)
        if not html:
            self._warn_empty_extraction(url, subject="calendar", html=html)
            return None

        events = GrislyPearExtractor.extract_events(
            html,
            base_url=url,
            club_name=self.club.name,
        )
        if not events:
            self._warn_empty_extraction(url, html=html)
            return None
        return GrislyPearPageData(event_list=events)
