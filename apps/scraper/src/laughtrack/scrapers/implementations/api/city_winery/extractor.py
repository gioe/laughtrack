"""City Winery API response extraction."""

from typing import Any

from laughtrack.core.entities.event.city_winery import CityWineryEvent


class CityWineryExtractor:
    """Converts City Winery API event dictionaries into domain events."""

    @staticmethod
    def extract_events(raw_events: list[dict[str, Any]]) -> list[CityWineryEvent]:
        events: list[CityWineryEvent] = []
        for raw in raw_events:
            event = CityWineryEvent.from_dict(raw)
            if event is not None:
                events.append(event)
        return events
