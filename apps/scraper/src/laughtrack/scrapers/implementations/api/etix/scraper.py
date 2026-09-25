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

import asyncio
import re
from datetime import date
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)

from .data import EtixPageData
from .extractor import EtixExtractor
from .rockhouse import extract_rockhouse_events_with_conflicts
from .tribe import extract_tribe_events
from .transformer import EtixEventTransformer

_ETIX_VENUE_URL = (
    "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue" "?venue_id={venue_id}&orderBy=1&pageNumber={page}"
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
    "28453": "https://desmoines.funnybone.com/shows/",
    "31603": "https://cleveland.funnybone.com/shows/",
    "31600": "https://tampa.funnybone.com/shows/",
    "31602": "https://vb.funnybone.com/shows/",
}
_ZANIES_NASHVILLE_VENUE_ID = "21745"
_ZANIES_NASHVILLE_HOME_URL = "https://nashville.zanies.com/"
_ETIX_TICKET_HREF_RE = re.compile(
    r'href=["\'](https://www\.etix\.com/ticket/[^"\']+)["\']',
    re.IGNORECASE,
)
_FB_MONTH_DAY_RE = re.compile(r"(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})", re.IGNORECASE)
_FB_SHOW_TIME_RE = re.compile(r"Show:\s*(\d{1,2}(?::\d{2})?)\s*([ap]m)", re.IGNORECASE)
_TITLE_YEAR_PREFIX_RE = re.compile(r"^\s*(\d{4})\s+(.+)$")
_MAX_PAGES = 10


