"""Minimal decoder for the observed public ConsumerFullCalendarV2 contract.

Field numbers come from Tock's published explore.js protobuf schemas. This
availability snapshot proves individual performances, never cancellations.
"""

import re
from datetime import datetime
from typing import TypedDict
from urllib.parse import urlencode, urlparse
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.event import JsonLdEvent, Offer
from .extractor import _extract_redux_state, _location_from_details


class TockReservationEvent(JsonLdEvent):
    """A dated observation cannot authorize deletion of unobserved ticket tiers."""

    def to_show(self, club, enhanced=True):
        show = super().to_show(club, enhanced=enhanced)
        if show is not None:
            show.tickets_complete = False
        return show


class TicketTypeDetails(TypedDict):
    name: str
    slug: str
    variety: int


class DatedTicketGroup(TypedDict):
    date: str
    business_day: str
    time: str
    epoch: int
    prices: list[tuple[int, int]]
    total: int
    available: int
    held: int
    sold: int
    locked: int


VENUES = {
    29114: ("batsu-chicago", "America/Chicago", "BATSU! Chicago"),
    27051: ("batsunyc", "America/New_York", "BATSU! NYC"),
}


def _varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ValueError("Truncated Tock varint")
        byte = data[offset]
        offset += 1
        if shift == 63 and byte > 1:
            raise ValueError("Oversized Tock varint")
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError("Oversized Tock varint")


def _wire(data):
    if not isinstance(data, bytes) or len(data) > 2 * 1024 * 1024:
        raise ValueError("Invalid Tock protobuf payload")
    result, offset, count = {}, 0, 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        field, wire = tag >> 3, tag & 7
        count += 1
        if not field or field > 536870911 or count > 20000:
            raise ValueError("Invalid Tock protobuf field")
        if wire == 0:
            value, offset = _varint(data, offset)
        elif wire in {1, 2, 5}:
            if wire == 2:
                size, offset = _varint(data, offset)
            else:
                size = 8 if wire == 1 else 4
            if size > len(data) - offset:
                raise ValueError("Truncated Tock protobuf field")
            value, offset = data[offset : offset + size], offset + size
        else:
            raise ValueError("Unsupported Tock protobuf wire type")
        result.setdefault(field, []).append((wire, value))
    return result


def _one(message, field, kind=bytes, default=None):
    items = message.get(field, [])
    if not items and default is not None:
        return default
    if len(items) != 1:
        raise ValueError(f"Missing or repeated Tock field {field}")
    wire, value = items[0]
    if wire != (2 if kind in {bytes, str} else 0):
        raise ValueError(f"Wrong Tock field type {field}")
    return value.decode("utf-8") if kind is str else value


def _many(message, field):
    values = message.get(field, [])
    if any(wire != 2 for wire, _ in values):
        raise ValueError("Wrong repeated Tock message type")
    return [_wire(value) for _, value in values]


def _map(message, field):
    result = {}
    for entry in _many(message, field):
        key = _one(entry, 1, str)
        if key in result:
            raise ValueError("Repeated Tock date map key")
        result[key] = _wire(_one(entry, 2))
    return result


def decode_calendar(payload: bytes) -> tuple[dict[int, TicketTypeDetails], list[DatedTicketGroup]]:
    """Require the observed response envelope, never interpret errors as empty."""
    response = _wire(payload)
    if 2 in response:
        raise ValueError("Tock calendar returned an error envelope")
    generic = _wire(_one(response, 1))
    extensions = _wire(_one(generic, 1))
    if set(extensions) != {60686}:
        raise ValueError("Unknown Tock calendar response version")
    calendar = _wire(_one(extensions, 60686))
    ticket_types = {}
    for record in _many(calendar, 2):
        identity = _one(record, 1, int)
        if identity in ticket_types or identity <= 0:
            raise ValueError("Invalid Tock ticket type identity")
        ticket_types[identity] = {
            "name": _one(record, 2, str),
            "slug": _one(record, 18, str),
            "variety": _one(record, 100, int),
        }
    groups = []
    for business_day, date_map in _map(calendar, 1).items():
        for date, listing in _map(date_map, 1).items():
            for record in _many(listing, 2):
                prices = []
                for price in _many(record, 13):
                    info = _wire(_one(price, 3))
                    cents = _one(price, 2, int)
                    if _one(info, 2, int) != 1 or _one(info, 3, int) != cents or _one(info, 1, int) != 3:
                        raise ValueError("Unverified Tock per-ticket prepaid price")
                    prices.append((_one(price, 1, int), cents))
                groups.append(
                    {
                        "date": date,
                        "business_day": business_day,
                        "time": _one(record, 3, str),
                        "epoch": _one(record, 16, int),
                        "prices": prices,
                        "total": _one(record, 4, int),
                        "available": _one(record, 5, int),
                        "held": _one(record, 6, int),
                        "sold": _one(record, 7, int),
                        "locked": _one(record, 8, int),
                    }
                )
    if not groups or not ticket_types:
        raise ValueError("Unverified empty Tock reservation calendar")
    return ticket_types, groups


