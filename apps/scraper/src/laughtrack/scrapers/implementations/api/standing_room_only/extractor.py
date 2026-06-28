"""Standing Room Only show extraction from ReadLiveEvents JSON responses.

The ReadLiveEvents feed returns ``{"Data": [event, ...]}`` where each event is a
headliner residency carrying a ``Shows`` array (one entry per showtime). The
extractor fans each event out to one StandingRoomOnlyEvent per showtime, parsing
the .NET ``Start`` epoch (``/Date(ms)/``, UTC) and dropping past showtimes.
"""

import re
import time
from typing import Any, List, Optional

from laughtrack.core.entities.event.standing_room_only import StandingRoomOnlyEvent

# .NET serializes DateTime as "/Date(1783639800000)/" (UTC epoch milliseconds,
# optionally with a trailing timezone offset like "/Date(1783639800000-0400)/").
_DOTNET_DATE_RE = re.compile(r"/Date\((-?\d+)")


class StandingRoomOnlyExtractor:
    """Converts raw ReadLiveEvents payloads to StandingRoomOnlyEvent objects."""

    @staticmethod
    def extract_events(
        payload: Any,
        base_url: str,
        default_timezone: str = "America/New_York",
    ) -> List[StandingRoomOnlyEvent]:
        """Fan ``payload['Data']`` events out to one event per upcoming showtime.

        Skips events without a usable ``Id``/``EventTitle``, showtimes whose
        ``Start`` cannot be parsed, and showtimes in the past (``IsShowOld`` or a
        ``Start`` before now). ``base_url`` is the SRO origin used to build each
        show's public event page (``{base}/WebOffice/EventList/{event_id}``).
        """
        if not isinstance(payload, dict):
            return []
        records = payload.get("Data")
        if not isinstance(records, list):
            return []

        base = base_url.rstrip("/")
        now_ms = int(time.time() * 1000)
        events: List[StandingRoomOnlyEvent] = []

        for raw in records:
            if not isinstance(raw, dict):
                continue
            title = (raw.get("EventTitle") or "").strip()
            try:
                event_id = int(raw.get("Id"))
            except (TypeError, ValueError):
                continue
            if not title:
                continue
            shows = raw.get("Shows")
            if not isinstance(shows, list):
                continue

            page_url = f"{base}/WebOffice/EventList/{event_id}"
            for show in shows:
                if not isinstance(show, dict):
                    continue
                if show.get("IsShowOld") is True:
                    continue
                start_ms = StandingRoomOnlyExtractor._parse_dotnet_ms(show.get("Start"))
                if start_ms is None or start_ms <= now_ms:
                    continue
                events.append(
                    StandingRoomOnlyEvent(
                        event_id=int(event_id),
                        title=title,
                        start_ms=start_ms,
                        show_page_url=page_url,
                        timezone_name=default_timezone,
                    )
                )

        return events

    @staticmethod
    def _parse_dotnet_ms(value: Any) -> Optional[int]:
        """Extract UTC epoch milliseconds from a .NET ``/Date(ms)/`` string.

        Returns ``None`` for missing values, unparseable strings, or the .NET
        "min date" sentinel (a large negative epoch used for unset End/OnSale
        fields) so a placeholder never becomes a 0001-01-01 show.
        """
        if not value or not isinstance(value, str):
            return None
        match = _DOTNET_DATE_RE.search(value)
        if not match:
            return None
        ms = int(match.group(1))
        return ms if ms > 0 else None
