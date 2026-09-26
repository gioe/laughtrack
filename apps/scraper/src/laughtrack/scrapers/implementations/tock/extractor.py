"""Extract events from Tock's rendered Redux calendar state."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import datetime
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.event import (
    JsonLdEvent,
    Offer,
    Place,
    PostalAddress,
)
from laughtrack.utilities.domain.show.factory import is_comedy_event
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger

_REDUX_MARKER = "window.$REDUX_STATE"


def extract_tock_events(
    html: str,
    *,
    source_url: str,
    timezone: str,
    comedy_filter: bool = False,
) -> list[JsonLdEvent]:
    """Return Tock GA events from a rendered business page."""
    state = _extract_redux_state(html)
    calendar = state.get("calendar")
    offerings = calendar.get("offerings") if isinstance(calendar, dict) else None
    experiences = offerings.get("experience") if isinstance(offerings, dict) else None
    if not isinstance(experiences, list) or not experiences:
        # Empty Redux initialization is not proof of a loaded empty calendar.
        raise ValueError("Missing, malformed or unverified empty Tock calendar")

    events: list[JsonLdEvent] = []
    unsupported: set[str] = set()
    for raw in experiences:
        if not isinstance(raw, dict):
            raise ValueError("Malformed Tock experience")
        if raw.get("type") != "GA_EVENT":
            unsupported.add(str(raw.get("type") or "unknown experience"))
            continue
        event = _event_from_experience(raw, source_url=source_url, timezone=timezone)
        if event is None:
            raise ValueError("Incomplete Tock GA event")
        if comedy_filter and not is_comedy_event(event.name, event.description):
            diagnostics = current_diagnostics()
            if diagnostics is not None:
                diagnostics.add_items_before_filter(1)
            continue
        expanded, incomplete = _explicit_ga_dates(raw, event, timezone=timezone)
        events.extend(expanded)
        if incomplete:
            unsupported.add("GA recurrence rule without explicit dates")

    if unsupported:
        message = "Unverified Tock recurring/unsupported availability: " + ", ".join(sorted(unsupported))
        if not events:
            raise ValueError(message)
        # Keep independently verified GA shows, but never reconcile a partial feed.
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_fetch_failed()
            diagnostics.record_scrape_error(message)
        Logger.warn(message)
    return events


def _explicit_ga_dates(
    raw: dict[str, Any], event: JsonLdEvent, *, timezone: str
) -> tuple[list[JsonLdEvent], bool]:
    """Expand dates/slots belonging to this GA experience, never business filters."""
    details = raw["eventDetails"]
    schedule = details.get("schedule")
    if not schedule:
        return [event], False
    if not isinstance(schedule, list):
        raise ValueError("Malformed Tock GA schedule")
    dates: set[str] = set()
    incomplete = False
    for group in schedule:
        if not isinstance(group, dict) or not isinstance(group.get("date", []), list):
            raise ValueError("Malformed Tock GA scheduled dates")
        if group.get("repetition"):
            incomplete = True
        for item in group.get("date", []):
            value = _string_value(item.get("date")) if isinstance(item, dict) else ""
            if not value:
                raise ValueError("Missing Tock GA scheduled date")
            dates.add(value)
    if not dates:
        return [event], incomplete
    slots = details.get("slots")
    if not isinstance(slots, list) or not slots:
        raise ValueError("Missing Tock GA schedule slots")
    times = {_string_value(slot.get("startTime")) if isinstance(slot, dict) else "" for slot in slots}
    if "" in times:
        raise ValueError("Invalid Tock GA schedule slot")
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()
    events = []
    for date in sorted(dates):
        for start_time in sorted(times):
            start = datetime.fromisoformat(f"{date}T{start_time}").replace(tzinfo=tz)
            if start.date() >= today:
                events.append(replace(event, start_date=start))
    return events, incomplete


def _extract_redux_state(html: str) -> dict[str, Any]:
    marker_index = html.find(_REDUX_MARKER)
    if marker_index < 0:
        return {}

    object_start = html.find("{", marker_index)
    if object_start < 0:
        return {}

    object_end = _find_balanced_object_end(html, object_start)
    if object_end is None:
        return {}

    raw_state = html[object_start:object_end]
    raw_state = re.sub(r":undefined(?=[,}\]])", ":null", raw_state)
    raw_state = re.sub(
        r'"onClose":function noop\((?:\.\.\._)?\) \{.*?\}',
        '"onClose":null',
        raw_state,
        flags=re.S,
    )
    try:
        parsed = json.loads(raw_state)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _find_balanced_object_end(text: str, object_start: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False

    for index, char in enumerate(text[object_start:], start=object_start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1

    return None


def _event_from_experience(
    raw: dict[str, Any],
    *,
    source_url: str,
    timezone: str,
) -> JsonLdEvent | None:
    if raw.get("type") != "GA_EVENT":
        return None

    name = _string_value(raw.get("name"))
    event_id = raw.get("id")
    slug = _string_value(raw.get("slug"))
    details = raw.get("eventDetails") if isinstance(raw.get("eventDetails"), dict) else {}
    date = _string_value(details.get("date"))
    start_time = _string_value(details.get("startTime") or details.get("time"))
    if not name or not event_id or not date or not start_time:
        return None

    try:
        start_date = datetime.fromisoformat(f"{date}T{start_time}").replace(
            tzinfo=ZoneInfo(timezone)
        )
    except (ValueError, TypeError):
        return None

    event_url = _event_url(source_url, event_id=event_id, slug=slug)
    description = _string_value(raw.get("description"))

    return JsonLdEvent(
        name=name,
        start_date=start_date,
        location=_location_from_details(details),
        offers=[_offer_from_details(details, event_url=event_url, state=raw.get("state"))],
        url=event_url,
        description=description,
    )


def _event_url(source_url: str, *, event_id: Any, slug: str) -> str:
    base = source_url.rstrip("/") + "/"
    path = f"event/{event_id}"
    if slug:
        path = f"{path}/{slug}"
    return urljoin(base, path)


def _location_from_details(details: dict[str, Any]) -> Place:
    raw_location = details.get("location")
    location = raw_location if isinstance(raw_location, dict) else {}
    return Place(
        name=_string_value(location.get("name")),
        address=PostalAddress(
            street_address=_string_value(location.get("address")),
            address_locality=_string_value(location.get("city")),
            address_region=_string_value(location.get("state")),
            postal_code=_string_value(location.get("zipCode")),
            address_country=_string_value(location.get("country")),
        ),
    )


def _offer_from_details(details: dict[str, Any], *, event_url: str, state: Any) -> Offer:
    price_cents = details.get("priceCents")
    valid_cents = (type(price_cents) is int and price_cents >= 0) or (
        isinstance(price_cents, str) and price_cents.isdigit()
    )
    price = f"{int(price_cents) / 100:.2f}" if valid_cents else ""

    availability = "InStock" if state == "AVAILABLE" else "SoldOut"
    return Offer(
        url=event_url,
        price_currency="USD",
        price=price,
        availability=availability,
        name="General Admission",
    )


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
