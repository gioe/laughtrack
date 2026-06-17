"""Scraper for Upright Citizens Brigade's WP Grid Builder show listing.

UCB's ``/shows/`` page is rendered by WP Grid Builder. The live AJAX seam is
``/?wpgb-ajax=render|refresh`` with a multipart ``wpgb`` payload, but the same
card HTML is server-rendered when the location facet is present in the query
string. Fetching ``/shows/?_filter_locations=<slug>`` keeps the scraper on the
normal HTML path while still using the WPGB datasource.
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import UCBPageData
from .extractor import UCBExtractor
from .transformer import UCBEventTransformer

_DEFAULT_SOURCE_URL = "https://ucbcomedy.com/shows/"
_DEFAULT_LOCATION_BY_CLUB_ID = {
    8823: "la-annex",
    8834: "la-franklin",
}


class UCBScraper(BaseScraper):
    """Fetch UCB shows for a configured WP Grid Builder location slug."""

    key = "ucb"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(UCBEventTransformer(club))

    @property
    def _source_url(self) -> str:
        return self.club.scraping_url or _DEFAULT_SOURCE_URL

    @property
    def _location_slug(self) -> Optional[str]:
        return self.club.metadata_value("location_slug") or _DEFAULT_LOCATION_BY_CLUB_ID.get(self.club.id)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        location_slug = self._location_slug
        if not location_slug:
            Logger.warn(
                f"{self._log_prefix}: UCB scraper requires metadata.location_slug",
                self.logger_context,
            )
            return []

        source_url = URLUtils.normalize_url(self._source_url)
        parsed = urlparse(source_url)
        if parsed.path == "/shows":
            source_url = f"{source_url}/"
        separator = "&" if urlparse(source_url).query else "?"
        return [f"{source_url}{separator}_filter_locations={location_slug}"]

    async def get_data(self, target: ScrapingTarget) -> Optional[UCBPageData]:
        location_slug = self._location_slug
        if not location_slug:
            return None

        try:
            html = await self.fetch_html(str(target), scraper_key=self.key)
        except Exception as e:
            Logger.warn(f"{self._log_prefix}: failed to fetch UCB target {target}: {e}", self.logger_context)
            return None

        events = UCBExtractor.extract_events(
            html,
            source_url=self._source_url,
            location_slug=location_slug,
        )
        if not events:
            self._warn_empty_extraction(str(target), html=html)
            return None

        Logger.info(
            f"{self._log_prefix}: Extracted {len(events)} UCB event(s) for location {location_slug}",
            self.logger_context,
        )
        return UCBPageData(event_list=events)
