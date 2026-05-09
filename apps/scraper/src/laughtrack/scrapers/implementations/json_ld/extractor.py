"""JSON-LD data extraction utilities."""

from typing import Any, Iterable, List, Set

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
        return EventExtractor.extract_typed_field_values(
            html_content,
            object_type="Event",
            field_path=field_path,
        )

    @staticmethod
    def extract_typed_field_values(
        html_content: str,
        *,
        object_type: str,
        field_path: str,
    ) -> Set[str]:
        """Extract string values from JSON-LD objects of ``object_type``.

        ``field_path`` supports dotted dictionary lookup and ``[]`` list
        traversal segments, such as ``mainEntity.itemListElement[].url``.
        The special ``object_type="Event"`` path preserves the existing
        recursive Event/ComedyEvent matching semantics.
        """
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return set()

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return set()

        values: Set[str] = set()
        for item in json_objects:
            for obj in EventExtractor._extract_objects_by_type(item, object_type):
                for value in EventExtractor._field_values(obj, field_path):
                    values.add(value)
        return values

    @staticmethod
    def _field_values(obj: dict[str, Any], field_path: str) -> List[str]:
        values: Iterable[Any] = [obj]
        for raw_part in field_path.split("."):
            traverse_list = raw_part.endswith("[]")
            part = raw_part[:-2] if traverse_list else raw_part
            next_values: list[Any] = []

            for value in values:
                if isinstance(value, list) and not traverse_list:
                    candidates = value
                else:
                    candidates = [value]

                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    resolved = candidate.get(part)
                    if traverse_list:
                        if isinstance(resolved, list):
                            next_values.extend(resolved)
                    else:
                        next_values.append(resolved)

            values = next_values

        strings: list[str] = []
        for value in values:
            if isinstance(value, str) and value:
                strings.append(value)
            elif isinstance(value, list):
                strings.extend(item for item in value if isinstance(item, str) and item)
        return strings

    @staticmethod
    def _extract_objects_by_type(obj: Any, object_type: str) -> list[dict[str, Any]]:
        if object_type.lower() == "event":
            return EventExtractor._extract_events_recursively(obj)
        return EventExtractor._extract_objects_by_exact_type_recursively(obj, object_type)

    @staticmethod
    def _extract_objects_by_exact_type_recursively(obj: Any, object_type: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        if isinstance(obj, list):
            for item in obj:
                matches.extend(EventExtractor._extract_objects_by_exact_type_recursively(item, object_type))
        elif isinstance(obj, dict):
            if EventExtractor._json_ld_type_matches(obj.get("@type"), object_type):
                matches.append(obj)
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    matches.extend(EventExtractor._extract_objects_by_exact_type_recursively(value, object_type))
        return matches

    @staticmethod
    def _json_ld_type_matches(raw_type: Any, expected_type: str) -> bool:
        expected = expected_type.lower()
        if isinstance(raw_type, list):
            return any(isinstance(item, str) and item.lower() == expected for item in raw_type)
        return isinstance(raw_type, str) and raw_type.lower() == expected

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
