"""
SeatEngine Classic scraper.

Handles venues on the legacy SeatEngine platform (cdn.seatengine.com),
which renders events as server-side HTML rather than the
services.seatengine.com REST API used by the newer platform.

Supports multi-location venues via a URL fragment:
  scraping_url = "https://example.com/events#location=Downtown"
The fragment is stripped before fetching but used to filter shows by
their event-label text (e.g. "Downtown", "6th and Proctor").
"""

from typing import List, Optional
from urllib.parse import urlparse, urlunparse, unquote

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url.utils import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.ports.scraping import EventListContainer

from .extractor import SeatEngineClassicExtractor
from .data import SeatEngineClassicPageData
from .transformer import SeatEngineClassicTransformer


class SeatEngineClassicScraper(BaseScraper):
    """
    Scraper for venues on the classic SeatEngine platform.

    These venues serve a server-rendered HTML events page at their
    custom domain (e.g. newbrunswick.stressfactory.com/events).
    The new services.seatengine.com REST API returns empty data for
    these venues, so we parse the HTML page directly.

    Multi-location filtering: If the scraping_url contains a fragment
    like ``#location=Downtown``, only shows whose event-label list
    includes "Downtown" (case-insensitive) are kept.

    DB column: clubs.scraper = 'seatengine_classic'
    """

    key = "seatengine_classic"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            SeatEngineClassicTransformer(club)
        )
        self._location_filter = self._parse_location_filter(club.scraping_url)

    @staticmethod
    def _parse_location_filter(scraping_url: str) -> Optional[str]:
        """Extract a location filter from the URL fragment (e.g. #location=Downtown)."""
        parsed = urlparse(scraping_url)
        fragment = parsed.fragment  # e.g. "location=Downtown"
        if fragment and fragment.startswith("location="):
            return unquote(fragment[len("location="):]).strip()
        return None

    async def collect_scraping_targets(self) -> List[str]:
        """Return the events page URL as the single scraping target (fragment stripped)."""
        url = URLUtils.normalize_url(self.club.scraping_url)
        # Strip fragment — it's only used for client-side location filtering
        parsed = urlparse(url)
        if parsed.fragment:
            url = urlunparse(parsed._replace(fragment=""))
        return [url]

    async def get_data(self, url: str) -> Optional[EventListContainer]:
        """Fetch the events page and extract shows from the HTML."""
        html = await self.fetch_html(url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: no HTML returned for {url}",
                self.logger_context,
            )
            return SeatEngineClassicPageData(event_list=[])

        base_url = URLUtils.get_base_domain_with_protocol(url)
        shows = SeatEngineClassicExtractor.extract_shows(html, base_url)
        Logger.info(
            f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
            self.logger_context,
        )

        if self._location_filter:
            filter_lower = self._location_filter.lower()
            filtered = [
                s for s in shows
                if any(filter_lower in lbl.lower() for lbl in s.get("location_labels", []))
            ]
            Logger.info(
                f"{self._log_prefix}: location filter '{self._location_filter}' "
                f"kept {len(filtered)}/{len(shows)} shows",
                self.logger_context,
            )
            shows = filtered

        return SeatEngineClassicPageData(event_list=shows)

    def transform_data(self, raw_data: EventListContainer, source_url: str) -> List[Show]:
        return super().transform_data(raw_data, source_url)
