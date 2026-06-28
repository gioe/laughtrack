"""HTML extraction for the Coral Springs Center for the Arts venue scraper.

Two phases:

1. :meth:`extract_comedy_detail_urls` parses the server-rendered, category-filtered
   comedy listing (``/events/category/comedy``) into the set of per-event detail
   page URLs. The listing is already comedy-only (the venue's CMS filters
   server-side); extraction is additionally **scoped to the ``.eventItem`` result
   cards** (the per-event tiles inside the ``.eventList`` wrapper) so a future
   featured/related/nav widget elsewhere on the page can't surface a non-comedy
   ``/events/detail`` link that would be persisted as comedy (parse_detail does no
   genre re-check — the comedy signal is the listing page itself). Falls back to a
   whole-document scan (with a warning) if the card markup ever disappears, so a
   CMS rename degrades to the old behavior instead of silently zeroing the venue.
2. :meth:`parse_detail` parses one ``/events/detail/<slug>`` page — the source of
   truth for the title (``<h1 class="title">``), the performance date(s) (the
   ``m-date__month`` / ``m-date__day`` / ``m-date__year`` spans), the showtime and
   the eVenue buy link. A single-night page repeats the same date across several
   ``.m-date__singleDate`` blocks, so dates are de-duplicated; a multi-night
   engagement carries distinct dates across blocks and yields one event per date.
"""

