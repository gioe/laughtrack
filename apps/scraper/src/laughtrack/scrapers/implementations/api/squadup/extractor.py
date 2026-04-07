"""SquadUP event extraction from API responses."""

from typing import Any, Dict, List

from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class SquadUpExtractor:
    """Converts raw SquadUP API event dicts to SquadUpEvent objects."""

    @staticmethod
    def extract_events(events_json: List[Dict[str, Any]]) -> List[SquadUpEvent]:
        """
        Convert a list of raw SquadUP API event dicts to SquadUpEvent objects.

        Skips events missing required fields (id, start_at, url).
        """
        results: List[SquadUpEvent] = []
        for raw in events_json:
            try:
                event_id = raw.get("id")
                name = raw.get("name") or ""
                start_at = raw.get("start_at") or ""
                url = raw.get("url") or ""
                timezone_name = raw.get("timezone_name") or "America/Chicago"

                if not event_id or not start_at or not url:
                    continue

                performers = SquadUpEvent.extract_performers(name)
                results.append(
                    SquadUpEvent(
                        event_id=int(event_id),
                        name=name,
                        start_at=start_at,
                        url=url,
                        timezone_name=timezone_name,
                        performers=performers,
                    )
                )
            except Exception as e:
                Logger.error(
                    f"SquadUpExtractor: failed to parse event id={raw.get('id')}: {e}"
                )
        return results
