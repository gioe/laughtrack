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
# Funny Bone venues whose Etix venue page is DataDome-blocked but whose
# venue-owned Rockhouse-Partners /shows/ page exposes the same data.
# Add new entries here as `venue_id: "https://<sub>.funnybone.com/shows/"` —
# the parser is shared because every Funny Bone WordPress site uses the
# identical Rockhouse Partners event widget.
_FUNNY_BONE_FALLBACKS: dict[str, str] = {
    "31600": "https://tampa.funnybone.com/shows/",
    "31602": "https://vb.funnybone.com/shows/",
}
_ZANIES_NASHVILLE_VENUE_ID = "21745"
_ZANIES_NASHVILLE_HOME_URL = "https://nashville.zanies.com/"
_ETIX_TICKET_HREF_RE = re.compile(
    r'href=["\'](https://www\.etix\.com/ticket/[^"\']+)["\']',
    re.IGNORECASE,
)
_FB_MONTH_DAY_RE = re.compile(
    r"(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})", re.IGNORECASE
)
_FB_SHOW_TIME_RE = re.compile(
    r"Show:\s*(\d{1,2}(?::\d{2})?)\s*([ap]m)", re.IGNORECASE
)
_FB_MONTH_YEAR_RE = re.compile(r"([A-Za-z]+)\s+(\d{4})")
_TITLE_YEAR_PREFIX_RE = re.compile(r"^\s*(\d{4})\s+(.+)$")
_MAX_PAGES = 10


