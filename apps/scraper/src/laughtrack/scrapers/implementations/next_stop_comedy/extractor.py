from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Iterable, Optional
from urllib.parse import urljoin

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
    events: list[NextStopComedyEvent] = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        payload = _loads_json(script.string or script.get_text("", strip=True))
        for node in _flatten_json_ld(payload):
            event = _event_from_json_ld(node)
            if event is not None:
                events.append(event)
    return events


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
    country = str(address.get("addressCountry") or "").strip()
    if street:
        return street
    return ", ".join(part for part in (city, state, postal, country) if part)


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
