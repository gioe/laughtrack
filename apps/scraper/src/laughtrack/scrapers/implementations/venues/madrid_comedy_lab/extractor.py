"""Madrid Comedy Lab event extractor for Fienta API data."""

from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.madrid_comedy_lab import MadridComedyLabEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Titles containing these substrings are filtered out (matches website JS behaviour).
_EXCLUDED_TITLE_SUBSTRINGS = ("Gift", "Valencia")


class MadridComedyLabEventExtractor:
    """Parse Fienta API JSON into MadridComedyLabEvent objects.

    The Fienta organizer API returns::

        {
          "success": {...},
          "count": 25,
          "events": [
            {
              "id": 177670,
              "title": "Dark Humour Night",
              "starts_at": "2026-04-09 20:30:00",
              "ends_at": "2026-04-09 22:00:00",
              "url": "https://fienta.com/dark-humour-night-lab-177670",
              "address": "Calle del Amor de Dios 13, 28014 Madrid",
              "description": "<p>...</p>",
              "sale_status": "onSale",
              ...
            },
            ...
          ]
        }
    """

    @staticmethod
    def parse_events(
        data: Any, logger_context: Optional[Dict] = None
    ) -> List[MadridComedyLabEvent]:
        """Parse Fienta API response into a flat list of events.

        Args:
            data: Parsed JSON value from the Fienta organizer endpoint.
            logger_context: Logging context for error reporting.

        Returns:
            List of :class:`MadridComedyLabEvent` objects.
        """
        ctx = logger_context or {}
        events: List[MadridComedyLabEvent] = []

        if not isinstance(data, dict):
            Logger.warn(
                f"MadridComedyLabEventExtractor: expected dict, got {type(data).__name__}",
                ctx,
            )
            return events

        raw_events = data.get("events", [])
        if not isinstance(raw_events, list):
            Logger.warn(
                "MadridComedyLabEventExtractor: 'events' key is not a list",
                ctx,
            )
            return events

        for item in raw_events:
            if not isinstance(item, dict):
                continue

            title = item.get("title") or ""
            if any(sub in title for sub in _EXCLUDED_TITLE_SUBSTRINGS):
                continue

            event_id = item.get("id")
            starts_at = item.get("starts_at") or ""
            ends_at = item.get("ends_at") or ""
            url = item.get("url") or ""
            sale_status = item.get("sale_status") or ""
            description = item.get("description") or ""

            if not starts_at or not url:
                Logger.warn(
                    f"MadridComedyLabEventExtractor: event '{title}' missing starts_at or url, skipping",
                    ctx,
                )
                continue

            events.append(
                MadridComedyLabEvent(
                    event_id=event_id,
                    title=title,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    url=url,
                    sale_status=sale_status,
                    description=description,
                )
            )

        Logger.info(
            f"MadridComedyLabEventExtractor: parsed {len(events)} events",
            ctx,
        )
        return events
