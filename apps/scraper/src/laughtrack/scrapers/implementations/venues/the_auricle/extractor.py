"""Extractor for The Auricle's SociableKit/accentapi Facebook-events JSON feed."""

import re
from datetime import datetime
from typing import Any, List, Optional

from laughtrack.core.entities.event.the_auricle import TheAuricleEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# The Auricle is a music/variety venue, so we keep only events whose name or
# description marks them as comedy. "Open mic" alone is excluded (it is usually
# a music open mic) — it only qualifies alongside a comedy term.
_COMEDY_RE = re.compile(r"\b(stand[\s-]?up|comedy|comedian|improv|sketch comedy)\b", re.IGNORECASE)

_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", re.IGNORECASE)


def _is_comedy(event: dict) -> bool:
    text = f"{event.get('name', '')} {event.get('description', '')}"
    return bool(_COMEDY_RE.search(text))


def _parse_dt_str(event: dict) -> Optional[str]:
    """Build a local 'YYYY-MM-DD HH:MM:00' string from the feed's date fields."""
    date_raw = (event.get("start_date_raw") or "").strip()  # e.g. "2026-06-29"
    time_raw = (event.get("start_time") or "").strip()       # e.g. "8:00 pm"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_raw):
        hour, minute = 0, 0
        tm = _TIME_RE.search(time_raw)
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2) or 0)
            if tm.group(3).lower() == "pm" and hour != 12:
                hour += 12
            if tm.group(3).lower() == "am" and hour == 12:
                hour = 0
        return f"{date_raw} {hour:02d}:{minute:02d}:00"

    # Fallback: parse the ISO UTC instant (rendered in the club tz downstream).
    utc = (event.get("event_start_utc") or "").strip()
    if utc:
        try:
            dt = datetime.fromisoformat(utc.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:00")
        except ValueError:
            return None
    return None


def _parse_price(event: dict) -> Optional[float]:
    raw = str(event.get("ticket_price") or "").strip()
    m = re.search(r"(\d+(?:\.\d{1,2})?)", raw)
    return float(m.group(1)) if m else None


class TheAuricleEventExtractor:
    """Parses comedy TheAuricleEvent objects from the accentapi feed JSON."""

    @staticmethod
    def extract_shows(payload: Any, logger_context=None) -> List[TheAuricleEvent]:
        if not isinstance(payload, dict):
            return []
        events = payload.get("events")
        if not isinstance(events, list):
            return []

        out: List[TheAuricleEvent] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            name = (ev.get("name") or "").strip()
            if not name or not _is_comedy(ev):
                continue
            dt_str = _parse_dt_str(ev)
            if not dt_str:
                continue
            url = (ev.get("ticket_uri") or "").strip() or (ev.get("html_link") or "").strip()
            out.append(
                TheAuricleEvent(name=name, dt_str=dt_str, url=url, price=_parse_price(ev))
            )

        if not out and logger_context is not None:
            Logger.warn(
                "TheAuricleEventExtractor: no comedy events in accentapi feed",
                logger_context,
            )
        return out
