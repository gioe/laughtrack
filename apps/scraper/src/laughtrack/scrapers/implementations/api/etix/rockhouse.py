"""Rockhouse Partners event extraction for Etix-backed public venue pages."""

import re
from datetime import date, datetime
from typing import List, Optional

from laughtrack.core.entities.event.etix import EtixEvent
from laughtrack.foundation.utilities.number import parse_price_text

from .extractor import _MONTHS

_MONTH_DAY_RE = re.compile(r"(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})", re.IGNORECASE)
_SHOW_TIME_RE = re.compile(r"\bShow\s*[:|]\s*(\d{1,2}(?::\d{2})?)\s*([ap]m)", re.IGNORECASE)
_MONTH_YEAR_RE = re.compile(r"([A-Za-z]+)\s+(\d{4})")
_PRICE_RANGE_RE = re.compile(
    r"\s*\$?\s*([+-]?\d+(?:\.\d{1,2})?)\s*(?:to|[-–—])\s*" r"\$?\s*([+-]?\d+(?:\.\d{1,2})?)\s*", re.IGNORECASE
)


_CARD_CLASSES = {"rhp-event__single-event--list", "rhp-event__single-series--list"}


def extract_rockhouse_events(html: str, today: date) -> List[EtixEvent]:
    """Return only performances with explicit times and consistent identities."""
    events, _ = extract_rockhouse_events_with_conflicts(html, today)
    return events


def extract_rockhouse_events_with_conflicts(
    html: str, today: date
) -> tuple[List[EtixEvent], dict[str, list[dict[str, Optional[str]]]]]:
    """Expose rejected identities so callers can prevent stale-show cleanup.

    A shared Etix performance ID with differing names or dates is source
    corruption, not evidence to choose whichever card happens to appear first.
    """
    groups: dict[str, list[EtixEvent]] = {}
    for event in _extract_candidates(html, today):
        match = re.search(r"/ticket/p/(\d+)(?:/|[?#]|$)", event.ticket_url)
        ident = match.group(1) if match else event.ticket_url
        groups.setdefault(ident, []).append(event)
    safe = []
    conflicts = {}
    for ident, candidates in groups.items():
        identities = {(" ".join(e.title.casefold().split()), e.start_date) for e in candidates}
        if len(identities) == 1:
            safe.append(candidates[0])
        else:
            conflicts[ident] = [
                {"title": e.title, "start_date": e.start_date, "ticket_url": e.ticket_url, "event_url": e.event_url}
                for e in candidates
            ]
    return safe, conflicts


def _owned_elements(wrapper, selector):
    """Exclude fields belonging to a nested event card."""
    return [
        element
        for element in wrapper.select(selector)
        if next((parent for parent in element.parents if _CARD_CLASSES.intersection(parent.get("class") or [])), None)
        is wrapper
    ]


def _owned_one(wrapper, selector):
    return next(iter(_owned_elements(wrapper, selector)), None)


def _extract_candidates(html: str, today: date) -> List[EtixEvent]:
    """Parse the Rockhouse Partners event list widget used by Etix venues."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    events: List[EtixEvent] = []
    seen: set[tuple[str, str, str]] = set()
    current_year = today.year

    # Walk separators and event wrappers in document order so each event picks
    # up the year context from its preceding "MMMM YYYY" header.
    nodes = soup.select(
        ".rhp-events-list-separator-month, " ".rhp-event__single-event--list, " ".rhp-event__single-series--list"
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
    title_el = _owned_one(wrapper, "h2.rhp-event__title--list, .rhp-event__title--list a")
    title = (title_el.get_text(" ", strip=True) if title_el else "").strip()
    date_el = _owned_one(wrapper, ".eventMonth.singleEventDate, .eventMonth")
    time_el = _owned_one(wrapper, ".rhp-event__time-text--list")
    ticket_a = _owned_one(wrapper, 'a[href*="etix.com/ticket/p/"]')
    event_a = _owned_one(wrapper, "a.url[href]")

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
    key = (title, iso_dt, ticket_url.split("?")[0])
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
    title_el = _owned_one(wrapper, ".rhpEventHeader a, .eventSeriesTitle a, h2.rhp-event__title--list")
    title = (title_el.get_text(" ", strip=True) if title_el else "").strip()
    event_a = _owned_one(wrapper, ".rhpEventHeader a, .eventSeriesTitle a, a.url[href]")
    event_url = event_a.get("href") if event_a else None
    if not title:
        return []

    ticket_price = _ticket_price(wrapper)
    results: List[EtixEvent] = []
    for li in _owned_elements(wrapper, "li.rhp-event-series-individual"):
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
        key = (title, iso_dt, ticket_url.split("?")[0])
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
    price_el = _owned_one(wrapper, ".rhp-event__cost-text--list, " ".rhp-event__cost-text--grid, " ".rhp-event-price")
    if price_el is None:
        return None

    text = price_el.get_text(" ", strip=True)
    price_range = _PRICE_RANGE_RE.fullmatch(text.replace(",", ""))
    if price_range:
        low, high = sorted(float(value) for value in price_range.groups())
        # A zero tier may be a companion/child ticket: it does not establish
        # free general admission. Invalid negative ranges are also unknown.
        if low < 0 or low == 0 < high:
            return None
    return parse_price_text(text)


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

    matches = list(_SHOW_TIME_RE.finditer(time_text or ""))
    if len(matches) != 1:
        return None
    time_part, ampm = matches[0].groups()
    parts = time_part.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) == 2 else 0
    if not 1 <= hour <= 12 or not 0 <= minute <= 59:
        return None
    hour = hour % 12 + (12 if ampm.lower() == "pm" else 0)
    try:
        return datetime(year, month, day, hour, minute).isoformat()
    except ValueError:
        return None
