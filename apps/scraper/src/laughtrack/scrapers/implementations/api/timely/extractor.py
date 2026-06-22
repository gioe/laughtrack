"""Extraction helpers for Timely calendar API responses."""

from typing import Any, Dict, Iterable, List

from laughtrack.core.entities.event.timely import TimelyEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class TimelyExtractor:
    """Converts Timely API JSON into TimelyEvent objects."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any], calendar_url: str) -> List[TimelyEvent]:
        events: List[TimelyEvent] = []
        for raw in TimelyExtractor._iter_raw_events(api_response):
            try:
                event = TimelyEvent.from_api(raw, calendar_url=calendar_url)
                if event is not None:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"TimelyExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def has_next_page(api_response: Dict[str, Any]) -> bool:
        data = api_response.get("data") if isinstance(api_response, dict) else None
        return bool(data and data.get("has_next"))

    @staticmethod
    def _iter_raw_events(api_response: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        data = api_response.get("data") if isinstance(api_response, dict) else None
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, dict):
            for day_events in items.values():
                if isinstance(day_events, list):
                    for raw in day_events:
                        if isinstance(raw, dict):
                            yield raw
        elif isinstance(items, list):
            for raw in items:
                if isinstance(raw, dict):
                    yield raw

