"""Comix Roadhouse scraper implementation."""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComixRoadhousePageData
from .extractor import ComixRoadhouseExtractor
from .transformer import ComixRoadhouseTransformer


class ComixRoadhouseScraper(BaseScraper):
    """Scraper for Comix Roadhouse at Mohegan Sun."""

    key = "comix_roadhouse"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComixRoadhouseTransformer(club))

    async def get_data(self, url: str) -> Optional[ComixRoadhousePageData]:
        try:
            listing_urls = []
            seen_listing_pages = set()
            next_url = URLUtils.normalize_url(url)

            while next_url and next_url not in seen_listing_pages:
                seen_listing_pages.add(next_url)
                html_content = await self.fetch_html(next_url)
                if not html_content:
                    break

                listing_urls.extend(ComixRoadhouseExtractor.extract_listing_urls(html_content))
                next_url = ComixRoadhouseExtractor.extract_next_page_url(html_content, next_url)

            detail_urls = list(dict.fromkeys(listing_urls))
            events = []
            for detail_url in detail_urls:
                detail_html = await self.fetch_html(detail_url)
                if not detail_html:
                    continue
                events.extend(
                    ComixRoadhouseExtractor.extract_events_from_detail(
                        detail_html,
                        detail_url,
                        self.club.timezone or "America/New_York",
                    )
                )

            Logger.info(f"{self._log_prefix}: extracted {len(events)} Comix Roadhouse event(s)", self.logger_context)
            return ComixRoadhousePageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to scrape Comix Roadhouse: {e}", self.logger_context)
            return None