class EtixScraper(BaseScraper):
    """Generic scraper for venues that sell tickets through Etix."""

    key = "etix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EtixEventTransformer(club))
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
        html = await self._fetch_etix_html(page1_url)
        if not html:
            return [page1_url]

        max_page = min(EtixExtractor.extract_max_page(html), _MAX_PAGES)
        urls = [page1_url]
        for page in range(2, max_page + 1):
            urls.append(_ETIX_VENUE_URL.format(venue_id=self._venue_id, page=page))

        Logger.info(
            f"{self._log_prefix}: discovered {max_page} page(s) of events",
            self.logger_context,
        )
        return urls

    async def get_data(self, url: str) -> Optional[EtixPageData]:
        """Fetch a single page and extract event cards."""
        try:
            html = await self._fetch_etix_html(url)
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
                if self._uses_funny_bone_fallback(url):
                    fallback_data = await self._get_funny_bone_fallback_data()
                    if fallback_data and fallback_data.event_list:
                        return fallback_data
                if self._uses_zanies_nashville_fallback(url):
                    fallback_data = await self._get_zanies_nashville_fallback_data()
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
                ticket_urls_by_event_url[event_url] = (
                    self._extract_laugh_patriot_place_ticket_url(detail_html or "")
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

    def _uses_funny_bone_fallback(self, url: str) -> bool:
        return (
            self._venue_id in _FUNNY_BONE_FALLBACKS
            and "etix.com/ticket/mvc/online/upcomingEvents/venue" in url
        )

    def _uses_zanies_nashville_fallback(self, url: str) -> bool:
        return (
            self._venue_id == _ZANIES_NASHVILLE_VENUE_ID
            and "etix.com/ticket/mvc/online/upcomingEvents/venue" in url
        )

    async def _get_zanies_nashville_fallback_data(self) -> Optional[EtixPageData]:
        """Use Nashville Zanies' public homepage when Etix is DataDome-blocked."""
        try:
            html = await self.fetch_html(_ZANIES_NASHVILLE_HOME_URL)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: Zanies Nashville fallback fetch failed "
                f"for {_ZANIES_NASHVILLE_HOME_URL}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: Zanies Nashville fallback returned no HTML "
                f"for {_ZANIES_NASHVILLE_HOME_URL}",
                self.logger_context,
            )
            return None

        events = self._extract_zanies_nashville_events(html)
        if events:
            Logger.info(
                f"{self._log_prefix}: Zanies Nashville fallback extracted {len(events)} events",
                self.logger_context,
            )
            return EtixPageData(event_list=events)

        Logger.warn(
            f"{self._log_prefix}: Zanies Nashville fallback found no usable events",
            self.logger_context,
        )
        return None

    def _extract_zanies_nashville_events(self, html: str) -> List[EtixEvent]:
        """Parse Nashville Zanies' Rockhouse Partners homepage widgets."""
        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: BeautifulSoup unavailable for Zanies Nashville fallback: {e}",
                self.logger_context,
            )
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[EtixEvent] = []
        seen: set[tuple[str, str]] = set()

        for wrapper in soup.select(".eventWrapper"):
            classes = wrapper.get("class") or []
            if "rhpEventSeries" in classes:
                events.extend(self._zanies_nashville_series_events(wrapper, seen))
            elif "rhpSingleEvent" in classes:
                event = self._zanies_nashville_single_event(wrapper, seen)
                if event is not None:
                    events.append(event)

        return events

    def _zanies_nashville_single_event(self, wrapper, seen: set) -> Optional[EtixEvent]:
        title_el = wrapper.select_one(
            "h2.rhp-event__title--grid, h2.rhp-event__title--list, h2"
        )
        title, title_year = self._clean_zanies_nashville_title(
            title_el.get_text(" ", strip=True) if title_el else ""
        )
        date_el = wrapper.select_one(".eventMonth.singleEventDate, .eventMonth")
        ticket_a = wrapper.select_one('a[href*="etix.com/ticket/"]')
        event_a = wrapper.select_one("a.url[href]")

        if not (title and date_el and ticket_a):
            return None

        time_text = wrapper.get_text(" ", strip=True)
        iso_dt = self._zanies_nashville_iso_datetime(
            date_el.get_text(" ", strip=True),
            time_text,
            title_year,
        )
        if iso_dt is None:
            return None

        ticket_url = ticket_a.get("href", "")
        event_url = event_a.get("href") if event_a else None
        key = (title, iso_dt)
        if key in seen:
            return None
        seen.add(key)
        return EtixEvent(
            title=title,
            start_date=iso_dt,
            time_str=time_text,
            ticket_url=ticket_url,
            event_url=event_url,
        )

    def _zanies_nashville_series_events(self, wrapper, seen: set) -> List[EtixEvent]:
        title_el = wrapper.select_one(
            ".rhpEventHeader a, .eventSeriesTitle a, h2.rhp-event__title--grid, h2"
        )
        title, title_year = self._clean_zanies_nashville_title(
            title_el.get_text(" ", strip=True) if title_el else ""
        )
        event_a = wrapper.select_one(
            ".rhpEventHeader a[href], .eventSeriesTitle a[href], a.url[href]"
        )
        event_url = event_a.get("href") if event_a else None
        if not title:
            return []

        results: List[EtixEvent] = []
        for li in wrapper.select("li.rhp-event-series-individual"):
            date_el = li.select_one(".rhp-event-series-date")
            time_el = li.select_one(".rhp-event-series-time")
            ticket_a = li.select_one('a[href*="etix.com/ticket/"]')
            if not (date_el and ticket_a):
                continue
            time_text = time_el.get_text(" ", strip=True) if time_el else ""
            iso_dt = self._zanies_nashville_iso_datetime(
                date_el.get_text(" ", strip=True),
                time_text,
                title_year,
            )
            if iso_dt is None:
                continue
            ticket_url = ticket_a.get("href", "")
            key = (title, iso_dt)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                EtixEvent(
                    title=title,
                    start_date=iso_dt,
                    time_str=time_text,
                    ticket_url=ticket_url,
                    event_url=event_url,
                )
            )
        return results

    async def _get_funny_bone_fallback_data(self) -> Optional[EtixPageData]:
        """Use a Funny Bone venue's public listing when Etix is DataDome-blocked.

        Every Funny Bone WordPress site exposes a Rockhouse-Partners-on-WordPress
        ``/shows/`` page with title, date, show time, ticket URL
        (etix.com/ticket/p/...), and event URL on a single listing — no detail-page
        round-trips required. The venue's ``shows`` URL is looked up in
        ``_FUNNY_BONE_FALLBACKS`` keyed on the Etix venue id parsed from
        ``scraping_url``.

        ``fetch_html_bare`` is used (not ``fetch_html``) because *.funnybone.com
        is also DataDome-protected: the curl_cffi impersonation fingerprint alone
        clears the challenge, but the application headers ``fetch_html`` adds
        trigger a 403.
        """
        shows_url = _FUNNY_BONE_FALLBACKS.get(self._venue_id)
        if not shows_url:
            return None

        try:
            html = await self.fetch_html_bare(shows_url)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: Funny Bone fallback fetch failed for {shows_url}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: Funny Bone fallback returned no HTML for {shows_url}",
                self.logger_context,
            )
            return None

        events = self._extract_funny_bone_events(html)
        if events:
            Logger.info(
                f"{self._log_prefix}: Funny Bone fallback extracted {len(events)} events from {shows_url}",
                self.logger_context,
            )
            return EtixPageData(event_list=events)

        Logger.warn(
            f"{self._log_prefix}: Funny Bone fallback found no usable events at {shows_url}",
            self.logger_context,
        )
        return None

    def _extract_funny_bone_events(self, html: str) -> List[EtixEvent]:
        """Parse the Rockhouse Partners /shows/ widget shared across Funny Bone venues."""
        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: BeautifulSoup unavailable for Funny Bone fallback: {e}",
                self.logger_context,
            )
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[EtixEvent] = []
        seen: set[tuple[str, str]] = set()
        current_year = date.today().year

        # Walk separators and event wrappers in document order so each
        # event picks up the year context from its preceding "MMMM YYYY" header.
        nodes = soup.select(
            ".rhp-events-list-separator-month, "
            ".rhp-event__single-event--list, "
            ".rhp-event__single-series--list"
        )
        for node in nodes:
            classes = node.get("class") or []
            if "rhp-events-list-separator-month" in classes:
                m = _FB_MONTH_YEAR_RE.search(node.get_text(" ", strip=True))
                if m:
                    try:
                        current_year = int(m.group(2))
                    except ValueError:
                        pass
                continue

            if "rhp-event__single-series--list" in classes:
                events.extend(
                    self._funny_bone_series_events(node, current_year, seen)
                )
            else:
                event = self._funny_bone_single_event(node, current_year, seen)
                if event is not None:
                    events.append(event)

        return events

    def _funny_bone_single_event(
        self, wrapper, year: int, seen: set
    ) -> Optional[EtixEvent]:
        title_el = wrapper.select_one(
            "h2.rhp-event__title--list, .rhp-event__title--list a"
        )
        title = (title_el.get_text(" ", strip=True) if title_el else "").strip()
        date_el = wrapper.select_one(".eventMonth.singleEventDate, .eventMonth")
        time_el = wrapper.select_one(".rhp-event__time-text--list")
        ticket_a = wrapper.select_one('a[href*="etix.com/ticket/p/"]')
        event_a = wrapper.select_one("a.url[href]")

        if not (title and date_el and ticket_a):
            return None

        ticket_url = ticket_a.get("href", "")
        date_text = date_el.get_text(" ", strip=True)
        time_text = time_el.get_text(" ", strip=True) if time_el else ""
        iso_dt = self._funny_bone_iso_datetime(date_text, time_text, year)
        if iso_dt is None:
            return None

        event_url = event_a.get("href") if event_a else None
        key = (title, iso_dt)
        if key in seen:
            return None
        seen.add(key)
        return EtixEvent(
            title=title,
            start_date=iso_dt,
            time_str=time_text,
            ticket_url=ticket_url,
            event_url=event_url,
        )

    def _funny_bone_series_events(
        self, wrapper, year: int, seen: set
    ) -> List[EtixEvent]:
        title_el = wrapper.select_one(
            ".rhpEventHeader a, .eventSeriesTitle a, h2.rhp-event__title--list"
        )
        title = (title_el.get_text(" ", strip=True) if title_el else "").strip()
        event_a = wrapper.select_one(".rhpEventHeader a, .eventSeriesTitle a, a.url[href]")
        event_url = event_a.get("href") if event_a else None
        if not title:
            return []

        results: List[EtixEvent] = []
        for li in wrapper.select("li.rhp-event-series-individual"):
            date_el = li.select_one(".rhp-event-series-date")
            time_el = li.select_one(".rhp-event-series-time")
            ticket_a = li.select_one('a[href*="etix.com/ticket/p/"]')
            if not (date_el and ticket_a):
                continue
            date_text = date_el.get_text(" ", strip=True)
            time_text = time_el.get_text(" ", strip=True) if time_el else ""
            iso_dt = self._funny_bone_iso_datetime(date_text, time_text, year)
            if iso_dt is None:
                continue
            ticket_url = ticket_a.get("href", "")
            key = (title, iso_dt)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                EtixEvent(
                    title=title,
                    start_date=iso_dt,
                    time_str=time_text,
                    ticket_url=ticket_url,
                    event_url=event_url,
                )
            )
        return results

    @staticmethod
    def _funny_bone_iso_datetime(
        date_text: str, time_text: str, year: int
    ) -> Optional[str]:
        """Build an ISO 8601 datetime from "May 07" / "Doors: ... // Show: 7 pm"."""
        from laughtrack.scrapers.implementations.api.etix.extractor import _MONTHS

        m = _FB_MONTH_DAY_RE.search(date_text or "")
        if not m:
            return None
        month_abbr = m.group(1).strip().lower()[:3]
        month = _MONTHS.get(month_abbr)
        if not month:
            return None
        try:
            day = int(m.group(2))
        except ValueError:
            return None

        # Default 8:00 PM matches the date-only fallback in EtixEvent.
        hour, minute = 20, 0
        tm = _FB_SHOW_TIME_RE.search(time_text or "")
        if tm:
            time_part = tm.group(1)
            ampm = tm.group(2).lower()
            if ":" in time_part:
                h_str, m_str = time_part.split(":")
                try:
                    hour = int(h_str)
                    minute = int(m_str)
                except ValueError:
                    return None
            else:
                try:
                    hour = int(time_part)
                except ValueError:
                    return None
                minute = 0
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

        try:
            return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
        except ValueError:
            return None

    @staticmethod
    def _clean_zanies_nashville_title(raw_title: str) -> tuple[str, Optional[int]]:
        title = (raw_title or "").strip()
        m = _TITLE_YEAR_PREFIX_RE.match(title)
        if not m:
            return title, None
        try:
            year = int(m.group(1))
        except ValueError:
            year = None
        return m.group(2).strip(), year

    @staticmethod
    def _zanies_nashville_iso_datetime(
        date_text: str, time_text: str, title_year: Optional[int]
    ) -> Optional[str]:
        from laughtrack.scrapers.implementations.api.etix.extractor import _MONTHS

        m = _FB_MONTH_DAY_RE.search(date_text or "")
        if not m:
            return None
        month_abbr = m.group(1).strip().lower()[:3]
        month = _MONTHS.get(month_abbr)
        if not month:
            return None
        try:
            day = int(m.group(2))
        except ValueError:
            return None

        today = date.today()
        year = title_year or today.year
        if title_year is None:
            try:
                candidate = date(year, month, day)
            except ValueError:
                return None
            if candidate < today:
                year += 1

        hour, minute = 20, 0
        tm = _FB_SHOW_TIME_RE.search(time_text or "")
        if tm:
            time_part = tm.group(1)
            ampm = tm.group(2).lower()
            if ":" in time_part:
                h_str, m_str = time_part.split(":")
                try:
                    hour = int(h_str)
                    minute = int(m_str)
                except ValueError:
                    return None
            else:
                try:
                    hour = int(time_part)
                except ValueError:
                    return None
                minute = 0
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

        try:
            date(year, month, day)
        except ValueError:
            return None
        return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"

    async def _fetch_etix_html(self, url: str) -> Optional[str]:
        """Fetch Etix pages using the shared Etix proxy allowlist key."""
        return await self.fetch_html(url, scraper_key="etix")
