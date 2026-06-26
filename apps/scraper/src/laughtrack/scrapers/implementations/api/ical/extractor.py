"""iCalendar (ICS) parsing for the generic ical scraper.

A deliberately small RFC 5545 reader scoped to what public Google Calendar
feeds emit: line unfolding, VEVENT blocks, ``DTSTART`` in UTC (``...Z``),
``TZID``-qualified, floating, or date-only form, and text unescaping. It avoids
a third-party ``icalendar`` dependency; recurring events are already expanded
into individual VEVENT instances by Google's public feed, so RRULE handling is
not required.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pytz

from laughtrack.core.entities.event.ical_event import IcalEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class IcalExtractor:
    """Parse raw ICS text into IcalEvent objects."""

    @staticmethod
    def extract_events(
        ics_text: str,
        default_timezone: str = "America/Chicago",
        page_url_fallback: str = "",
        drop_before: Optional[datetime] = None,
    ) -> List[IcalEvent]:
        """Parse every VEVENT in ``ics_text`` into IcalEvent objects.

        Events without a SUMMARY or a parseable DTSTART, and events with
        ``STATUS:CANCELLED``, are skipped. When ``drop_before`` (a
        timezone-aware datetime) is given, events starting before it are
        skipped too — used to drop stale past events from feeds that always
        carry recent history.
        """
        try:
            tz = pytz.timezone(default_timezone)
        except Exception:
            tz = pytz.timezone("America/Chicago")

        events: List[IcalEvent] = []
        for block in IcalExtractor._iter_vevent_blocks(ics_text):
            event = IcalExtractor._parse_vevent(block, tz, page_url_fallback)
            if event is None:
                continue
            if drop_before is not None and event.start < drop_before:
                continue
            events.append(event)
        return events

    @staticmethod
    def _unfold(ics_text: str) -> List[str]:
        """Join RFC 5545 folded lines (continuations start with space/tab)."""
        lines: List[str] = []
        for raw in ics_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if raw[:1] in (" ", "\t"):
                if lines:
                    lines[-1] += raw[1:]
                else:
                    lines.append(raw[1:])
            else:
                lines.append(raw)
        return lines

    @staticmethod
    def _iter_vevent_blocks(ics_text: str):
        """Yield lists of unfolded property lines, one list per VEVENT."""
        current: Optional[List[str]] = None
        for line in IcalExtractor._unfold(ics_text):
            if line == "BEGIN:VEVENT":
                current = []
            elif line == "END:VEVENT":
                if current is not None:
                    yield current
                current = None
            elif current is not None:
                current.append(line)

    @staticmethod
    def _parse_property(line: str) -> Tuple[str, Dict[str, str], str]:
        """Split ``NAME;PARAM=VAL:VALUE`` into (name, params, value)."""
        colon = line.find(":")
        if colon == -1:
            return "", {}, ""
        head, value = line[:colon], line[colon + 1:]
        parts = head.split(";")
        name = parts[0].upper()
        params: Dict[str, str] = {}
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k.upper()] = v
        return name, params, value

    @staticmethod
    def _unescape_text(value: str) -> str:
        """Unescape RFC 5545 TEXT values."""
        out = []
        i = 0
        while i < len(value):
            ch = value[i]
            if ch == "\\" and i + 1 < len(value):
                nxt = value[i + 1]
                out.append({"n": "\n", "N": "\n", ",": ",", ";": ";", "\\": "\\"}.get(nxt, nxt))
                i += 2
            else:
                out.append(ch)
                i += 1
        return "".join(out)

    @staticmethod
    def _parse_dt(value: str, params: Dict[str, str], tz) -> Optional[datetime]:
        """Resolve a DTSTART value to a timezone-aware datetime."""
        value = value.strip()
        try:
            if params.get("VALUE") == "DATE" or (len(value) == 8 and "T" not in value):
                naive = datetime.strptime(value[:8], "%Y%m%d")
                return tz.localize(naive)
            if value.endswith("Z"):
                naive = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
                return naive.replace(tzinfo=timezone.utc)
            naive = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
            tzid = params.get("TZID")
            local_tz = tz
            if tzid:
                try:
                    local_tz = pytz.timezone(tzid)
                except Exception:
                    local_tz = tz
            return local_tz.localize(naive)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_vevent(lines: List[str], tz, page_url_fallback: str) -> Optional[IcalEvent]:
        fields: Dict[str, Tuple[Dict[str, str], str]] = {}
        for line in lines:
            name, params, value = IcalExtractor._parse_property(line)
            if name and name not in fields:
                fields[name] = (params, value)

        try:
            status = fields.get("STATUS", ({}, ""))[1].upper()
            if status == "CANCELLED":
                return None

            summary = IcalExtractor._unescape_text(fields.get("SUMMARY", ({}, ""))[1]).strip()
            if not summary:
                return None

            dt_params, dt_value = fields.get("DTSTART", ({}, ""))
            start = IcalExtractor._parse_dt(dt_value, dt_params, tz)
            if start is None:
                return None

            url = (fields.get("URL", ({}, ""))[1] or "").strip()
            # Calendar URL fields sometimes hold non-web junk (e.g. an
            # `messages://` deep link pasted as the event URL); only trust http(s).
            if not url.lower().startswith(("http://", "https://")):
                url = ""
            uid = (fields.get("UID", ({}, ""))[1] or "").strip()
            description = IcalExtractor._unescape_text(fields.get("DESCRIPTION", ({}, ""))[1]).strip()
            location = IcalExtractor._unescape_text(fields.get("LOCATION", ({}, ""))[1]).strip()

            return IcalEvent(
                uid=uid,
                summary=summary,
                start=start,
                show_page_url=url or page_url_fallback,
                description=description or None,
                location=location or None,
            )
        except Exception as e:
            Logger.error(f"IcalExtractor: failed to parse VEVENT: {e}")
            return None
