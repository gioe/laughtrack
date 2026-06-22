"""Parse the Tix.com organization events JSON into events."""

import html as html_lib
import re
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict

from .data import TixComEvent

_DEFAULT_TZ = "America/New_York"
_TICKET_BASE = "https://www.tix.com/ticket-sales"


def _flatten_grouped(payload: JSONDict) -> List[JSONDict]:
    """payload.groupedEvents is a list of event-lists; flatten to one list."""
    grouped = (payload or {}).get("groupedEvents") or []
    events: List[JSONDict] = []
    for group in grouped:
        if isinstance(group, list):
            events.extend(e for e in group if isinstance(e, dict))
        elif isinstance(group, dict):
            events.append(group)
    return events


def _parse_datetime(raw: Optional[str], tz: str) -> Optional[datetime]:
    """Tix.com EventDate is a naive local ISO timestamp, e.g. 2026-07-08T19:30:00."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=ZoneInfo(tz))
    except (ValueError, TypeError):
        return None


def _clean_description(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _price(event: JSONDict) -> Optional[float]:
    """Lowest advertised price, or None when unknown.

    A MinPrice of 0 is treated as price-unknown rather than "free": Tix.com emits
    0 for not-yet-priced / suppressed-price events, and ShowFactoryUtils reserves
    price=0.0 for events explicitly proven free (per the tickets-are-access-records
    convention). Returning None avoids surfacing a paid show as free.
    """
    if event.get("SuppressPrices"):
        return None
    val = event.get("MinPrice")
    try:
        price = float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
    return price if price and price > 0 else None


class TixComExtractor:
    @staticmethod
    def extract_events(
        payload: JSONDict, ticket_base_url: str, tz: str = _DEFAULT_TZ
    ) -> List[TixComEvent]:
        events: List[TixComEvent] = []
        base = (ticket_base_url or "").rstrip("/")
        for raw in _flatten_grouped(payload):
            event_id = raw.get("EventId")
            title = (raw.get("ProductionName") or "").strip()
            date = _parse_datetime(raw.get("EventDate"), tz)
            if event_id is None or not title or not date:
                if title:
                    Logger.debug(f"tix_com: skipping event with missing id/date '{title}'")
                continue
            show_page_url = f"{base}/event/{event_id}" if base else (raw.get("URL") or "")
            events.append(
                TixComEvent(
                    event_id=int(event_id),
                    title=html_lib.unescape(title),
                    date=date,
                    show_page_url=show_page_url,
                    price=_price(raw),
                    description=_clean_description(raw.get("ProductionDescription") or raw.get("EventDescription")),
                )
            )
        return events
