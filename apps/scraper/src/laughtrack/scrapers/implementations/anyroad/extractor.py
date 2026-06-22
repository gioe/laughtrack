"""Extract events from the AnyRoad plugin experiences API.

AnyRoad (app.anyroad.com) is a reusable experiences-booking platform. A venue
embeds a widget keyed by a ``plugin_id``; the widget calls
``/plugins/api/v3/experiences?plugin_id=<id>&page=N`` (Cloudflare-gated, cleared
by curl_cffi browser impersonation) for the experience list (name, price, url,
slug, location, an inline ``schedule`` summary).

Real per-occurrence start times do NOT live in the list endpoint — its inline
``schedule`` reports only a nominal placeholder time (Rozzie's feed reports a
uniform ``9:00 AM`` for every occurrence). The true times (and the *full*
availability calendar) are embedded in each experience's booking detail page
(the experience's ``attributes.url``,
``app.anyroad.com/i/plugin/<plugin_id>/tours/<slug>?lang=en-US``) as a JSON
blob ``"tour_availability":{...,"dates":{"YYYY-MM-DD":{" 6:00pm":<count>}}}``.
That page is also fetchable via curl_cffi impersonation (``fetch_html``).

The scraper fetches each detail page and passes the parsed availability into
:func:`extract_anyroad_events` via ``availability_by_id``; we fan one
``JsonLdEvent`` per (date, time) using the real times, falling back to the
list's placeholder ``schedule`` only when a detail fetch fails. See
``apps/scraper/SCRAPERS.md`` (AnyRoad section).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.event import (
    JsonLdEvent,
    Offer,
    Place,
    PostalAddress,
)
from laughtrack.utilities.domain.show.factory import is_comedy_event

# Accepted slot time formats, tried in order (after upper-casing). The detail
# page reports lower-case " 6:00pm"; the list placeholder reports "9:00 AM"; we
# also tolerate 24-hour "HH:MM" in case a venue's feed differs.
_TIME_FORMATS = ("%I:%M%p", "%I:%M %p", "%H:%M")

_TOUR_AVAILABILITY_KEY = '"tour_availability":'


def extract_tour_availability(detail_html: Optional[str]) -> Optional[dict]:
    """Parse the real availability map from an AnyRoad booking detail page.

    Returns the ``tour_availability.dates`` object
    (``{"YYYY-MM-DD": {"<time>": <count>}}``) embedded as JSON in the detail
    page HTML, or ``None`` if the page has no parseable availability block.
    """
    if not detail_html:
        return None
    start = detail_html.find(_TOUR_AVAILABILITY_KEY)
    if start < 0:
        return None
    # Parse the whole tour_availability object and read its own ``dates`` field,
    # rather than anchoring on the first textual "dates": after the key — the
    # object has a sibling ``cached`` before ``dates`` that could itself nest a
    # ``dates`` key and steal the match.
    brace = detail_html.find("{", start + len(_TOUR_AVAILABILITY_KEY))
    if brace < 0:
        return None
    end = _find_balanced_object_end(detail_html, brace)
    if end is None:
        return None
    try:
        parsed = json.loads(detail_html[brace:end])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    dates = parsed.get("dates")
    return dates if isinstance(dates, dict) else None


def _find_balanced_object_end(text: str, object_start: int) -> Optional[int]:
    depth = 0
    in_string = False
    escaped = False
    for index in range(object_start, len(text)):
        char = text[index]
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


def extract_anyroad_events(
    experiences: Iterable[dict[str, Any]],
    *,
    timezone: str,
    comedy_filter: bool = False,
    availability_by_id: Optional[dict[str, dict]] = None,
) -> list[JsonLdEvent]:
    """Return one JsonLdEvent per (experience, date, time) occurrence.

    Args:
        experiences: The merged ``experiences.data`` records across all pages,
            each shaped ``{"id", "type", "attributes": {...}}``.
        timezone: IANA tz name for the venue; slot times are local to it.
        comedy_filter: When True, drop experiences whose name/description do not
            look like comedy (for AnyRoad venues that mix non-comedy experiences).
        availability_by_id: Optional ``{experience_id: dates_map}`` of real
            per-occurrence times parsed from each experience's detail page (via
            :func:`extract_tour_availability`). When an experience has an entry,
            its real availability is used; otherwise the experience falls back to
            its list ``schedule`` (placeholder time).
    """
    availability_by_id = availability_by_id or {}
    events: list[JsonLdEvent] = []
    for record in experiences:
        if not isinstance(record, dict):
            continue
        attrs = record.get("attributes")
        if not isinstance(attrs, dict):
            continue
        exp_id = _experience_id(record, attrs)
        dates = availability_by_id.get(exp_id) if exp_id else None
        if not isinstance(dates, dict) or not dates:
            dates = attrs.get("schedule")  # placeholder-time fallback
        events.extend(
            _events_from_experience(
                attrs, dates, timezone=timezone, comedy_filter=comedy_filter
            )
        )
    return events


def _experience_id(record: dict[str, Any], attrs: dict[str, Any]) -> Optional[str]:
    raw = record.get("id") or attrs.get("id")
    return str(raw) if raw is not None else None


def _events_from_experience(
    attrs: dict[str, Any],
    dates: Any,
    *,
    timezone: str,
    comedy_filter: bool,
) -> list[JsonLdEvent]:
    name = _string_value(attrs.get("nameTranslation"))
    url = _string_value(attrs.get("url"))
    if not name or not url:
        return []

    description = _string_value(attrs.get("descriptionTranslation"))
    if comedy_filter and not is_comedy_event(name, description):
        return []

    if not isinstance(dates, dict) or not dates:
        return []

    tzinfo = ZoneInfo(timezone)
    location = _location(attrs)
    image = _image(attrs)

    events: list[JsonLdEvent] = []
    for date_str, slots in dates.items():
        if not isinstance(slots, dict):
            continue
        for time_str, count in slots.items():
            start_date = _parse_datetime(date_str, time_str, tzinfo)
            if start_date is None:
                continue
            available = _is_available(count)
            events.append(
                JsonLdEvent(
                    name=name,
                    start_date=start_date,
                    location=location,
                    offers=[_offer(attrs, url=url, available=available)],
                    url=url,
                    description=description,
                    image=image,
                )
            )
    return events


def _parse_datetime(date_str: Any, time_str: Any, tzinfo: ZoneInfo) -> datetime | None:
    date_str = _string_value(date_str)
    time_str = _string_value(time_str)
    if not date_str:
        return None
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    # Detail-page times are lower-case with a leading space (" 6:00pm");
    # upper-case so %p matches regardless of the source's casing.
    normalized_time = time_str.upper()
    parsed_time = None
    for fmt in _TIME_FORMATS:
        try:
            parsed_time = datetime.strptime(normalized_time, fmt).time()
            break
        except (ValueError, TypeError):
            continue
    if parsed_time is None:
        # No usable time signal — keep the (accurate) date at midnight local.
        return day.replace(tzinfo=tzinfo)
    return day.replace(
        hour=parsed_time.hour, minute=parsed_time.minute, tzinfo=tzinfo
    )


def _is_available(count: Any) -> bool:
    try:
        return int(count) > 0
    except (TypeError, ValueError):
        # A truthy non-numeric availability value still signals bookable.
        return bool(count)


def _offer(attrs: dict[str, Any], *, url: str, available: bool) -> Offer:
    if attrs.get("zeroPriced"):
        price = "0.00"
    else:
        raw_price = attrs.get("unformattedPrice")
        try:
            price = f"{float(raw_price):.2f}" if raw_price is not None else ""
        except (TypeError, ValueError):
            price = ""
    return Offer(
        url=url,
        price_currency="USD",
        price=price,
        availability="InStock" if available else "SoldOut",
        name="General Admission",
    )


def _location(attrs: dict[str, Any]) -> Place:
    # AnyRoad exposes only a free-text ``locationInfo`` string per experience
    # (the sub-venue/space, e.g. "18b Corinth Street" or "The Substation");
    # there is no structured address. Carry it as the Place name so the
    # AnyRoadTransformer can map it onto Show.room — that disambiguates
    # experiences at *different* sub-venues sharing a date (AnyRoad's plugin
    # feed reports only a placeholder time, so without a room differentiator
    # the (club, date, room) key would collapse them). The club identity
    # supplies the real venue downstream.
    location_info = _string_value(attrs.get("locationInfo"))
    return Place(
        name=location_info,
        address=PostalAddress(
            street_address=location_info,
            address_locality="",
            address_region="",
            postal_code="",
            address_country="",
        ),
    )


def _image(attrs: dict[str, Any]) -> str | None:
    picture = _string_value(attrs.get("picture"))
    if not picture:
        return None
    if picture.startswith("//"):
        return f"https:{picture}"
    return picture


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