class EtixScraper(BaseScraper):
    """Generic scraper for venues that sell tickets through Etix."""

    key = "etix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(EtixEventTransformer(club))
        self._venue_id = self._extract_venue_id()
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None

    def _extract_venue_id(self) -> str:
        """Extract the Etix venue ID from scraping_url."""
        url = self.club.scraping_url or ""
        if self._is_rockhouse_public_url(url):
            return ""
        # Try venue_id query param
        m = re.search(r"venue_id=(\d+)", url)
        if m:
            return m.group(1)
        # Try /v/{id}/ path segment
        m = re.search(r"/v/(\d+)/", url)
        if m:
            return m.group(1)
        Logger.warn(f"{self._log_prefix}: could not extract venue_id from scraping_url '{url}'")
        return ""

    async def collect_scraping_targets(self) -> List[str]:
        """
        Build paginated Etix URLs.

        Fetches page 1 first to discover the total page count, then
        returns URLs for all pages.
        """
        if self._uses_rockhouse_public_source():
            return [self.club.scraping_url]

        if not self._venue_id:
            Logger.error(
                f"{self._log_prefix}: no venue_id — cannot scrape",
                self.logger_context,
            )
            return []

        page1_url = _ETIX_VENUE_URL.format(venue_id=self._venue_id, page=1)
        if self._uses_laugh_patriot_place_fallback(page1_url):
            return [page1_url]
        if self._uses_funny_bone_fallback(page1_url):
            return [page1_url]

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

    @staticmethod
    def _source_failure(message: str, cause=None) -> DataError:
        error = DataError(message, "etix_calendar", cause)
        error.severity = ErrorSeverity.HIGH
        return error

    def _require_source_html(self, html: Optional[str], url: str) -> str:
        if not html or not html.strip():
            raise self._source_failure(f"Etix mandatory source returned no HTML: {url}")
        signature = _bot_block_reason(html)
        if signature:
            diagnostics = current_diagnostics()
            if diagnostics is not None:
                diagnostics.record_bot_block(signature, source="response_body", stage="direct_fetch")
            raise self._source_failure(f"Etix mandatory source blocked ({signature}): {url}")
        return html

    @staticmethod
    def _verified_rockhouse_empty(html: str) -> bool:
        """Recognize the observed unfiltered Winery Rockhouse empty calendar.

        Plain notice text elsewhere in a maintenance/error page is insufficient.
        Contradictory event cards or active filters make the result untrusted.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        calendar = soup.select_one("#desktopView")
        if calendar is None or soup.select_one(".eventWrapper") is not None:
            return False
        heading = calendar.select_one("h1.rhp-events-page-title")
        notice = calendar.select_one(":scope > .noEventsNotice")
        form = calendar.select_one("form#rhp-bar-form")
        if (
            heading is None
            or heading.get_text(" ", strip=True) != "Upcoming Events"
            or notice is None
            or notice.get_text(" ", strip=True) != "There were no results found."
            or form is None
            or calendar.select_one(".generalView") is None
        ):
            return False
        for selector, expected in (
            ("#rhp_bar_search_box", ""),
            ("#rhp_bar_rhp_month", "0"),
            ("#rhp-bar-just-announced", "0"),
        ):
            field = form.select_one(selector)
            if field is None or field.get("value") != expected:
                return False
        return True

    async def get_data(self, url: str) -> Optional[EtixPageData]:
        """Fetch a page's events, then (opt-in) keep only comedy.

        Mixed-use Etix venues set ``scraping_sources.metadata.comedy_filter`` so
        their concerts/plays/dance don't surface; all-comedy venues leave it
        unset and run the raw path unchanged.
        """
        data = await self._get_data_raw(url)
        # Only a parser-verified empty calendar returns an explicit empty
        # PageData. None remains an unverified or failed mandatory source.
        if data is None:
            raise self._source_failure(f"Etix mandatory source produced no verified events: {url}")
        # Source-reviewed exclusions outrank every positive comedy signal.
        # Match complete normalized titles; never broaden this to substrings.
        excluded = self.club.source_metadata.get("excluded_event_titles", [])
        if not isinstance(excluded, list) or any(not isinstance(title, str) or not title.strip() for title in excluded):
            raise self._source_failure("Etix excluded_event_titles must be a list of nonempty titles")
        normalized = {" ".join(title.casefold().split()) for title in excluded}
        if normalized:
            kept = [event for event in data.event_list if " ".join(event.title.casefold().split()) not in normalized]
            Logger.info(
                f"{self._log_prefix}: source title exclusions removed {len(data.event_list) - len(kept)} events",
                self.logger_context,
            )
            data = EtixPageData(event_list=kept)
        if not self._comedy_filter or not data.event_list:
            return data
        return await self._filter_comedy(data)

    async def _filter_comedy(self, data: EtixPageData) -> Optional[EtixPageData]:
        titles = [e.title for e in data.event_list]
        loop = asyncio.get_running_loop()
        comedy_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                titles,
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                min_popularity=resolve_min_popularity(self.club.source_metadata),
                allowlist=resolve_allowlist(self.club.source_metadata),
            ),
        )
        kept = [e for e in data.event_list if e.title in comedy_titles]
        Logger.info(
            f"{self._log_prefix}: comedy filter kept {len(kept)}/{len(data.event_list)} event(s)",
            self.logger_context,
        )
        if not kept:
            return None
        return EtixPageData(event_list=kept)

    async def _get_data_raw(self, url: str) -> Optional[EtixPageData]:
        """Fetch a single page and extract event cards."""
        try:
            if self._is_rockhouse_public_url(url):
                return await self._get_rockhouse_public_data(url)

            if self._uses_laugh_patriot_place_fallback(url):
                fallback_data = await self._get_laugh_patriot_place_fallback_data()
                if fallback_data and fallback_data.event_list:
                    return fallback_data
                Logger.info(
                    f"{self._log_prefix}: Laugh Patriot Place fallback found no events for {url}",
                    self.logger_context,
                )
                return None

            if self._uses_funny_bone_fallback(url):
                fallback_data = await self._get_funny_bone_fallback_data()
                if fallback_data is not None:
                    return fallback_data
                Logger.info(
                    f"{self._log_prefix}: Funny Bone fallback found no events for {url}",
                    self.logger_context,
                )
                return None

            html = await self._fetch_etix_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            # Keep the existing Nashville recovery path for blocked Etix HTML.
            if self._uses_zanies_nashville_fallback(url) and _bot_block_reason(html):
                return await self._get_zanies_nashville_fallback_data()
            self._require_source_html(html, url)
            events = EtixExtractor.extract_events(html)
            if not events:
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
                f"{self._log_prefix}: error fetching {url}: {type(e).__name__}: {e}",
                self.logger_context,
            )
            if isinstance(e, DataError) and e.severity == ErrorSeverity.HIGH:
                raise
            raise self._source_failure(f"Etix mandatory source failed: {url}: {type(e).__name__}: {e}", e) from e

    def _uses_laugh_patriot_place_fallback(self, url: str) -> bool:
        return (
            not self._datadome_reprobe_enabled()
            and self._venue_id == _LAUGH_PATRIOT_PLACE_VENUE_ID
            and "etix.com/ticket/mvc/online/upcomingEvents/venue" in url
        )

    async def _get_laugh_patriot_place_fallback_data(self) -> Optional[EtixPageData]:
        """Use Laugh Patriot Place's public calendar when Etix is DataDome-blocked."""
        candidates: List[EtixEvent] = []
        for calendar_url, year, month in self._laugh_patriot_place_calendar_targets():
            calendar_html = self._require_source_html(await self.fetch_html(calendar_url), calendar_url)
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
                detail_html = self._require_source_html(await self.fetch_html(event_url), event_url)
                ticket_urls_by_event_url[event_url] = self._extract_laugh_patriot_place_ticket_url(detail_html or "")
            ticket_url = ticket_urls_by_event_url[event_url]
            if not ticket_url:
                Logger.warn(
                    f"{self._log_prefix}: Laugh Patriot Place fallback missing Etix ticket URL "
                    f"for '{event.title}' at {event.event_url}",
                    self.logger_context,
                )
                raise self._source_failure(f"Etix fallback missing mandatory ticket identity: {event_url}")
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
            not self._datadome_reprobe_enabled()
            and self._venue_id in _FUNNY_BONE_FALLBACKS
            and "etix.com/ticket/mvc/online/upcomingEvents/venue" in url
        )

    def _uses_rockhouse_public_source(self) -> bool:
        return self._is_rockhouse_public_url(self.club.scraping_url)

    def _is_rockhouse_public_url(self, url: str) -> bool:
        if not url:
            return False
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        return host not in {"www.etix.com", "etix.com", "event.etix.com"}

    def _uses_zanies_nashville_fallback(self, url: str) -> bool:
        return (
            not self._datadome_reprobe_enabled()
            and self._venue_id == _ZANIES_NASHVILLE_VENUE_ID
            and "etix.com/ticket/mvc/online/upcomingEvents/venue" in url
        )

    async def _get_zanies_nashville_fallback_data(self) -> Optional[EtixPageData]:
        """Use Nashville Zanies' public homepage when Etix is DataDome-blocked."""
        try:
            html = await self.fetch_html(_ZANIES_NASHVILLE_HOME_URL)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: Zanies Nashville fallback fetch failed " f"for {_ZANIES_NASHVILLE_HOME_URL}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: Zanies Nashville fallback returned no HTML " f"for {_ZANIES_NASHVILLE_HOME_URL}",
                self.logger_context,
            )
            return None

        self._require_source_html(html, _ZANIES_NASHVILLE_HOME_URL)
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
        title_el = wrapper.select_one("h2.rhp-event__title--grid, h2.rhp-event__title--list, h2")
        title, title_year = self._clean_zanies_nashville_title(title_el.get_text(" ", strip=True) if title_el else "")
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
        title_el = wrapper.select_one(".rhpEventHeader a, .eventSeriesTitle a, h2.rhp-event__title--grid, h2")
        title, title_year = self._clean_zanies_nashville_title(title_el.get_text(" ", strip=True) if title_el else "")
        event_a = wrapper.select_one(".rhpEventHeader a[href], .eventSeriesTitle a[href], a.url[href]")
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

    def _extract_rockhouse_with_status(self, html: str, url: str) -> List[EtixEvent]:
        events, conflicts = extract_rockhouse_events_with_conflicts(html, date.today())
        if conflicts:
            message = (
                f"Etix source {url} has conflicting performance IDs: {', '.join(sorted(conflicts))}; "
                f"retaining {len(events)} unambiguous events and blocking stale reconciliation"
            )
            Logger.warn(message, self.logger_context)
            diagnostics = current_diagnostics()
            if diagnostics is not None:
                diagnostics.record_fetch_failed()
                diagnostics.record_scrape_error(message)
        return events

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

        self._require_source_html(html, shows_url)
        events = self._extract_rockhouse_with_status(html, shows_url)
        if not events and self._verified_rockhouse_empty(html):
            return EtixPageData(event_list=[])
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

    async def _get_rockhouse_public_data(self, shows_url: str) -> Optional[EtixPageData]:
        """Parse a venue-owned Rockhouse public page configured directly as source_url."""
        try:
            html = await self.fetch_html_bare(shows_url)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: Rockhouse public source fetch failed for {shows_url}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: Rockhouse public source returned no HTML for {shows_url}",
                self.logger_context,
            )
            return None

        self._require_source_html(html, shows_url)
        from bs4 import BeautifulSoup

        if BeautifulSoup(html, "html.parser").select_one("article.tribe-events-calendar-list__event") is not None:
            events = extract_tribe_events(html)
            if not events:
                raise self._source_failure(f"Etix Tribe source produced no verified comedy events: {shows_url}")
            return EtixPageData(event_list=events)

        events = self._extract_rockhouse_with_status(html, shows_url)
        if not events and self._verified_rockhouse_empty(html):
            return EtixPageData(event_list=[])
        if events:
            Logger.info(
                f"{self._log_prefix}: Rockhouse public source extracted {len(events)} events from {shows_url}",
                self.logger_context,
            )
            return EtixPageData(event_list=events)

        Logger.warn(
            f"{self._log_prefix}: Rockhouse public source found no usable events at {shows_url}",
            self.logger_context,
        )
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
    def _zanies_nashville_iso_datetime(date_text: str, time_text: str, title_year: Optional[int]) -> Optional[str]:
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

        year = title_year or DateTimeUtils.infer_year(month, day, today=date.today())

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
