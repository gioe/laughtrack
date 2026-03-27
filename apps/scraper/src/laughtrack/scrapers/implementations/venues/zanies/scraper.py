"""
Zanies Comedy Club scraper.

Zanies (1548 N Wells St, Chicago, IL) lists shows on its homepage via the
rhp-events WordPress plugin.  Headliner runs are surfaced as series page
links; one-off special events appear as individual event-card "More Info"
links.

Pipeline:
  1. collect_scraping_targets() — fetch the homepage; collect unique series
     page URLs (/calendar/category/series/...) and single-show page URLs
     (/show/...).
  2. get_data(url) — fetch one page and extract events; the URL type
     determines which extractor path is used.
  3. transformation_pipeline — ZaniesEvent.to_show() → Show objects.
"""

import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ZaniesPageData
from .extractor import ZaniesExtractor
from .transformer import ZaniesEventTransformer

_SERIES_URL_RE = re.compile(
    r'href="(https://chicago\.zanies\.com/calendar/category/series/[^"]+)"',
    re.IGNORECASE,
)
_SHOW_URL_RE = re.compile(
    r'href="(https://chicago\.zanies\.com/show/[^"]+)"',
    re.IGNORECASE,
)


class ZaniesScraper(BaseScraper):
    """Scraper for Zanies Comedy Club (Chicago, IL)."""

    key = "zanies"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ZaniesEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """
        Return the list of page URLs to scrape.

        Fetches the homepage and extracts unique series page URLs (each
        covering a full headliner run) and single-show page URLs (for
        standalone special events).  The two sets are combined and
        deduplicated using dict ordering.
        """
        homepage_url = URLUtils.normalize_url(self.club.scraping_url)
        html = await self.fetch_html(homepage_url)
        if not html:
            Logger.warn(
                f"ZaniesScraper: empty response for homepage {homepage_url}",
                self.logger_context,
            )
            return []

        series_urls = list(dict.fromkeys(_SERIES_URL_RE.findall(html)))
        show_urls = list(dict.fromkeys(_SHOW_URL_RE.findall(html)))
        targets = series_urls + show_urls

        Logger.info(
            f"ZaniesScraper: discovered {len(series_urls)} series URLs and "
            f"{len(show_urls)} single-show URLs from homepage",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[ZaniesPageData]:
        """
        Fetch one page and extract events.

        Detects the page type from the URL:
        - /calendar/category/series/... → series page (multiple performances)
        - /show/...                     → single-show page (one event)
        """
        try:
            html = await self.fetch_html(URLUtils.normalize_url(url))
            if not html:
                Logger.warn(
                    f"ZaniesScraper: empty response for {url}",
                    self.logger_context,
                )
                return None

            if "/calendar/category/series/" in url:
                events = ZaniesExtractor.extract_series_events(html)
            else:
                events = ZaniesExtractor.extract_single_show_events(html)

            if not events:
                Logger.info(
                    f"ZaniesScraper: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"ZaniesScraper: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ZaniesPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"ZaniesScraper: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
