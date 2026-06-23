"""Extraction helpers for public FareHarbor item and calendar JSON."""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .data import FareHarborEvent

_DEFAULT_OPERATIONAL_KEYWORDS = frozenset(
    {
        "class",
        "classes",
        "donation",
        "gift card",
        "gift certificate",
        "practice",
        "workshop",
    }
)
_RATE_RE = re.compile(
    r"(?:rates?|tickets?|admission)[^$\n\r]{0,80}\$(?P<price>\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_ANY_PRICE_RE = re.compile(r"\$(?P<price>\d+(?:\.\d{1,2})?)")


def extract_items(payload: Any) -> list[dict[str, Any]]:
    """Return item dictionaries from the public company items payload."""
    if isinstance(payload, dict):
        raw_items = payload.get("items") or []
    elif isinstance(payload, list):
        raw_items = payload
    else:
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def item_is_operational(
    item: dict[str, Any],
    *,
    excluded_item_pks: Iterable[int] = (),
    allowed_item_pks: Optional[Iterable[int]] = None,
    operational_keywords: Iterable[str] = _DEFAULT_OPERATIONAL_KEYWORDS,
) -> bool:
    """Return True for non-show FareHarbor products that should be skipped."""
    pk = _int_or_none(item.get("pk"))
    if pk is not None and allowed_item_pks is not None:
        return pk not in set(allowed_item_pks)
    if pk is not None and pk in set(excluded_item_pks):
        return True

    name = _clean_text(item.get("name"))
    headline = _clean_text(item.get("headline"))
    haystack = f"{name} {headline}".lower()
    return any(keyword.lower() in haystack for keyword in operational_keywords)


def extract_events_from_calendar(
    calendar_payload: Any,
    *,
    item: dict[str, Any],
    base_url: str = "https://fareharbor.com",
) -> List[FareHarborEvent]:
    """Extract one event per availability from a FareHarbor calendar payload."""
    calendar = calendar_payload.get("calendar") if isinstance(calendar_payload, dict) else None
    if not isinstance(calendar, dict):
        return []

    title = _clean_text(item.get("name")) or "Comedy Show"
    description = _description_from_item(item)
    price = _price_from_item(item)

    events: List[FareHarborEvent] = []
    for week in calendar.get("weeks") or []:
        if not isinstance(week, dict):
            continue
        for day in week.get("days") or []:
            if not isinstance(day, dict):
                continue
            for availability in day.get("availabilities") or []:
                if not isinstance(availability, dict):
                    continue
                start_at = _clean_text(availability.get("start_at"))
                book_url = _clean_text(availability.get("book_url"))
                if not start_at or not book_url:
                    continue
                headline = _clean_text(
                    availability.get("headline")
                    or availability.get("custom_headline")
                    or availability.get("availability_headline")
                )
                event_title = f"{title}: {headline}" if headline else title
                events.append(
                    FareHarborEvent(
                        title=event_title,
                        start_at=start_at,
                        utc_start_at=_clean_text(availability.get("utc_start_at")) or None,
                        show_page_url=urljoin(base_url, book_url),
                        price=price,
                        description=description,
                        sold_out=bool(availability.get("is_sold_out")),
                    )
                )
    return events


def _description_from_item(item: dict[str, Any]) -> Optional[str]:
    raw = _clean_text(item.get("description_text")) or _clean_text(item.get("description"))
    if not raw:
        return None
    text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _price_from_item(item: dict[str, Any]) -> Optional[float]:
    text = "\n".join(
        value
        for value in (
            _clean_text(item.get("headline")),
            _clean_text(item.get("description")),
            _clean_text(item.get("description_text")),
        )
        if value
    )
    for pattern in (_RATE_RE, _ANY_PRICE_RE):
        match = pattern.search(text)
        if match:
            try:
                return float(match.group("price"))
            except ValueError:
                return None
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
