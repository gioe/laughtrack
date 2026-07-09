"""Rockhouse Partners event extraction for Etix-backed public venue pages."""

import re
from datetime import date
from typing import List, Optional

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.foundation.utilities.number import parse_price_text

from .extractor import _MONTHS

_MONTH_DAY_RE = re.compile(
    r"(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})", re.IGNORECASE
)
_SHOW_TIME_RE = re.compile(
    r"Show:\s*(\d{1,2}(?::\d{2})?)\s*([ap]m)", re.IGNORECASE
)
_MONTH_YEAR_RE = re.compile(r"([A-Za-z]+)\s+(\d{4})")


def extract_rockhouse_events(html: str, today: date) -> List[EtixEvent]:
    """Parse the Rockhouse Partners event list widget used by Etix venues."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    events: List[EtixEvent] = []
    seen: set[tuple[str, str]] = set()
    current_year = today.year

    # Walk separators and event wrappers in document order so each event picks
    # up the year context from its preceding "MMMM YYYY" header.
    nodes = soup.select(
        ".rhp-events-list-separator-month, "
        ".rhp-event__single-event--list, "
        ".rhp-event__single-series--list"
    )
    for node in nodes:
        classes = node.get("class") or []
        if "rhp-events-list-separator-month" in classes:
            match = _MONTH_YEAR_RE.search(node.get_text(" ", strip=True))
            if match:
                try:
                    current_year = int(match.group(2))
                except ValueError:
                    pass
            continue

        if "rhp-event__single-series--list" in classes:
            events.extend(_series_events(node, current_year, seen))
        else:
            event = _single_event(node, current_year, seen)
            if event is not None:
                events.append(event)

    return events


def _single_event(wrapper, year: int, seen: set) -> Optional[EtixEvent]:
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
    ticket_price = _ticket_price(wrapper)
    iso_dt = _iso_datetime(date_text, time_text, year)
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
        ticket_price=ticket_price,
    )


def _series_events(wrapper, year: int, seen: set) -> List[EtixEvent]:
    title_el = wrapper.select_one(
        ".rhpEventHeader a, .eventSeriesTitle a, h2.rhp-event__title--list"
    )
    title = (title_el.get_text(" ", strip=True) if title_el else "").strip()
    event_a = wrapper.select_one(".rhpEventHeader a, .eventSeriesTitle a, a.url[href]")
    event_url = event_a.get("href") if event_a else None
    if not title:
        return []

    ticket_price = _ticket_price(wrapper)
    results: List[EtixEvent] = []
    for li in wrapper.select("li.rhp-event-series-individual"):
        date_el = li.select_one(".rhp-event-series-date")
        time_el = li.select_one(".rhp-event-series-time")
        ticket_a = li.select_one('a[href*="etix.com/ticket/p/"]')
        if not (date_el and ticket_a):
            continue
        date_text = date_el.get_text(" ", strip=True)
        time_text = time_el.get_text(" ", strip=True) if time_el else ""
        iso_dt = _iso_datetime(date_text, time_text, year)
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
                ticket_price=ticket_price,
            )
        )
    return results


def _ticket_price(wrapper) -> Optional[float]:
    price_el = wrapper.select_one(
        ".rhp-event__cost-text--list, "
        ".rhp-event__cost-text--grid, "
        ".rhp-event-price"
    )
    if price_el is None:
        return None

    # Targeted cost-text element ("$60 to $100"): shared parser returns the
    # min of the range, matching the old first-$ result for low-first ranges.
    return parse_price_text(price_el.get_text(" ", strip=True))


def _iso_datetime(date_text: str, time_text: str, year: int) -> Optional[str]:
    """Build an ISO 8601 datetime from "May 07" / "Doors: ... // Show: 7 pm"."""
    match = _MONTH_DAY_RE.search(date_text or "")
    if not match:
        return None
    month_abbr = match.group(1).strip().lower()[:3]
    month = _MONTHS.get(month_abbr)
    if not month:
        return None
    try:
        day = int(match.group(2))
    except ValueError:
        return None

    # Default 8:00 PM matches the date-only fallback in EtixEvent.
    hour, minute = 20, 0
    time_match = _SHOW_TIME_RE.search(time_text or "")
    if time_match:
        time_part = time_match.group(1)
        ampm = time_match.group(2).lower()
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
