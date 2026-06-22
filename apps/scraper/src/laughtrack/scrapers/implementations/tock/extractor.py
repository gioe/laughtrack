"""Extract events from Tock's rendered Redux calendar state."""

from __future__ import annotations

import json
import re
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
    experiences = (
        state.get("calendar", {})
        .get("offerings", {})
        .get("experience", [])
    )
    if not isinstance(experiences, list):
        return []

    events: list[JsonLdEvent] = []
    events.extend(
        _recurring_events_from_experiences(
            state,
            experiences,
            source_url=source_url,
            timezone=timezone,
            comedy_filter=comedy_filter,
        )
    )
    for raw in experiences:
        if not isinstance(raw, dict):
            continue
        event = _event_from_experience(raw, source_url=source_url, timezone=timezone)
        if event is None:
            continue
        if comedy_filter and not is_comedy_event(event.name, event.description):
            continue
        events.append(event)
    return events


def _recurring_events_from_experiences(
    state: dict[str, Any],
    experiences: list[Any],
    *,
    source_url: str,
    timezone: str,
    comedy_filter: bool,
) -> list[JsonLdEvent]:
    calendar = state.get("calendar", {})
    offerings = calendar.get("offerings", {}) if isinstance(calendar, dict) else {}
    dates = _string_list(calendar.get("openDate")) or _string_list(offerings.get("openDate"))
    times = _string_list(calendar.get("openTime")) or _string_list(offerings.get("openTime"))
    if not dates or not times:
        return []

    recurring = [raw for raw in experiences if isinstance(raw, dict) and raw.get("type") == "PRIX_FIXE"]
    if not recurring:
        return []

    name = _recurring_event_name(state, recurring)
    description = "\n\n".join(
        value for value in (_string_value(raw.get("description")) for raw in recurring) if value
    )
    if comedy_filter and not is_comedy_event(name, description):
        return []

    location = _location_from_details(_first_details(recurring))
    offers = [
        offer
        for raw in recurring
        if (offer := _offer_from_recurring_experience(raw, source_url=source_url)) is not None
    ]
    if not offers:
        offers = [Offer(url=source_url, price_currency="USD", price="", availability="InStock")]

    events: list[JsonLdEvent] = []
    for date in dates:
        for start_time in times:
            try:
                start_date = datetime.fromisoformat(f"{date}T{start_time}").replace(
                    tzinfo=ZoneInfo(timezone)
                )
            except (ValueError, TypeError):
                continue
            events.append(
                JsonLdEvent(
                    name=name,
                    start_date=start_date,
                    location=location,
                    offers=offers,
                    url=source_url,
                    description=description,
                )
            )
    return events


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
        r'"onClose":function noop\(\) \{.*?\}',
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


def _recurring_event_name(state: dict[str, Any], experiences: list[dict[str, Any]]) -> str:
    business = state.get("app", {}).get("config", {}).get("business", {})
    business_name = _string_value(business.get("name")) if isinstance(business, dict) else ""
    if business_name:
        return business_name

    names = [_string_value(raw.get("name")) for raw in experiences]
    names = [name for name in names if name]
    if not names:
        return "Tock Event"

    prefixes = [name.split(" - ", 1)[0].strip() for name in names if " - " in name]
    if prefixes and len(set(prefixes)) == 1:
        return prefixes[0]
    return names[0]


def _first_details(experiences: list[dict[str, Any]]) -> dict[str, Any]:
    for raw in experiences:
        details = raw.get("eventDetails")
        if isinstance(details, dict):
            return details
    return {}


def _offer_from_recurring_experience(raw: dict[str, Any], *, source_url: str) -> Offer | None:
    name = _string_value(raw.get("name")) or "General Admission"
    price_cents = _price_cents_from_recurring_experience(raw)
    price = f"{price_cents / 100:.2f}" if price_cents is not None else ""
    return Offer(
        url=_event_url(source_url, event_id=raw.get("id"), slug=_string_value(raw.get("slug"))),
        price_currency="USD",
        price=price,
        availability="InStock" if raw.get("state") == "AVAILABLE" else "SoldOut",
        name=name,
    )


def _price_cents_from_recurring_experience(raw: dict[str, Any]) -> int | None:
    for path in (
        ("ticketPriceInformation", "amountCents"),
        ("price", "pricePerPerson", "minCents"),
        ("price", "partyRangeConfigs", 0, "ticketPriceInformation", "amountCents"),
    ):
        value: Any = raw
        for part in path:
            if isinstance(part, int):
                if not isinstance(value, list) or len(value) <= part:
                    value = None
                    break
                value = value[part]
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


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
    try:
        price = f"{int(price_cents or 0) / 100:.2f}"
    except (TypeError, ValueError):
        price = ""

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


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_string_value(value)]
    if not isinstance(value, list):
        return []
    return [item for item in (_string_value(item) for item in value or []) if item]
