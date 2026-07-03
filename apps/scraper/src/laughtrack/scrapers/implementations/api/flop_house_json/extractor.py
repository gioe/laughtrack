"""Extraction helpers for Flop House static JSON feeds."""

import time
from typing import Any, Dict, List

from laughtrack.core.entities.event.flop_house_json import FlopHouseJsonEvent


class FlopHouseJsonExtractor:
    """Parse Flop House venue event-group JSON into events."""

    @staticmethod
    def extract_events(
        event_groups: Any,
        *,
        venues_by_id: Dict[str, Dict[str, Any]],
    ) -> List[FlopHouseJsonEvent]:
        if not isinstance(event_groups, list):
            return []

        now_ms = int(time.time() * 1000)
        events: List[FlopHouseJsonEvent] = []
        for group in event_groups:
            if not isinstance(group, dict):
                continue
            show = group.get("show") if isinstance(group.get("show"), dict) else {}
            raw_events = group.get("events")
            if not isinstance(raw_events, list):
                continue
            for raw_event in raw_events:
                event = FlopHouseJsonExtractor._parse_event(raw_event, show, venues_by_id)
                if event is None or event.start_ms < now_ms:
                    continue
                events.append(event)
        return events

    @staticmethod
    def _parse_event(
        raw_event: Any,
        show: Dict[str, Any],
        venues_by_id: Dict[str, Dict[str, Any]],
    ) -> FlopHouseJsonEvent | None:
        if not isinstance(raw_event, dict):
            return None
        eventbrite_id = raw_event.get("eventbriteId")
        start_ms = raw_event.get("startTime")
        if not eventbrite_id or not isinstance(start_ms, int):
            return None

        title = raw_event.get("title") or show.get("title") or ""
        if not isinstance(title, str) or not title.strip():
            return None

        venue_id = raw_event.get("venueId")
        venue = venues_by_id.get(str(venue_id), {}) if venue_id is not None else {}
        venue_name = venue.get("name") if isinstance(venue.get("name"), str) else ""
        description = raw_event.get("description") or show.get("description") or ""

        return FlopHouseJsonEvent(
            title=title.replace("^", "'").strip(),
            start_ms=start_ms,
            show_page_url=f"https://www.eventbrite.com/e/tickets-{eventbrite_id}",
            description=description if isinstance(description, str) else "",
            venue_name=venue_name,
        )
