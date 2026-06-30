"""Extract BrassTix calendar entries from inline JavaScript."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.brasstix import BrassTixEvent

_EVENT_RE = re.compile(
    r"\{title:'(?P<title>(?:\\'|[^'])*)',"
    r"subtitle:'(?P<subtitle>(?:\\'|[^'])*)',"
    r"eventid:'(?P<event_id>[^']*)',"
    r"start:'(?P<start>[^']*)',"
    r"url:'(?P<url>[^']*)'"
    r".*?,ShowName:'(?P<show_name>[^']*)'\}",
    re.DOTALL,
)

_STATUS_LABELS = {
    "BEST AVAILABILITY",
    "SELLING OUT",
    "SOLD OUT",
}

_TICKET_PRICES_RE = re.compile(r"\bticketprices\s*=\s*\{(?P<body>.*?)\}", re.DOTALL)
_TICKET_PRICE_PAIR_RE = re.compile(r"['\"]?(?P<tier>[^'\":,\s{}]+)['\"]?\s*:\s*(?P<price>\d+(?:\.\d+)?)")
_PRIVATE_TIER_LABEL_RE = re.compile(r"\b(private|buyout|buy\s*out|full\s*house)\b", re.IGNORECASE)
_PRIVATE_BUYOUT_PRICE_FLOOR = 250.0


def extract_brasstix_events(html: str, calendar_url: str) -> list[BrassTixEvent]:
    """Return future purchasable calendar entries embedded in BrassTix JS."""
    events: list[BrassTixEvent] = []
    for match in _EVENT_RE.finditer(html or ""):
        raw_url = _unescape_js_string(match.group("url")).strip()
        if not raw_url:
            continue

        title_lines = _clean_lines(_unescape_js_string(match.group("title")))
        subtitle_lines = _clean_lines(_unescape_js_string(match.group("subtitle")))
        title_parts = [line for line in title_lines if line.upper() not in _STATUS_LABELS]
        if not title_parts:
            continue

        availability_parts = [line for line in [*title_lines, *subtitle_lines] if line.upper() in _STATUS_LABELS]
        events.append(
            BrassTixEvent(
                event_id=_unescape_js_string(match.group("event_id")).strip(),
                title=" ".join(title_parts),
                start=_unescape_js_string(match.group("start")).strip(),
                ticket_url=urljoin(calendar_url, raw_url.replace(" ", "%20")),
                show_name=_unescape_js_string(match.group("show_name")).strip(),
                availability_label="; ".join(dict.fromkeys(availability_parts)),
            )
        )
    return events


def extract_brasstix_checkout_price(html: str) -> float | None:
    """Return the public base ticket price from a BrassTix checkout page."""
    prices_by_tier = _extract_ticketprices_map(html)
    if not prices_by_tier:
        return None

    public_prices = _public_prices_from_price_rows(html, prices_by_tier)
    if public_prices:
        return min(public_prices)

    non_buyout_prices = [price for price in prices_by_tier.values() if 0 < price < _PRIVATE_BUYOUT_PRICE_FLOOR]
    if non_buyout_prices:
        return min(non_buyout_prices)

    positive_prices = [price for price in prices_by_tier.values() if price > 0]
    return min(positive_prices) if positive_prices else None


def _clean_lines(value: str) -> list[str]:
    return [" ".join(line.split()) for line in value.splitlines() if line.strip()]


def _unescape_js_string(value: str) -> str:
    return (
        value.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t").replace("\\'", "'").replace("\\\\", "\\")
    )


def _extract_ticketprices_map(html: str) -> dict[str, float]:
    match = _TICKET_PRICES_RE.search(html or "")
    if not match:
        return {}

    prices: dict[str, float] = {}
    for pair in _TICKET_PRICE_PAIR_RE.finditer(match.group("body")):
        try:
            prices[pair.group("tier")] = float(pair.group("price"))
        except ValueError:
            continue
    return prices


def _public_prices_from_price_rows(html: str, prices_by_tier: dict[str, float]) -> list[float]:
    soup = BeautifulSoup(html or "", "html.parser")
    prices: list[float] = []
    for row in soup.select(".pricerow"):
        container = row.find_parent(class_="ticketdiv") or row
        text = container.get_text(" ", strip=True)
        if _PRIVATE_TIER_LABEL_RE.search(text):
            continue

        price = _price_for_row(row, prices_by_tier)
        if price is not None and 0 < price < _PRIVATE_BUYOUT_PRICE_FLOOR:
            prices.append(price)
    return prices


def _price_for_row(row, prices_by_tier: dict[str, float]) -> float | None:
    candidates = [row, *row.find_all(True)]
    for element in candidates:
        for attr in ("typeid", "priceid", "tickettypeid", "ticketid", "tierid"):
            tier_id = element.get(attr)
            if tier_id and tier_id in prices_by_tier:
                return prices_by_tier[tier_id]

    for element in candidates:
        for attr in ("menuprice", "originalprice"):
            raw_price = element.get(attr)
            if raw_price:
                try:
                    return float(raw_price)
                except ValueError:
                    continue
    return None
