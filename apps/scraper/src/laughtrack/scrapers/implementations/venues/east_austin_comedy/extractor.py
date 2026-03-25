"""East Austin Comedy event extractor for Netlify availability API responses."""

from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.east_austin_comedy import EastAustinComedyEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_DAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


class EastAustinComedyEventExtractor:
    """Parse East Austin Comedy Netlify API JSON into EastAustinComedyEvent objects.

    The availability API is queried once per weekday name:
      GET /.netlify/functions/availability?showDay={day}&offset=0

    Response structure::

        {
          "availability": {
            "2026-03-27": {
              "6:00 PM":  { "ga": { "remaining": 71, "soldOut": false }, "front-row": {...} },
              "8:00 PM":  { ... },
              "10:00 PM": { ... }
            },
            "2026-04-03": { ... },
            ...
          }
        }

    One :class:`EastAustinComedyEvent` is produced per date+time combination.
    """

    @staticmethod
    def parse_availability(
        data: Any, logger_context: Optional[Dict] = None
    ) -> List[EastAustinComedyEvent]:
        """Parse a single availability API response into a list of show slots."""
        ctx = logger_context or {}
        events: List[EastAustinComedyEvent] = []

        if not isinstance(data, dict):
            Logger.warn(
                f"EastAustinComedyEventExtractor: expected dict, got {type(data).__name__}",
                ctx,
            )
            return events

        availability = data.get("availability", {})
        if not isinstance(availability, dict):
            Logger.warn(
                "EastAustinComedyEventExtractor: 'availability' key missing or not a dict",
                ctx,
            )
            return events

        for date_str, times in availability.items():
            if not isinstance(times, dict):
                continue
            for time_str in times:
                events.append(EastAustinComedyEvent(date=date_str, time=time_str))

        return events
