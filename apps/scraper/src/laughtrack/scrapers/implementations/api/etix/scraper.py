"""
Generic Etix venue scraper.

Etix venue pages at https://www.etix.com/ticket/v/{venue_id}/... have a
consistent HTML structure across all venues: microdata (itemprop=startDate),
CSS classes (row performance, performance-name, performance-datetime),
ticket URLs (/ticket/p/{id}/...), and paginated results (20 per page).

The venue_id is extracted from the club's scraping_url, which should be
either:
  - The venue page: https://www.etix.com/ticket/v/35455/drgrins-comedy-club-at-the-bob
  - The API URL with venue_id param: ...?venue_id=35455

A new Etix venue can be onboarded with only a DB row — no Python changes.
"""

import re
from datetime import date
from typing import List, Optional
from urllib.parse import urljoin

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import EtixPageData
from .extractor import EtixExtractor
from .transformer import EtixEventTransformer

_ETIX_VENUE_URL = (
    "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue"
    "?venue_id={venue_id}&orderBy=1&pageNumber={page}"
)
_LAUGH_PATRIOT_PLACE_VENUE_ID = "32411"
_LAUGH_PATRIOT_PLACE_CALENDAR_URL = "https://laughpatriotplace.com/calendar/"
_LAUGH_PATRIOT_PLACE_FALLBACK_MONTHS = 6
_ETIX_TICKET_HREF_RE = re.compile(
    r'href=["\'](https://www\.etix\.com/ticket/[^"\']+)["\']',
    re.IGNORECASE,
)
_MAX_PAGES = 10


