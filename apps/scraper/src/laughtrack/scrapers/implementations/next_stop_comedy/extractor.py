from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Iterable, Optional
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bs4 import BeautifulSoup

from .event import NextStopComedyEvent

_BASE_URL = "https://www.nextstopcomedy.com"
_EVENT_RE = re.compile(r"(?:https://www\.nextstopcomedy\.com)?/events/[A-Za-z0-9_-]+")


def extract_event_urls(html: str, api_events: Optional[Iterable[dict[str, Any]]] = None) -> list[str]:
    urls = set()
    for match in _EVENT_RE.finditer(html or ""):
        urls.add(urljoin(_BASE_URL, match.group(0)))

    for item in api_events or []:
        slug = str(item.get("slug") or "").strip()
        if slug:
            urls.add(f"{_BASE_URL}/events/{slug}")

    return sorted(urls)


def extract_json_ld_events(html: str) -> list[NextStopComedyEvent]:
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    event_props = _main_event_props(soup)
    events: list[NextStopComedyEvent] = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        payload = _loads_json(script.string or script.get_text("", strip=True))
        for node in _flatten_json_ld(payload):
            event = _event_from_json_ld(node)
            if event is not None:
                event.venue_timezone = _supplied_timezone(node, event, event_props)
                events.append(event)
    return events


def _main_event_props(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Decode Flight JSON; never regex-match a timezone in nearby-show text."""
    chunks = []
    for script in soup.find_all("script"):
        match = re.fullmatch(r"\s*self\.__next_f\.push\((.*)\);?\s*", script.get_text(), re.S)
        if not match:
            continue
        payload = _loads_json(match.group(1))
        if isinstance(payload, list) and len(payload) == 2 and payload[0] == 1 and isinstance(payload[1], str):
            chunks.append(payload[1])
    candidates = []
    for line in "".join(chunks).splitlines():
        _, separator, raw = line.partition(":")
        if not separator:
            continue
        stack = [_loads_json(raw)]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                if value.get("eventId") and value.get("eventId") == value.get("currentEventId"):
                    candidates.append(value)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
    return candidates


def _supplied_timezone(
    node: dict[str, Any], event: NextStopComedyEvent, candidates: list[dict[str, Any]]
) -> Optional[str]:
    url = urlparse(str(node.get("url") or ""))
    if url.hostname not in {"nextstopcomedy.com", "www.nextstopcomedy.com"}:
        return None
    path = url.path.rstrip("/").split("/")
    if len(path) != 3 or path[1] != "events":
        return None
    zones = set()
    for props in candidates:
        if props.get("eventSlug") != path[2]:
            continue
        if props.get("eventDate"):
            try:
                supplied_date = datetime.fromisoformat(
                    str(props["eventDate"]).removeprefix("$D").replace("Z", "+00:00")
                )
            except ValueError:
                continue
            if supplied_date != event.start_date:
                continue
        zone = props.get("venueTimezone")
        if not isinstance(zone, str) or not zone:
            continue
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError):
            continue
        zones.add(zone)
    return next(iter(zones)) if len(zones) == 1 else None


def _loads_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _flatten_json_ld(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _event_from_json_ld(node: dict[str, Any]) -> Optional[NextStopComedyEvent]:
    json_type = node.get("@type")
    types = json_type if isinstance(json_type, list) else [json_type]
    if not any(str(t).lower() in {"comedyevent", "event"} for t in types):
        return None

    title = str(node.get("name") or "").strip()
    event_url = str(node.get("url") or "").strip()
    start_raw = str(node.get("startDate") or "").strip()
    if not title or not event_url or not start_raw:
        return None

    try:
        start_date = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    except ValueError:
        return None

    location = node.get("location") if isinstance(node.get("location"), dict) else {}
    address = location.get("address") if isinstance(location.get("address"), dict) else {}
    venue_name = str(location.get("name") or title).strip()
    venue_address = _full_address(address)
    venue_zip = str(address.get("postalCode") or "").strip()

    offers = node.get("offers") if isinstance(node.get("offers"), dict) else {}
    ticket_url = str(offers.get("url") or event_url).strip()
    price = _parse_float(offers.get("lowPrice") or offers.get("price"))
    availability = str(offers.get("availability") or "")

    return NextStopComedyEvent(
        title=title,
        start_date=start_date,
        event_url=ticket_url or event_url,
        venue_name=venue_name,
        venue_address=venue_address,
        venue_zip=venue_zip,
        description=str(node.get("description") or "").strip() or None,
        performers=_performers(node.get("performer")),
        ticket_price=price,
        sold_out=availability.endswith("SoldOut") or "soldout" in availability.lower(),
    )


def _full_address(address: dict[str, Any]) -> str:
    street = str(address.get("streetAddress") or "").strip()
    city = str(address.get("addressLocality") or "").strip()
    state = str(address.get("addressRegion") or "").strip()
    postal = str(address.get("postalCode") or "").strip()
    country_value = address.get("addressCountry")
    if isinstance(country_value, dict):
        country_value = country_value.get("name")
    country = str(country_value or "").strip()
    parts = [street] if street else []

    # Compare against the locality suffix, not the street itself: Boston Road
    # is not evidence that the address already includes the city of Boston.
    suffix = street.partition(",")[2]
    normalized_suffix = " " + " ".join(re.findall(r"\w+", suffix.casefold())) + " "

    def already_present(value: str) -> bool:
        normalized = " ".join(re.findall(r"\w+", value.casefold()))
        return bool(normalized and f" {normalized} " in normalized_suffix)

    if city and not already_present(city):
        parts.append(city)
    if state and not already_present(state):
        parts.append(state)
    if postal and not already_present(postal):
        # Keep region + postal together for the shared city/state parser.
        if state and parts and parts[-1].casefold().endswith(state.casefold()):
            parts[-1] += f" {postal}"
        else:
            parts.append(postal)
    if country and not already_present(country):
        parts.append(country)
    return ", ".join(parts)


def _performers(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if raw:
        return [raw]
    return []


def _parse_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
