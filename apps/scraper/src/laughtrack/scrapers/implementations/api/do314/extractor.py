"""do314 event extraction from venue events.json API responses."""

from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.do314 import Do314Event
from laughtrack.foundation.infrastructure.logger.logger import Logger


class Do314Extractor:
    """Converts raw do314 ``event_groups`` payloads to Do314Event objects."""

    @staticmethod
    def extract_events(
        event_groups: List[Dict[str, Any]],
        default_timezone: str = "America/Chicago",
    ) -> List[Do314Event]:
        """
        Flatten ``event_groups[].events[]`` into a list of Do314Event objects.

        Skips events missing the required fields (id, title, and a usable
        start date). Past events (``past: true``) are skipped so re-runs only
        surface upcoming shows.
        """
        results: List[Do314Event] = []
        for group in event_groups or []:
            if not isinstance(group, dict):
                continue
            for raw in group.get("events") or []:
                event = Do314Extractor._parse_event(raw, default_timezone)
                if event is not None:
                    results.append(event)
        return results

    @staticmethod
    def _parse_event(raw: Any, default_timezone: str) -> Optional[Do314Event]:
        if not isinstance(raw, dict):
            return None
        try:
            event_id = raw.get("id")
            title = (raw.get("title") or "").strip()
            permalink = raw.get("permalink") or ""
            begin_time = raw.get("begin_time") or ""
            begin_date = raw.get("begin_date") or ""

            if event_id is None or not title or not permalink:
                return None
            if not begin_time and not begin_date:
                return None
            if raw.get("past") is True:
                return None

            return Do314Event(
                event_id=str(event_id),
                title=title,
                begin_time=str(begin_time),
                begin_date=str(begin_date),
                permalink=str(permalink),
                category_param=str(raw.get("category_param") or "").lower(),
                buy_url=(raw.get("buy_url") or None),
                description=(raw.get("excerpt") or raw.get("description") or None),
                is_free=bool(raw.get("is_free")),
                timezone_name=default_timezone,
            )
        except Exception as e:
            Logger.error(f"Do314Extractor: failed to parse event id={raw.get('id')}: {e}")
            return None
