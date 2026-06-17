"""HTML extraction for the Playhouse Square event feed.

The carbonhouse "showtime" CMS renders each event as an ``m-eventItem`` card:
  - title in ``<h3 class="m-eventItem__title"><a href="/events/detail/<slug>">NAME</a></h3>``
  - date in ``<div class="m-eventItem__date">`` as either a single date
    (``<span class="m-date__singleDate"><span class="m-date__month">Oct </span>
    <span class="m-date__day">22</span><span class="m-date__year">, 2026</span></span>``)
    or a range (``m-date__rangeFirst`` month+day, ``m-date__rangeLast`` day+year)
  - the producing theatre in ``<span class="venue_title">Mimi Ohio Theatre</span>``
  - a box-office ticket link in ``<a class="tickets" href="tickets.playhousesquare.org/...">``

The feed has **no genre/comedy signal** (see comedy_filter.py for how comedy is
isolated). These are pure functions: decoded feed HTML in, ``PlayhouseSquareEvent``
out. For date ranges the range START is taken as the show date.
"""

import re
from html import unescape
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.playhouse_square import PlayhouseSquareEvent


def _clean(text: Optional[str]) -> str:
    # Collapse whitespace and drop the &nbsp; (\xa0) the date delimiter uses.
    return unescape(" ".join((text or "").replace("\xa0", " ").split()))


def _span_text(parent, selector: str) -> str:
    el = parent.select_one(selector) if parent else None
    return _clean(el.get_text()) if el else ""


def _extract_start_date(date_el) -> str:
    """Build a ``"Mon DD, YYYY"`` start-date string from the date spans.

    Handles both the single-date layout (``m-date__singleDate``) and the range
    layout (``m-date__rangeFirst`` + ``m-date__rangeLast``), always returning the
    START of a range. The year lives on the first sub-span when present, else on
    ``m-date__rangeLast``. Returns "" when no date spans are found.
    """
    if not date_el:
        return ""

    single = date_el.select_one(".m-date__singleDate")
    first = single or date_el.select_one(".m-date__rangeFirst")
    if not first:
        return ""

    month = _span_text(first, ".m-date__month").strip(" ,")
    day = _span_text(first, ".m-date__day").strip(" ,")
    year = _span_text(first, ".m-date__year").strip(" ,")
    if not year:
        # Ranges carry the year on the last span ("Aug 29 - 30, 2026").
        last = date_el.select_one(".m-date__rangeLast")
        year = _span_text(last, ".m-date__year").strip(" ,")

    if not (month and day and year):
        return ""
    return f"{month} {day}, {year}"


def extract_events(decoded_html: str, base_url: str) -> List[PlayhouseSquareEvent]:
    """Parse the decoded Playhouse Square feed HTML into PlayhouseSquareEvents.

    ``base_url`` resolves the relative ``/events/detail/<slug>`` hrefs to absolute
    URLs. Cards missing a title, detail link, or parseable date are skipped.
    Duplicate cards (the feed repeats each event's markup for thumb + buttons)
    are de-duplicated by detail href.
    """
    soup = BeautifulSoup(decoded_html or "", "html.parser")
    events: List[PlayhouseSquareEvent] = []
    seen: set = set()

    for item in soup.select("div.m-eventItem"):
        link = item.select_one("h3.m-eventItem__title a")
        if not link:
            continue
        title = _clean(link.get_text())
        href = (link.get("href") or "").strip()
        if not title or not href:
            continue
        if href in seen:
            continue
        seen.add(href)

        date_str = _extract_start_date(item.select_one(".m-eventItem__date"))
        if not date_str:
            continue

        venue_title = _span_text(item, "span.venue_title")

        ticket_url = None
        tix = item.select_one("a.tickets")
        if tix and tix.get("href"):
            ticket_url = tix["href"].strip()

        events.append(
            PlayhouseSquareEvent(
                title=title,
                date_str=date_str,
                show_page_url=urljoin(base_url, href),
                venue_title=venue_title,
                ticket_url=ticket_url,
            )
        )
    return events
