"""JSON-LD data extraction utilities."""

from typing import Any, List, Set

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.core.entities.event.event import JsonLdEvent


class EventExtractor:
    """Utility class for extracting JSON-LD event dictionaries from HTML content."""

    @staticmethod
    def extract_events(
        html_content: str,
        *,
        same_as_override: str | None = None,
    ) -> List[JsonLdEvent]:
        """
        Extract JSON-LD data from HTML content.

        Args:
            html_content: HTML content to parse
            extract_events_only: If True, recursively extract only Event/ComedyEvent objects.
                                If False, return all JSON-LD objects as-is.

        Returns:
            List of Event dictionaries found in the HTML (all objects or events only)
        """
        # Use the HtmlScraper utility method to extract JSON-LD data
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)

        if not script_contents:
            return []

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return []

        # For non-event-only extraction, return all JSON-LD objects that look like events
        return EventExtractor._extract_events_from_data(
            json_objects,
            same_as_override=same_as_override,
        )

    @staticmethod
    def extract_event_field_values(html_content: str, field_path: str) -> Set[str]:
        """Extract string values from a JSON-LD field on Event objects.

        ``field_path`` supports dotted lookup for nested dictionaries. If the
        resolved value is a list, string members are returned.
        """
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return set()

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return set()

        values: Set[str] = set()
        for item in json_objects:
            for event in EventExtractor._extract_events_recursively(item):
                for value in EventExtractor._field_values(event, field_path):
                    values.add(value)
        return values

    @staticmethod
    def _field_values(obj: dict[str, Any], field_path: str) -> List[str]:
        value: Any = obj
        for part in field_path.split("."):
            if not isinstance(value, dict):
                return []
            value = value.get(part)

        if isinstance(value, str) and value:
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str) and item]
        return []

    @staticmethod
    def _extract_events_recursively(obj, processed_keys=None):
        """
        Recursively extract event dicts from a JSON-LD object or structure.

        Args:
            obj: The object to search for events (dict, list, or other)
            processed_keys: Set of keys already processed to avoid infinite recursion

        Returns:
            List of event dictionaries found in the object
        """
        if processed_keys is None:
            processed_keys = set()

        events = []
        if isinstance(obj, list):
            for item in obj:
                events.extend(EventExtractor._extract_events_recursively(item, processed_keys))
        elif isinstance(obj, dict):
            # If this dict looks like an event, add it (case-insensitive)
            event_type = obj.get("@type", "")
            if isinstance(event_type, list):
                event_type = " ".join(event_type)
            event_type_lower = event_type.lower()

            # Only match actual event types, not event-containing words
            if event_type_lower in ("event", "comedyevent") or (
                "event" in event_type_lower and event_type_lower not in ("eventseries", "eventlisting", "eventschedule")
            ):
                events.append(obj)

            # Special handling for Events key to avoid double-processing
            if "Events" in obj:
                events.extend(EventExtractor._extract_events_recursively(obj["Events"], processed_keys))
                processed_keys.add("Events")

            # Check other values, but skip already processed keys
            for key, value in obj.items():
                if key not in processed_keys and isinstance(value, (dict, list)):
                    events.extend(EventExtractor._extract_events_recursively(value, processed_keys))

        return events

    @staticmethod
    def _extract_events_from_data(
        json_ld_data: List[JSONDict],
        *,
        same_as_override: str | None = None,
    ) -> List[JsonLdEvent]:
        """
        Extract events from already-parsed JSON-LD data using recursive logic.

        Args:
            json_ld_data: List of already-parsed JSON-LD objects

        Returns:
            List of Event dictionaries found in the data
        """
        all_events = []
        for item in json_ld_data:
            all_events.extend(EventExtractor._extract_events_recursively(item))

        # Deduplicate events by their string representation
        seen = set()
        unique_events = []
        for event in all_events:
            event_str = str(sorted(event.items()))
            if event_str in seen:
                continue

            seen.add(event_str)
            # Build using the model factory to tolerate extra keys like '@context'
            try:
                parsed_event = JsonLdEvent.from_json_ld(event)
                if same_as_override:
                    parsed_event.same_as = same_as_override
                unique_events.append(parsed_event)
            except Exception:
                # If parsing fails, skip the event; upstream scrapers may log details
                continue

        return unique_events