import html as _html
import re
from datetime import date, datetime
from typing import List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.coral_springs_center import (
    CoralSpringsCenterEvent,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger

_DETAIL_PATH_RE = re.compile(r'/events/detail/[a-z0-9][a-z0-9-]*', re.IGNORECASE)
# Standalone fallbacks (used only when a detail page lacks .m-date__singleDate
# wrappers, e.g. after a markup change) — first-match single date, original behavior.
_MONTH_RE = re.compile(r'class="m-date__month"[^>]*>\s*([A-Za-z]{3,9})', re.IGNORECASE)
_DAY_RE = re.compile(r'class="m-date__day"[^>]*>\s*(\d{1,2})', re.IGNORECASE)
_YEAR_RE = re.compile(r'class="m-date__year"[^>]*>\s*,?\s*(\d{4})', re.IGNORECASE)
_TIME_RE = re.compile(r'(\d{1,2}:\d{2}\s*[AP]M)', re.IGNORECASE)
_TICKET_RE = re.compile(
    r'https://thecenter\.evenue\.net/cgi-bin/ncommerce3/SEGetEventInfo\?[^"\'<>\s]+',
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _extract_showtime(detail_html: str, default: str = "7:30PM") -> str:
    """Return the most likely SHOW time on a detail page.

    The CMS repeats the show time across the title, date line and buy button
    while listing the doors time at most once, so the most-frequent time is the
    show time. This is more robust than first/last-match, which would pick the
    doors time whenever it happens to appear first.
    """
    times = [re.sub(r'\s+', '', t).upper() for t in _TIME_RE.findall(detail_html)]
    if not times:
        # Fabricating a wall-clock is worse than dropping it silently — log so a
        # markup change that breaks time parsing surfaces instead of quietly
        # emitting fabricated default-time shows.
        Logger.warn(
            f"CoralSpringsCenterExtractor: no showtime parsed; defaulting to {default}"
        )
        return default
    counts: dict = {}
    for t in times:
        counts[t] = counts.get(t, 0) + 1
    # Highest count wins; ties broken by first appearance order.
    return max(times, key=lambda t: (counts[t], -times.index(t)))


class CoralSpringsCenterExtractor:
    """Pure HTML parsing for Coral Springs Center for the Arts."""

    @staticmethod
    def extract_comedy_detail_urls(listing_html: str, base_url: str) -> List[str]:
        """Return absolute detail-page URLs from the comedy-category listing.

        Scoped to the ``.eventItem`` result cards so only the comedy listing tiles
        contribute links; a featured/related/nav widget elsewhere on the page is
        ignored. Falls back to a whole-document scan (with a warning) when the card
        markup is absent. Detail hrefs may be absolute or root-relative — the path
        is extracted either way.
        """
        origin = re.match(r'https?://[^/]+', base_url)
        prefix = origin.group(0) if origin else "https://www.thecentercs.com"

        soup = BeautifulSoup(listing_html or "", "html.parser")
        cards = soup.select(".eventItem")
        if cards:
            anchors = [a for card in cards for a in card.find_all("a", href=True)]
        else:
            Logger.warn(
                "CoralSpringsCenterExtractor: no .eventItem result cards found — "
                "falling back to whole-document detail-link scan"
            )
            anchors = soup.find_all("a", href=True)

        seen: set = set()
        urls: List[str] = []
        for anchor in anchors:
            match = _DETAIL_PATH_RE.search(anchor.get("href") or "")
            if not match:
                continue
            url = f"{prefix}{match.group(0)}"
            if url not in seen:
                seen.add(url)
                urls.append(url)
        return urls

    @staticmethod
    def _extract_performance_dates(soup: BeautifulSoup, detail_html: str) -> List[date]:
        """Return the distinct, sorted performance dates on a detail page.

        Reads each ``.m-date__singleDate`` block's month/day/year, de-duplicating
        the repeated single-night blocks and surfacing every night of a
        multi-night engagement. Falls back to a first-match single date when no
        ``.m-date__singleDate`` wrappers are present (markup change resilience).
        """
        seen: set = set()
        dates: List[date] = []
        for block in soup.select(".m-date__singleDate"):
            month_el = block.select_one(".m-date__month")
            day_el = block.select_one(".m-date__day")
            year_el = block.select_one(".m-date__year")
            if not (month_el and day_el and year_el):
                continue  # e.g. the weekday-only block — its date is covered elsewhere
            month = _MONTHS.get(month_el.get_text(strip=True)[:3].lower())
            day_digits = re.sub(r"\D", "", day_el.get_text())
            year_digits = re.sub(r"\D", "", year_el.get_text())
            if not (month and day_digits and year_digits):
                continue
            try:
                parsed = date(int(year_digits), month, int(day_digits))
            except ValueError:
                continue
            if parsed not in seen:
                seen.add(parsed)
                dates.append(parsed)

        if dates:
            return sorted(dates)

        # Fallback: standalone first-match (no .m-date__singleDate wrappers).
        month_match = _MONTH_RE.search(detail_html)
        day_match = _DAY_RE.search(detail_html)
        year_match = _YEAR_RE.search(detail_html)
        if not (month_match and day_match and year_match):
            return []
        month = _MONTHS.get(month_match.group(1)[:3].lower())
        if not month:
            return []
        try:
            return [date(int(year_match.group(1)), month, int(day_match.group(1)))]
        except ValueError:
            return []

    @staticmethod
    def parse_detail(detail_html: str, detail_url: str) -> List[CoralSpringsCenterEvent]:
        """Parse a detail page into one event per upcoming performance date.

        Returns an empty list when the page is unparseable or every performance is
        in the past. A single-night show yields one event; a multi-night
        engagement yields one event per distinct upcoming date.
        """
        if not detail_html:
            return []

        soup = BeautifulSoup(detail_html, "html.parser")
        title_el = soup.select_one("h1.title")
        if not title_el:
            return []
        name = _html.unescape(title_el.get_text(" ", strip=True)).strip()
        if not name:
            return []

        dates = CoralSpringsCenterExtractor._extract_performance_dates(soup, detail_html)
        if not dates:
            return []

        start_time = _extract_showtime(detail_html)
        ticket_match = _TICKET_RE.search(detail_html)
        ticket_url = _html.unescape(ticket_match.group(0)) if ticket_match else None

        today = datetime.now().date()
        events: List[CoralSpringsCenterEvent] = []
        for event_date in dates:
            if event_date < today:  # be defensive — the listing is already upcoming
                continue
            events.append(
                CoralSpringsCenterEvent(
                    name=name,
                    start_date=event_date.isoformat(),
                    start_time=start_time,
                    detail_url=detail_url,
                    ticket_url=ticket_url,
                )
            )
        return events

    @staticmethod
    def extract_events(
        listing_html: str,
        base_url: str,
        detail_pages: dict,
    ) -> List[CoralSpringsCenterEvent]:
        """Build events from the listing + a {detail_url: html} map (test entrypoint)."""
        events: List[CoralSpringsCenterEvent] = []
        for url in CoralSpringsCenterExtractor.extract_comedy_detail_urls(listing_html, base_url):
            html_content = detail_pages.get(url)
            if not html_content:
                Logger.warn(f"CoralSpringsCenterExtractor: no detail HTML for {url}")
                continue
            events.extend(CoralSpringsCenterExtractor.parse_detail(html_content, url))
        return events
