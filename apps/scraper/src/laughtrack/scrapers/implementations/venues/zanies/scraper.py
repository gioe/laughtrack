"""
Zanies Comedy Club scraper.

Zanies (1548 N Wells St, Chicago, IL) lists shows on its homepage via the
rhp-events WordPress plugin.  Headliner runs are surfaced as series page
links; one-off special events appear as individual event-card "More Info"
links. Rosemont instead uses its full RHP month calendar's performance feed.

Pipeline:
  1. collect_scraping_targets() — fetch the homepage; collect unique series
     page URLs (/calendar/category/series/... or /show/category/series/...)
     and single-show page URLs
     (/show/...), or the full month calendar's individual performance URLs.
  2. get_data(url) — fetch one page and extract events; the URL type
     determines which extractor path is used.
  3. transformation_pipeline — ZaniesEvent.to_show() → Show objects.
"""

import json
import re
from typing import List, Optional
from urllib.parse import urlencode, urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ZaniesPageData
from .extractor import ZaniesExtractor
from .transformer import ZaniesEventTransformer


def _build_url_patterns(scraping_url: str):
    """Build URL regex patterns from the club's scraping_url host."""
    host = urlparse(scraping_url).hostname or "chicago.zanies.com"
    escaped = re.escape(host)
    series_re = re.compile(
        rf'href="(https://{escaped}/(?:calendar|show)/category/series/[^"]+)"',
        re.IGNORECASE,
    )
    show_re = re.compile(
        rf'href="(https://{escaped}/show/(?!category/)[^"]+)"',
        re.IGNORECASE,
    )
    return series_re, show_re


class ZaniesScraper(BaseScraper):
    """Scraper for Zanies Comedy Club venues."""

    key = "zanies"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ZaniesEventTransformer(club))
        self._series_url_re, self._show_url_re = _build_url_patterns(club.scraping_url or "")

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
                f"{self._log_prefix}: empty response for homepage {homepage_url}",
                self.logger_context,
            )
            return []

        # RHP's month calendar loads the entire advertised schedule in one
        # request (month navigation is client-side). Rosemont's homepage is
        # only a teaser; use its configured calendar instead of that subset.
        soup = BeautifulSoup(html, "html.parser")
        calendar = soup.select_one("#eventCalendar.mainCalendar")
        if calendar is not None:
            return await self._collect_calendar_targets(soup, calendar, homepage_url)
        if "view=month" in homepage_url:
            raise ValueError("Zanies month calendar widget is missing")

        series_urls = list(dict.fromkeys(self._series_url_re.findall(html)))
        show_urls = list(dict.fromkeys(self._show_url_re.findall(html)))
        targets = series_urls + show_urls

        Logger.info(
            f"{self._log_prefix}: discovered {len(series_urls)} series URLs and "
            f"{len(show_urls)} single-show URLs from homepage",
            self.logger_context,
        )
        return targets

    async def _collect_calendar_targets(self, soup, calendar, calendar_url: str) -> List[str]:
        """Mirror RHP monthCustom.js using the calendar's own configuration."""
        endpoint = soup.select_one("#adminAjaxURL")
        limit = soup.select_one("#evPostPerPage")
        ajax_url = endpoint.get("value", "") if endpoint else ""
        venue = calendar.get("widget-venues", "")
        if (
            urlparse(ajax_url).scheme != "https"
            or urlparse(ajax_url).netloc != urlparse(calendar_url).netloc
            or not venue
            or limit is None
            or not str(limit.get("value", "")).isdigit()
        ):
            raise ValueError("Zanies month calendar has invalid endpoint or venue configuration")
        response = json.loads(
            await self.post_form(
                ajax_url,
                urlencode(
                    {
                        "action": "loadEtixMonthViewEventPageFn",
                        "data[limit]": limit["value"],
                        "data[venues]": venue,
                        "data[widget]": "true",
                        "data[target]": "calendar-1",
                    }
                ),
            )
        )
        data = response.get("data") if isinstance(response, dict) else None
        if (
            not isinstance(response, dict)
            or response.get("success") is not True
            or not isinstance(data, dict)
            or not isinstance(data.get("events"), list)
        ):
            raise ValueError("Zanies month calendar returned an invalid event response")
        events = data["events"]
        if len(events) >= int(limit["value"]):
            raise ValueError("Zanies month calendar reached its event limit; coverage may be truncated")
        targets = []
        for event in events:
            url = event.get("url", "") if isinstance(event, dict) else ""
            if not isinstance(url, str):
                continue
            parsed = urlparse(url)
            if (
                parsed.scheme == "https"
                and parsed.netloc == urlparse(calendar_url).netloc
                and parsed.path.startswith("/show/")
                and "/category/" not in parsed.path
            ):
                targets.append(url)
        targets = list(dict.fromkeys(targets))
        if events and not targets:
            raise ValueError("Zanies month calendar returned no usable performance links")
        Logger.info(f"{self._log_prefix}: discovered {len(targets)} calendar performance URLs", self.logger_context)
        return targets

    async def get_data(self, url: str) -> Optional[ZaniesPageData]:
        """
        Fetch one page and extract events.

        Detects the page type from the URL:
        - /category/series/... → series page (multiple performances)
        - /show/...            → single-show page (one event)
        """
        try:
            normalized_url = URLUtils.normalize_url(url)
            html = await self.fetch_html(normalized_url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            if "/category/series/" in normalized_url:
                events = ZaniesExtractor.extract_series_events(
                    html,
                    event_url=normalized_url,
                )
            else:
                events = ZaniesExtractor.extract_single_show_events(
                    html,
                    event_url=normalized_url,
                )

            if not events:
                self._warn_empty_extraction(url, html=html)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return ZaniesPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
