"""Coral Springs Center for the Arts venue scraper.

Coral Springs Center for the Arts (Coral Springs, FL) is a multi-genre
performing-arts theater whose ticketing backend (thecenter.evenue.net, AudienceView
eVenue) is bot-walled. Its own site (thecentercs.com) exposes a server-rendered,
category-filtered comedy listing at ``/events/category/comedy`` and per-event detail
pages at ``/events/detail/<slug>``.

Pipeline:
  1. collect_scraping_targets() → [the comedy-category listing URL]
  2. get_data(url):
       - fetch the listing, extract the comedy detail-page URLs (already comedy-only,
         filtered server-side — no keyword heuristic needed);
       - fetch each detail page (the source of truth for title / full date / showtime
         / eVenue buy link) and parse it into an event.
  3. transformation_pipeline → CoralSpringsCenterEvent.to_show() → Show objects,
     with show_page_url pointing at the venue's own detail page.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import CoralSpringsCenterPageData
from .extractor import CoralSpringsCenterExtractor
from .transformer import CoralSpringsCenterEventTransformer

# The venue's own server-rendered comedy-category listing. The CMS filters the
# event set server-side, so this URL returns comedy events only.
_DEFAULT_COMEDY_URL = "https://www.thecentercs.com/events/category/comedy"


class CoralSpringsCenterScraper(BaseScraper):
    """Scrape comedy events from Coral Springs Center for the Arts' own site."""

    key = "coral_springs_center"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            CoralSpringsCenterEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        source_url = self.club.scraping_url or _DEFAULT_COMEDY_URL
        return [URLUtils.normalize_url(source_url)]

    async def get_data(self, url: str) -> Optional[CoralSpringsCenterPageData]:
        # The listing fetch error deliberately propagates (no broad try/except):
        # this is a single-target scraper, so swallowing it would misclassify a
        # full site outage as an empty comedy calendar. Per-detail fetch errors
        # below are contained so one bad detail page doesn't drop the rest.
        listing_html = await self.fetch_html(url)
        if not listing_html:
            self._warn_empty_extraction(url, subject="html", html=listing_html)
            return None

        detail_urls = CoralSpringsCenterExtractor.extract_comedy_detail_urls(listing_html, url)
        if not detail_urls:
            self._warn_empty_extraction(
                url,
                html=listing_html,
                note="no comedy detail links found (site structure changed or no comedy scheduled)",
            )
            return None

        events = []
        for detail_url in detail_urls:
            try:
                detail_html = await self.fetch_html(detail_url)
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: failed to fetch detail page {detail_url}: {e}",
                    self.logger_context,
                )
                continue
            # parse_detail returns one event per performance date (multi-night
            # engagements yield several); extend so every night is kept.
            events.extend(
                CoralSpringsCenterExtractor.parse_detail(detail_html or "", detail_url)
            )

        if not events:
            self._warn_empty_extraction(
                url,
                html=listing_html,
                note="comedy detail pages yielded no parseable upcoming events",
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} comedy event(s) from {url}",
            self.logger_context,
        )
        return CoralSpringsCenterPageData(event_list=events)