def extract_reservations(
    html: str,
    payload: bytes,
    *,
    source_url: str,
    business_id: int,
    timezone: str,
) -> list[JsonLdEvent]:
    """Consolidate dated PRIX_FIXE ticket tiers without inventing performances."""
    expected = VENUES.get(business_id)
    parsed_url = urlparse(source_url)
    if (
        not expected
        or parsed_url.scheme != "https"
        or parsed_url.netloc != "www.exploretock.com"
        or parsed_url.path.strip("/") != expected[0]
        or parsed_url.query
        or parsed_url.fragment
        or timezone != expected[1]
    ):
        raise ValueError("Unexpected Tock venue scope")
    state = _extract_redux_state(html)
    app = state.get("app", {})
    business = app.get("config", {}).get("business", {})
    if (
        business.get("id") != business_id
        or business.get("name") != expected[2]
        or app.get("activeAuth", {}).get("businessId") != business_id
    ):
        raise ValueError("Tock business identity mismatch")
    experiences = state.get("calendar", {}).get("offerings", {}).get("experience", [])
    by_id = {}
    for raw in experiences:
        identity = raw.get("id")
        if identity in by_id:
            raise ValueError("Repeated Tock experience identity")
        by_id[identity] = raw
    types, groups = decode_calendar(payload)
    for identity, item in types.items():
        source = by_id.get(identity)
        if (
            not source
            or item["name"] != source.get("name")
            or item["slug"] != source.get("slug")
            or not re.fullmatch(r"[a-z0-9-]+", item["slug"])
        ):
            raise ValueError("Tock ticket type disagrees with public experience")
        if (source.get("type"), item["variety"]) not in {("PRIX_FIXE", 1), ("GA_EVENT", 5)}:
            raise ValueError("Unsupported Tock experience type")
        if source.get("type") == "PRIX_FIXE":
            location = _location_from_details(source.get("eventDetails", {}))
            if location.name != expected[2]:
                raise ValueError("Tock reservation venue mismatch")
    grouped = {}
    for group in groups:
        date, wall_time = group["date"], group["time"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not re.fullmatch(r"\d{2}:\d{2}", wall_time):
            raise ValueError("Malformed Tock dated slot")
        start = datetime.fromtimestamp(group["epoch"], ZoneInfo(timezone))
        if start.strftime("%Y-%m-%dT%H:%M") != date + "T" + wall_time or start.second:
            raise ValueError("Tock epoch disagrees with dated slot")
        # Map keys are source dates, not global dropdown values. The observed
        # BATSU feed has no after-midnight business-day rollover.
        if group["business_day"] != date:
            raise ValueError("Unverified Tock business-day rollover")
        if sum(group[k] for k in ("available", "held", "sold", "locked")) != group["total"]:
            raise ValueError("Inconsistent Tock ticket counts")
        if not group["prices"]:
            raise ValueError("Missing Tock dated ticket types")
        for identity, cents in group["prices"]:
            if identity not in types or cents > 10000000:
                raise ValueError("Unknown Tock ticket type or invalid price")
            if by_id[identity]["type"] == "GA_EVENT":
                continue  # Existing explicit GA schedule remains authoritative.
            tiers = grouped.setdefault(start, {})
            if identity in tiers and tiers[identity][0] != cents:
                raise ValueError("Conflicting Tock tier prices")
            old = tiers.get(identity, (cents, 0))
            tiers[identity] = (cents, old[1] + group["available"])
    events = []
    for start, tiers in sorted(grouped.items()):
        offers = []
        for identity, (cents, available) in sorted(tiers.items()):
            record = types[identity]
            offers.append(
                Offer(
                    url=f"{source_url.rstrip('/')}/experience/{identity}/{record['slug']}",
                    price_currency="USD",
                    price=f"{cents / 100:.2f}",
                    availability="InStock" if available > 0 else "SoldOut",
                    name=record["name"],
                )
            )
        source = by_id[next(iter(tiers))]
        location = _location_from_details(source.get("eventDetails", {}))
        if location.name != expected[2]:
            raise ValueError("Tock reservation venue mismatch")
        events.append(
            TockReservationEvent(
                name=business["name"],
                start_date=start,
                location=location,
                offers=offers,
                url=source_url.rstrip("/")
                + "/search?"
                + urlencode({"date": start.strftime("%Y-%m-%d"), "size": 2, "time": start.strftime("%H:%M")}),
                description="",
            )
        )
    return events
