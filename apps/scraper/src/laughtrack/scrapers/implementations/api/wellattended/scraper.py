"""WellAttended platform scraper.

WellAttended (``<venue>.wellattended.com``) is a Next.js RSC ticketing platform.
A venue's calendar lives on its own subdomain root; each show is a
``/events/<slug>`` detail page whose showing/occurrence + ticket-tier data is
embedded in the ``self.__next_f.push(...)`` RSC flight (no JSON-LD, no
``__NEXT_DATA__``).

Generic across the platform — point a ``scraping_sources`` row's ``source_url``
at the venue's WellAttended root (``https://<venue>.wellattended.com/``) and the
scraper keys off that subdomain. No per-venue code.

Pipeline:
  1. collect_scraping_targets() → [the venue WellAttended root]
  2. get_data(url):
       a. fetch the root → extract /events/<slug> slugs;
       b. fetch each /events/<slug> concurrently, parse the RSC flight into one
          WellAttendedEvent per upcoming occurrence.
  3. transformation_pipeline → WellAttendedEvent.to_show() → Show objects.

Currently used by: Theatre of Dreams Arts & Event Center (Castle Rock, CO).
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.wellattended import WellAttendedEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .data import WellAttendedPageData
from .extractor import WellAttendedExtractor
from .transformer import WellAttendedEventTransformer

_SLUG_BATCH_CONFIG = BatchScrapingConfig(
    max_concurrent=5,
    delay_between_requests=0,
    enable_logging=True,
)


class WellAttendedScraper(BaseScraper):
    """Scraper for WellAttended venue calendars (Next.js RSC flight)."""

    key = "wellattended"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            WellAttendedEventTransformer(club)
        )
        self.batch_scraper = BatchScraper(self.logger_context, config=_SLUG_BATCH_CONFIG)

    def _origin(self) -> str:
        parsed = urlparse(self.club.scraping_url or "")
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return (self.club.scraping_url or "").rstrip("/")

    async def collect_scraping_targets(self) -> List[str]:
        return [URLUtils.normalize_url(self.club.scraping_url)]

    async def get_data(self, url: str) -> Optional[WellAttendedPageData]:
        try:
            listing_html = await self.fetch_html(url)
            if not listing_html:
                self._warn_empty_extraction(url, subject="html", html=listing_html)
                return None

            slugs = WellAttendedExtractor.extract_event_slugs(listing_html)
            if not slugs:
                self._warn_empty_extraction(
                    url,
                    html=listing_html,
                    note="no /events/<slug> links found (site changed or no events)",
                )
                return None

            Logger.info(
                f"{self._log_prefix}: found {len(slugs)} event slug(s) on {url}",
                self.logger_context,
            )

            origin = self._origin()

            async def _fetch_slug(slug: str) -> List[WellAttendedEvent]:
                event_url = f"{origin}/events/{slug}"
                event_html = await self.fetch_html(event_url)
                if not event_html:
                    Logger.warn(
                        f"{self._log_prefix}: empty response for event {slug}",
                        self.logger_context,
                    )
                    return []
                return WellAttendedExtractor.extract_event_occurrences(
                    event_html, origin, slug
                )

            slug_results = await self.batch_scraper.process_batch(
                slugs, _fetch_slug, description="WellAttended event pages"
            )
            events: List[WellAttendedEvent] = [
                ev for result in slug_results for ev in result
            ]

            if not events:
                self._warn_empty_extraction(
                    f"{len(slugs)} event page(s) on {url}",
                    subject="upcoming occurrences",
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} upcoming occurrence(s)",
                self.logger_context,
            )
            return WellAttendedPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
