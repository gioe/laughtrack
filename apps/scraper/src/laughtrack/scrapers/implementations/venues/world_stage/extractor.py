"""Extraction utilities for the World Stage Ciright calendar response."""

from typing import Iterable, List, Optional

from laughtrack.core.entities.event.world_stage import WorldStageEvent

_CONFIRMED_STATUS = "Confirmed"


class WorldStageExtractor:
    """Filter and shape the Ciright `data` array into WorldStageEvent rows."""

    @staticmethod
    def extract_events(
        payload: Optional[dict],
        *,
        room_ids: Iterable[int],
        source_url: str,
    ) -> List[WorldStageEvent]:
        if not payload or not payload.get("status"):
            return []

        rows = payload.get("data") or []
        if not isinstance(rows, list):
            return []

        allowed = {int(r) for r in room_ids if r is not None}
        events: List[WorldStageEvent] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if allowed and int(row.get("roomId") or 0) not in allowed:
                continue
            if (row.get("status") or "").strip() != _CONFIRMED_STATUS:
                continue

            event_id = row.get("childEventId") or row.get("eventId")
            title = (row.get("eventName") or "").strip()
            start_date = (row.get("startDate") or "").strip()
            time = (row.get("time") or "").strip()
            room = (row.get("room") or "").strip()
            if not event_id or not title or not start_date:
                continue

            events.append(
                WorldStageEvent(
                    event_id=int(event_id),
                    title=title,
                    start_date=start_date,
                    time=time,
                    room=room,
                    source_url=source_url,
                )
            )
        return events
