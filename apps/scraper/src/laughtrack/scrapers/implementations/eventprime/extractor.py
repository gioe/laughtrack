"""Extract events from the EventPrime WordPress plugin API.

EventPrime is a common WordPress events plugin that exposes a public,
unauthenticated REST endpoint at
``<site>/wp-json/eventprime/v1/get_events`` returning::

    {"status": "success", "count": N, "events": [ {event}, ... ]}

Each event carries ``id``, ``title``, ``slug``, ``content`` (HTML), ``status``
(``"publish"`` when live), ``permalink`` (the public show page), ``image_url``,
``start_date`` / ``end_date`` (ISO-8601, usually with a UTC offset),
``timezone``, ``venue``, ``tickets`` (``[{name, price, capacity}]``), and
``event_types``.

The endpoint returns the venue's *entire* event history (past + future), so we
drop past occurrences here — only upcoming shows are emitted. ``content`` is
full HTML, so it is stripped to plain text for the show description.
"""

from __future__ import annotations

from datetime import datetime, timezone as _tz
from typing import Any, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.event import (
    JsonLdEvent,
    Offer,
    Place,
    PostalAddress,
)
from laughtrack.foundation.utilities.html.utils import HtmlUtils
from laughtrack.utilities.domain.show.factory import is_comedy_event


def extract_eventprime_events(
    payload: Any,
    *,
    timezone: str,
    comedy_filter: bool = False,
    include_past: bool = False,
) -> list[JsonLdEvent]:
    """Return one JsonLdEvent per upcoming published EventPrime event.

    Args:
        payload: The decoded ``get_events`` JSON (``{"events": [...]}``).
        timezone: IANA tz name for the venue; used to localize any naive
            ``start_date`` and to evaluate whether an event is in the past.
        comedy_filter: When True, drop events whose title/description do not look
            like comedy (for mixed-use venues running EventPrime).
        include_past: When True, keep past events (default drops them — the API
            returns the venue's full history).
    """
    events_raw = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events_raw, list):
        return []

    tzinfo = ZoneInfo(timezone)
    now = datetime.now(_tz.utc)

    events: list[JsonLdEvent] = []
    for raw in events_raw:
        if not isinstance(raw, dict):
            continue
        if _string_value(raw.get("status")) not in ("", "publish"):
            continue  # drafts/trash/private

        name = _string_value(raw.get("title"))
        url = _string_value(raw.get("permalink"))
        if not name or not url:
            continue

        start_date = _parse_datetime(raw.get("start_date"), tzinfo)
        if start_date is None:
            continue
        if not include_past and start_date.astimezone(_tz.utc) < now:
            continue

        description = HtmlUtils.strip_tags(raw.get("content"), normalize_whitespace=True)
        if comedy_filter and not is_comedy_event(name, description):
            continue

        events.append(
            JsonLdEvent(
                name=name,
                start_date=start_date,
                location=_location(raw),
                offers=_offers(raw, url=url),
                url=url,
                description=description,
                image=_string_value(raw.get("image_url")) or None,
            )
        )
    return events


def _parse_datetime(value: Any, tzinfo: ZoneInfo) -> Optional[datetime]:
    text = _string_value(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None
    # Naive EventPrime timestamps are local to the venue; tz-aware ones already
    # carry the correct UTC offset.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzinfo)
    return dt


def _offers(raw: dict[str, Any], *, url: str) -> list[Offer]:
    tickets = raw.get("tickets")
    if not isinstance(tickets, list) or not tickets:
        return []
    offers: list[Offer] = []
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        price = _price(ticket.get("price"))
        offers.append(
            Offer(
                url=url,
                price_currency="USD",
                price=price,
                availability="InStock",
                name=_string_value(ticket.get("name")) or "General Admission",
            )
        )
    return offers


def _price(raw_price: Any) -> str:
    if raw_price is None or raw_price == "":
        return ""
    try:
        return f"{float(raw_price):.2f}"
    except (TypeError, ValueError):
        return ""


def _location(raw: dict[str, Any]) -> Place:
    # EventPrime ``venue`` is usually null for single-location venues; the club
    # identity supplies the real venue downstream. Carry the venue name when
    # present so a multi-venue EventPrime producer keeps its sub-venue label.
    venue = raw.get("venue")
    venue_name = ""
    if isinstance(venue, dict):
        venue_name = _string_value(venue.get("name") or venue.get("title"))
    elif isinstance(venue, str):
        venue_name = venue.strip()
    return Place(
        name=venue_name,
        address=PostalAddress(
            street_address="",
            address_locality="",
            address_region="",
            postal_code="",
            address_country="",
        ),
    )


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
