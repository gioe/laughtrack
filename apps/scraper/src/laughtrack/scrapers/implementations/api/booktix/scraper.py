"""Generic BookTix box-office scraper (Path B, listing → detail).

Serves any venue whose shows are ticketed through a BookTix box office at
``https://{org}.booktix.com``. Per-venue configuration is the box office home
URL, read from the club's scraping_url (e.g.
``https://makeshift.booktix.com/dept/main``).

BookTix exposes no JSON-LD or public JSON API; both the box office home and the
production pages are server-rendered HTML, so plain ``fetch_html`` (curl-cffi
with the shared Playwright fallback) suffices — no JS rendering required.

Pipeline:
    1. collect_scraping_targets(): fetch the box office home, regex-extract the
       production codes, return one production-page URL per code.
    2. get_data(url): fetch the production page, extract the production name and
       every showtime, wrap as BookTixPageData (one BookTixEvent per showtime).
    3. transformation_pipeline: BookTixEvent.to_show() -> Show objects.
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import BookTixPageData
from .extractor import extract_event_urls, extract_events
from .transformer import BookTixEventTransformer


class BookTixScraper(BaseScraper):
    """Two-step scraper for venues hosted on a {org}.booktix.com box office."""

    key = "booktix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(BookTixEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Fetch the box office home and return the production-page URLs."""
        home_url = self.club.scraping_url
        if not home_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no scraping_url configured",
                self.logger_context,
            )
            return []

        normalized_url = URLUtils.normalize_url(home_url)
        parsed = urlparse(normalized_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        html = await self.fetch_html(normalized_url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: BookTix box office returned empty HTML: {normalized_url}",
                self.logger_context,
            )
            return []

        event_urls = extract_event_urls(html, base_url)
        if not event_urls:
            Logger.warn(
                f"{self._log_prefix}: No BookTix production codes found on {normalized_url}",
                self.logger_context,
            )
            return []

        Logger.info(
            f"{self._log_prefix}: Discovered {len(event_urls)} BookTix production(s)",
            self.logger_context,
        )
        return event_urls

    async def get_data(self, target: ScrapingTarget) -> Optional[BookTixPageData]:
        """Fetch one BookTix production page and extract its showtimes."""
        try:
            html = await self.fetch_html(target)
            events = extract_events(html, target)
            if not events:
                Logger.warn(
                    f"{self._log_prefix}: No showtimes extracted from BookTix page {target}",
                    self.logger_context,
                )
                return None
            return BookTixPageData(event_list=events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting BookTix page {target}: {e}",
                self.logger_context,
            )
            return None