class EtixScraper(BaseScraper):
    """Generic scraper for venues that sell tickets through Etix."""

    key = "etix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            EtixEventTransformer(club)
        )
        self._venue_id = self._extract_venue_id()

    def _extract_venue_id(self) -> str:
        """Extract the Etix venue ID from scraping_url."""
        url = self.club.scraping_url or ""
        # Try venue_id query param
        m = re.search(r"venue_id=(\d+)", url)
        if m:
            return m.group(1)
        # Try /v/{id}/ path segment
        m = re.search(r"/v/(\d+)/", url)
        if m:
            return m.group(1)
        Logger.warn(
            f"{self._log_prefix}: could not extract venue_id from scraping_url '{url}'"
        )
        return ""

    async def collect_scraping_targets(self) -> List[str]:
        """
        Build paginated Etix URLs.

        Fetches page 1 first to discover the total page count, then
        returns URLs for all pages.
        """
        if not self._venue_id:
            Logger.error(
                f"{self._log_prefix}: no venue_id — cannot scrape",
                self.logger_context,
            )
            return []

        page1_url = _ETIX_VENUE_URL.format(venue_id=self._venue_id, page=1)
        html = await self.fetch_html(page1_url)
        if not html:
            return [page1_url]

        max_page = min(EtixExtractor.extract_max_page(html), _MAX_PAGES)
        urls = [page1_url]
        for page in range(2, max_page + 1):
            urls.append(
                _ETIX_VENUE_URL.format(venue_id=self._venue_id, page=page)
            )

        Logger.info(
            f"{self._log_prefix}: discovered {max_page} page(s) of events",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[EtixPageData]:
        """Fetch a single page and extract event cards."""
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            events = EtixExtractor.extract_events(html)
            if not events:
                if self._uses_laugh_patriot_place_fallback(url):
                    fallback_data = await self._get_laugh_patriot_place_fallback_data()
                    if fallback_data and fallback_data.event_list:
                        return fallback_data
                Logger.info(
                    f"{self._log_prefix}: no events found on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return EtixPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None

    def _uses_laugh_patriot_place_fallback(self, url: str) -> bool:
        return (
            self._venue_id == _LAUGH_PATRIOT_PLACE_VENUE_ID
            and "etix.com/ticket/mvc/online/upcomingEvents/venue" in url
        )

    async def _get_laugh_patriot_place_fallback_data(self) -> Optional[EtixPageData]:
        """Use Laugh Patriot Place's public calendar when Etix is DataDome-blocked."""
        candidates: List[EtixEvent] = []
        for calendar_url, year, month in self._laugh_patriot_place_calendar_targets():
            calendar_html = await self.fetch_html(calendar_url)
            if not calendar_html:
                Logger.warn(
                    f"{self._log_prefix}: Laugh Patriot Place fallback calendar returned no HTML "
                    f"for {calendar_url}",
                    self.logger_context,
                )
                continue
            candidates.extend(
                self._extract_laugh_patriot_place_calendar_events(
                    calendar_html,
                    year=year,
                    month=month,
                )
            )

        events: List[EtixEvent] = []
        ticket_urls_by_event_url: dict[str, Optional[str]] = {}
        for event in candidates:
            event_url = event.event_url or ""
            if event_url not in ticket_urls_by_event_url:
                detail_html = await self.fetch_html(event_url)
                ticket_urls_by_event_url[event_url] = self._extract_laugh_patriot_place_ticket_url(
                    detail_html or ""
                )
            ticket_url = ticket_urls_by_event_url[event_url]
            if not ticket_url:
                Logger.warn(
                    f"{self._log_prefix}: Laugh Patriot Place fallback missing Etix ticket URL "
                    f"for '{event.title}' at {event.event_url}",
                    self.logger_context,
                )
                continue
            event.ticket_url = ticket_url
            events.append(event)

        if events:
            Logger.info(
                f"{self._log_prefix}: Laugh Patriot Place fallback extracted {len(events)} events",
                self.logger_context,
            )
            return EtixPageData(event_list=events)

        Logger.warn(
            f"{self._log_prefix}: Laugh Patriot Place fallback found no usable events",
            self.logger_context,
        )
        return None

    def _laugh_patriot_place_calendar_targets(self) -> List[tuple[str, int, int]]:
        today = date.today()
        targets: List[tuple[str, int, int]] = []
        for offset in range(_LAUGH_PATRIOT_PLACE_FALLBACK_MONTHS):
            month_index = today.month - 1 + offset
            year = today.year + month_index // 12
            month = month_index % 12 + 1
            if offset == 0:
                url = _LAUGH_PATRIOT_PLACE_CALENDAR_URL
            else:
                url = f"{_LAUGH_PATRIOT_PLACE_CALENDAR_URL}?cal_year={year}&month={month}"
            targets.append((url, year, month))
        return targets

    def _extract_laugh_patriot_place_calendar_events(
        self,
        html: str,
        *,
        year: int,
        month: int,
    ) -> List[EtixEvent]:
        """Extract event title/date/public URL from the venue-owned WordPress calendar."""
        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: BeautifulSoup unavailable for Laugh Patriot Place fallback: {e}",
                self.logger_context,
            )
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[EtixEvent] = []
        seen: set[tuple[str, str, str]] = set()

        for cell in soup.select("td.has-events"):
            if cell.select_one(".post-details.disable-events"):
                continue
            day_el = cell.select_one(".calendar-date")
            title_el = cell.select_one("h3")
            link_el = cell.select_one('a.btn[href*="/shows/"]')
            if not (day_el and title_el and link_el):
                continue

            try:
                event_day = int(day_el.get_text(strip=True))
                event_date = date(year, month, event_day).isoformat()
            except (TypeError, ValueError):
                continue

            title = title_el.get_text(" ", strip=True)
            event_url = urljoin(_LAUGH_PATRIOT_PLACE_CALENDAR_URL, link_el["href"])
            key = (title, event_date, event_url)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                EtixEvent(
                    title=title,
                    start_date=event_date,
                    time_str="",
                    ticket_url="",
                    event_url=event_url,
                )
            )

        return events

    def _extract_laugh_patriot_place_ticket_url(self, html: str) -> Optional[str]:
        match = _ETIX_TICKET_HREF_RE.search(html or "")
        return match.group(1) if match else None
