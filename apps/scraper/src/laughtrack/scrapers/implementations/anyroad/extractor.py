"""Extract events from the AnyRoad plugin experiences API.

AnyRoad (app.anyroad.com) is a reusable experiences-booking platform. A venue
embeds a widget keyed by a ``plugin_id``; the widget calls
``/plugins/api/v3/experiences?plugin_id=<id>&page=N`` (Cloudflare-gated, cleared
by curl_cffi browser impersonation). Each experience carries an inline
``schedule`` map of ``{ "YYYY-MM-DD": { "<time>": <availability_count> } }``.

We fan a single experience into one ``JsonLdEvent`` per (date, time) slot so a
recurring show/class becomes one dated show per occurrence — the same shape the
``json_ld`` / ``tock`` extractors produce.

Time caveat: the plugin *summary* endpoint reports a nominal slot time (Rozzie
Square Theater's feed reports a uniform ``9:00 AM`` placeholder for every
occurrence — the real per-slot times live behind the Cloudflare/CORS-gated
booking-availability step the widget only loads on "Book Now"). The schedule
*dates* are accurate; we transform the reported time literally rather than
inventing one. See ``apps/scraper/SCRAPERS.md`` (AnyRoad section).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.event import (
    JsonLdEvent,
    Offer,
    Place,
    PostalAddress,
)
from laughtrack.utilities.domain.show.factory import is_comedy_event

# Accepted schedule time formats, tried in order. AnyRoad reports "9:00 AM";
# we also tolerate 24-hour "HH:MM" in case a venue's feed differs.
_TIME_FORMATS = ("%I:%M %p", "%I:%M%p", "%H:%M")


def extract_anyroad_events(
    experiences: Iterable[dict[str, Any]],
    *,
    timezone: str,
    comedy_filter: bool = False,
) -> list[JsonLdEvent]:
    """Return one JsonLdEvent per (experience, date, time) schedule slot.

    Args:
        experiences: The merged ``experiences.data`` records across all pages,
            each shaped ``{"id", "type", "attributes": {...}}``.
        timezone: IANA tz name for the venue; schedule times are local to it.
        comedy_filter: When True, drop experiences whose name/description do not
            look like comedy (for AnyRoad venues that mix non-comedy experiences).
    """
    events: list[JsonLdEvent] = []
    for record in experiences:
        if not isinstance(record, dict):
            continue
        attrs = record.get("attributes")
        if not isinstance(attrs, dict):
            continue
        events.extend(
            _events_from_experience(attrs, timezone=timezone, comedy_filter=comedy_filter)
        )
    return events


def _events_from_experience(
    attrs: dict[str, Any],
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

    schedule = attrs.get("schedule")
    if not isinstance(schedule, dict) or not schedule:
        return []

    tzinfo = ZoneInfo(timezone)
    location = _location(attrs)
    image = _image(attrs)

    events: list[JsonLdEvent] = []
    for date_str, slots in schedule.items():
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

    parsed_time = None
    for fmt in _TIME_FORMATS:
        try:
            parsed_time = datetime.strptime(time_str, fmt).time()
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
    # AnyRoad exposes only a free-text ``locationInfo`` string per experience;
    # there is no structured address. Store it as the street line so the venue
    # context survives; the club identity supplies the real venue downstream.
    return Place(
        name="",
        address=PostalAddress(
            street_address=_string_value(attrs.get("locationInfo")),
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
