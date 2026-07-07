"""HoldMyTicket show extraction from public API JSON responses.

Both the whitelabel feed (``public/events/nearby``) and the series expansion
(``public/events/repeating/id/{id}``) return ``{"events": [event, ...]}``
where each event carries ``id``, ``title``, a venue wall-clock ``start``
(``2026-07-10 19:00:00``), and a per-showtime ``ticket_url``. Feed entries
additionally carry ``venue_id``, cancellation/postponement flags, and a
``repeating_future_events`` count; expansion entries are bare showtimes.

The extractor validates raw event dicts and converts them to
HoldMyTicketEvent objects, dropping past showtimes against the venue clock.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.holdmyticket import HoldMyTicketEvent

_START_FORMAT = "%Y-%m-%d %H:%M:%S"
# MySQL zero-date sentinel meaning "not cancelled".
_CANCEL_SENTINEL = "0000-00-00 00:00:00"
_TICKETS_BASE = "https://tickets.holdmyticket.com/tickets/"


class HoldMyTicketExtractor:
    """Converts raw HoldMyTicket API payloads to HoldMyTicketEvent objects."""

    @staticmethod
    def extract_raw_events(payload: Any) -> List[Dict[str, Any]]:
        """Return the validated raw event dicts from an API payload.

        Skips entries without a usable ``id``/``title``/``start``, cancelled
        entries (``cancel`` set past the zero-date sentinel), and postponed
        entries (``postponed == 'y'`` — their listed date is stale until the
        venue reschedules). Expansion entries lack the cancel/postponed flags
        entirely, so they pass those checks by default.
        """
        if not isinstance(payload, dict):
            return []
        records = payload.get("events")
        if not isinstance(records, list):
            return []

        raw_events: List[Dict[str, Any]] = []
        for raw in records:
            if not isinstance(raw, dict):
                continue
            try:
                int(raw.get("id"))
            except (TypeError, ValueError):
                continue
            if not (raw.get("title") or "").strip():
                continue
            if not isinstance(raw.get("start"), str) or not raw["start"].strip():
                continue
            cancel = raw.get("cancel")
            if isinstance(cancel, str) and cancel.strip() and cancel != _CANCEL_SENTINEL:
                continue
            if raw.get("postponed") == "y":
                continue
            raw_events.append(raw)
        return raw_events

    @staticmethod
    def to_events(
        raw_events: List[Dict[str, Any]],
        timezone_name: str = "America/Denver",
    ) -> List[HoldMyTicketEvent]:
        """Convert validated raw event dicts to upcoming HoldMyTicketEvent objects.

        Drops showtimes whose ``start`` cannot be parsed or is in the past
        relative to the venue's wall clock. ``ticket_url`` falls back to the
        canonical checkout URL built from the event id.
        """
        try:
            now_local = datetime.now(ZoneInfo(timezone_name)).replace(tzinfo=None)
        except Exception:
            now_local = datetime.now()

        events: List[HoldMyTicketEvent] = []
        for raw in raw_events:
            event_id = int(raw["id"])
            start_local = raw["start"].strip()
            start = HoldMyTicketExtractor._parse_start(start_local)
            if start is None or start <= now_local:
                continue
            ticket_url = (raw.get("ticket_url") or "").strip() or f"{_TICKETS_BASE}{event_id}"
            events.append(
                HoldMyTicketEvent(
                    event_id=event_id,
                    title=raw["title"].strip(),
                    start_local=start_local,
                    ticket_url=ticket_url,
                    timezone_name=timezone_name,
                )
            )
        return events

    @staticmethod
    def _parse_start(value: str) -> Optional[datetime]:
        """Parse a venue wall-clock ``start`` string, or None if malformed."""
        try:
            return datetime.strptime(value, _START_FORMAT)
        except (ValueError, TypeError):
            return None
