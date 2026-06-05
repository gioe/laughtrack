"""
Price extraction for classic SeatEngine show detail pages.

Classic SeatEngine venues (cdn.seatengine.com) embed a
``window.seat_engine_app_config`` JSON object on each ``/shows/{id}`` page.
The object's ``showtime.inventories[]`` list mirrors the shape served by the
SeatEngine REST API for non-classic venues — each inventory carries a ``price``
field in cents.

The listing page (``/events``) does not include prices, so the scraper must
fetch each show page to recover them. The functions below are HTML/JSON →
price helpers and do no network I/O; ``cheapest_price`` does emit a
``Logger.warn`` line (which the logger routes to its rotating file handler)
when it drops a sentinel-priced inventory, so callers should not treat it as
side-effect-free for test capture purposes.
"""

import json
from typing import List, Optional

from laughtrack.core.clients.seatengine.price import coerce_inventory_price_cents
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict


_CONFIG_PREFIX = "window.seat_engine_app_config = "


def extract_inventories(html: str) -> List[JSONDict]:
    """Return the inventories list from a classic SeatEngine show page.

    Returns an empty list when the embedded config object cannot be located,
    parsed, or contains no inventory objects.
    """
    cfg = _extract_app_config(html)
    if cfg is None:
        return []
    showtime = cfg.get("showtime") or {}
    inventories = showtime.get("inventories")
    if not isinstance(inventories, list):
        return []
    return [inv for inv in inventories if isinstance(inv, dict)]


def cheapest_price(inventories: List[JSONDict]) -> Optional[float]:
    """Return the cheapest positive price in dollars across the inventory list.

    Inventory ``price`` fields are integer cents; values <= 0 are treated as
    extraction-failure signals and ignored, and values over the sentinel
    ceiling (see ``core.clients.seatengine.price``) are dropped with a
    warning — sentinel placeholders like 100_000_000¢ ($1M "Closed for
    holiday" markers) otherwise overflow ``tickets.price`` Decimal(7,2) and
    abort the whole batch insert. Returns ``None`` when no inventory exposes a
    real positive price — callers should persist NULL rather than 0.
    """
    prices: List[float] = []
    for inv in inventories:
        price, reject_reason = coerce_inventory_price_cents(inv.get("price"))
        if reject_reason is not None:
            Logger.warn(
                f"SeatEngine classic price extractor: dropped inventory "
                f"{inv.get('id')}: {reject_reason}"
            )
            continue
        if price is not None:
            prices.append(price)
    if not prices:
        return None
    return min(prices)


def _extract_app_config(html: str) -> Optional[JSONDict]:
    idx = html.find(_CONFIG_PREFIX)
    if idx < 0:
        return None
    start = idx + len(_CONFIG_PREFIX)
    end = _walk_balanced_braces(html, start)
    if end is None:
        return None
    try:
        return json.loads(html[start:end])
    except (json.JSONDecodeError, ValueError):
        return None


def _walk_balanced_braces(s: str, start: int) -> Optional[int]:
    """Return the index *after* the matching closing brace for the object at ``start``.

    Tracks string boundaries so braces inside string literals are ignored.
    Returns ``None`` if the scan reaches EOF before the object closes.
    """
    if start >= len(s) or s[start] != "{":
        return None
    depth = 0
    in_str = False
    escape = False
    for j in range(start, len(s)):
        c = s[j]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return j + 1
    return None
