"""Ice House Comedy Club event extraction from Tockify API response."""

from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from laughtrack.core.entities.event.ice_house import IceHouseEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _extract_calname(api_url: Optional[str]) -> str:
    """Pull the Tockify calname from an API URL like .../api/ngevent?calname=theicehouse&..."""
    if not api_url:
        return ""
    try:
        values = parse_qs(urlparse(api_url).query).get("calname") or []
    except Exception:
        return ""
    return values[0] if values else ""


class IceHouseExtractor:
    """Converts raw Tockify API JSON into IceHouseEvent objects."""

    @staticmethod
    def extract_events(
        api_response: Dict[str, Any],
        api_url: Optional[str] = None,
    ) -> List[IceHouseEvent]:
        """Extract IceHouseEvent objects from the Tockify API response dict.

        Passing the source api_url lets the extractor derive each event's public
        Tockify detail URL (https://tockify.com/<calname>/detail/<uid>/<tid>),
        which is used as a fallback when content.customButtonLink is absent.
        """
        raw_events = api_response.get("events", [])
        if not isinstance(raw_events, list):
            return []

        calname = _extract_calname(api_url)
        events = []
        for raw in raw_events:
            try:
                event = IceHouseExtractor._parse_event(raw, calname=calname)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"IceHouseExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any], calname: str = "") -> IceHouseEvent | None:
        """Parse a single raw Tockify event dict into an IceHouseEvent, or None to skip."""
        eid = raw.get("eid") or {}
        uid = str(eid.get("uid", ""))
        if not uid:
            return None

        content = raw.get("content") or {}
        summary = content.get("summary") or {}
        title = (summary.get("text") or "").strip()
        if not title:
            return None

        when = raw.get("when") or {}
        start = when.get("start") or {}
        start_ms = start.get("millis")
        if not isinstance(start_ms, (int, float)):
            return None

        ticket_url = (content.get("customButtonLink") or "").strip()
        tzid = start.get("tzid") or "America/Los_Angeles"

        tagset = content.get("tagset") or {}
        tags = tagset.get("tags") or {}
        default_tags = tags.get("default") or []
        room = default_tags[0] if default_tags else ""

        tid = eid.get("tid")
        if not isinstance(tid, (int, float)):
            tid = int(start_ms)
        detail_url = (
            f"https://tockify.com/{calname}/detail/{uid}/{int(tid)}" if calname else ""
        )

        return IceHouseEvent(
            uid=uid,
            title=title,
            start_ms=int(start_ms),
            ticket_url=ticket_url,
            timezone=tzid,
            room=room,
            detail_url=detail_url,
        )
