"""Creek and Cave event extractor for S3 monthly JSON data."""

from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.creek_and_cave import CreekAndCaveEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class CreekAndCaveEventExtractor:
    """Parse Creek and Cave S3 monthly JSON into CreekAndCaveEvent objects.

    The S3 monthly JSON is structured as::

        {
          "25": [
            {
              "event": {
                "name": "Off The Cuff",
                "slug": "off-the-cuff",
                "date": "2026-03-25T23:00:00.000Z",
                "shows": [
                  {
                    "time": "6:00 pm",
                    "listing_url": "https://www.showclix.com/event/off-the-cuffwv5n1ol",
                    "date": "2026-03-25T23:00:00.000Z",
                    "inventory": 195
                  }
                ]
              },
              "hours": 18,
              "minutes": 0
            }
          ],
          "26": [...],
          ...
        }

    One :class:`CreekAndCaveEvent` is produced per ``shows`` entry.
    """

    @staticmethod
    def parse_monthly_json(
        data: Any, logger_context: Optional[Dict] = None
    ) -> List[CreekAndCaveEvent]:
        """Parse the S3 monthly JSON response into a flat list of show slots.

        Args:
            data: Parsed JSON value from the S3 monthly endpoint.
            logger_context: Logging context for error reporting.

        Returns:
            List of :class:`CreekAndCaveEvent` objects, one per show slot.
        """
        ctx = logger_context or {}
        events: List[CreekAndCaveEvent] = []

        if not isinstance(data, dict):
            Logger.warn(
                f"CreekAndCaveEventExtractor: expected dict, got {type(data).__name__}",
                ctx,
            )
            return events

        for day_key, day_entries in data.items():
            if not isinstance(day_entries, list):
                continue

            for entry in day_entries:
                if not isinstance(entry, dict):
                    continue

                event_data = entry.get("event", {})
                if not isinstance(event_data, dict):
                    continue

                slug = event_data.get("slug") or ""
                name = event_data.get("name") or ""
                shows = event_data.get("shows", [])

                if not slug or not name:
                    Logger.warn(
                        f"CreekAndCaveEventExtractor: skipping entry missing slug/name on day {day_key}",
                        ctx,
                    )
                    continue

                if not isinstance(shows, list) or not shows:
                    Logger.warn(
                        f"CreekAndCaveEventExtractor: event '{name}' has no shows, skipping",
                        ctx,
                    )
                    continue

                for show in shows:
                    if not isinstance(show, dict):
                        continue

                    date_utc = show.get("date") or ""
                    time_local = show.get("time") or ""
                    listing_url = show.get("listing_url") or ""
                    inventory = show.get("inventory")

                    if not date_utc or not listing_url:
                        Logger.warn(
                            f"CreekAndCaveEventExtractor: show missing date/url for '{name}', skipping",
                            ctx,
                        )
                        continue

                    events.append(
                        CreekAndCaveEvent(
                            slug=slug,
                            name=name,
                            date_utc=date_utc,
                            time_local=time_local,
                            listing_url=listing_url,
                            inventory=inventory,
                        )
                    )

        Logger.info(
            f"CreekAndCaveEventExtractor: parsed {len(events)} show slots",
            ctx,
        )
        return events
