"""Gotham Comedy Club S3 monthly response data model."""

from dataclasses import dataclass
from typing import Any, Dict, List

from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.core.entities.show.local.gotham_show import GothamShow


@dataclass
class GothamMonthlyResponse:
    """
    Data model for the complete S3 monthly JSON response.

    The response structure is:
    {
        "1": [GothamEvent, ...],
        "2": [GothamEvent, ...],
        ...
        "31": [GothamEvent, ...]
    }

    Where each key is a day of the month (as string) and each value
    is a list of events happening on that day.
    """

    days: Dict[str, List[GothamEvent]]

    def __post_init__(self):
        """Validate the response structure."""
        if not isinstance(self.days, dict):
            raise ValueError("days must be a dictionary")

        for day_key, events_list in self.days.items():
            if not isinstance(day_key, str):
                raise ValueError(f"Day key must be string, got {type(day_key)}")
            if not isinstance(events_list, list):
                raise ValueError(f"Events for day {day_key} must be a list")
            for i, event_data in enumerate(events_list):
                if not isinstance(event_data, GothamEvent):
                    raise ValueError(f"Event {i} for day {day_key} must be GothamEvent")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GothamMonthlyResponse":
        """
        Create a GothamMonthlyResponse from the raw S3 JSON dictionary.

        Args:
            data: Raw dictionary from S3 JSON response

        Returns:
            GothamMonthlyResponse instance with validated data
        """
        days = {}

        for day_key, events_list in data.items():
            if isinstance(events_list, list):
                validated_events = []
                for event_dict in events_list:
                    if isinstance(event_dict, dict):
                        # Extract the nested event object
                        nested_event = event_dict.get("event", {})

                        # Convert shows data to GothamShow objects
                        shows_data = nested_event.get("shows", [])
                        shows = []
                        for show_data in shows_data:
                            try:
                                show = GothamShow(
                                    time=show_data.get("time", ""),
                                    listing_url=show_data.get("listing_url", ""),
                                    date=show_data.get("date", ""),
                                    inventory=show_data.get("inventory"),
                                )
                                shows.append(show)
                            except (ValueError, TypeError):
                                # Skip invalid show data
                                continue

                        # Create GothamEvent with proper parameters
                        event_data = GothamEvent(
                            id=nested_event.get("slug", "unknown"),
                            name=nested_event.get("name", ""),
                            date=nested_event.get("date", ""),
                            hours=event_dict.get("hours", 20),  # Default 8 PM
                            minutes=event_dict.get("minutes", 0),  # Default 0 minutes
                            slug=nested_event.get("slug"),
                            shows=shows,
                            _raw_data=event_dict,
                        )
                        validated_events.append(event_data)
                days[day_key] = validated_events

        return cls(days=days)

    def flatten_events(self) -> List[GothamEvent]:
        """
        Flatten all shows from all events across all days into a single list.

        This creates individual GothamEvent instances for each show, where each
        GothamEvent contains the shared event details (name, slug, thumbnail)
        but with the specific show details (date, inventory).

        Returns:
            List of GothamEvent objects, one for each individual show
        """
        all_events = []
        for events_list in self.days.values():
            for event in events_list:
                if event.shows:
                    for show in event.shows:
                        # Create a new GothamEvent for each show, sharing event-level details
                        # but using the specific show's date and inventory
                        individual_event = GothamEvent(
                            id=event.id,
                            name=event.name,
                            date=show.date,  # Use show's specific date
                            hours=event.hours,
                            minutes=event.minutes,
                            slug=event.slug,
                            shows=[show],  # Single show for this event instance
                            _raw_data=event._raw_data,
                        )
                        all_events.append(individual_event)
        return all_events

    def get_events_for_day(self, day: str) -> List[GothamEvent]:
        """
        Get events for a specific day.

        Args:
            day: Day number as string (e.g., "1", "15", "31")

        Returns:
            List of events for that day, or empty list if no events
        """
        return self.days.get(day, [])
