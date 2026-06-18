"""Wix Events event extraction from the paginated-events API response."""

from typing import Any, Dict, List

from laughtrack.core.entities.event.wix_events import WixEventsEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.show.factory import is_comedy_event


class WixEventsExtractor:
    """Converts raw Wix Events API JSON into WixEventsEvent objects."""

    @staticmethod
    def extract_events(
        api_response: Dict[str, Any], comedy_filter: bool = False
    ) -> List[WixEventsEvent]:
        """Extract WixEventsEvent objects from the Wix paginated-events API response.

        When comedy_filter is True (opt-in via the source's `comedy_filter`
        metadata flag for mixed-use venues, e.g. jazz clubs), events whose title
        and description carry no comedy keyword are dropped so the venue's
        non-comedy programming does not surface. The Wix paginated-events API
        exposes no category field, so the keyword match is the only signal.
        """
        events = []
        for raw in api_response.get("events", []):
            try:
                event = WixEventsExtractor._parse_event(raw)
                if not event:
                    continue
                if comedy_filter and not is_comedy_event(event.title, event.description):
                    Logger.info(f"Skipping non-comedy Wix event: {event.title!r}")
                    continue
                events.append(event)
            except Exception as e:
                Logger.warn(f"WixEventsExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any]) -> WixEventsEvent:
        """Parse a single raw event dict into a WixEventsEvent."""
        return WixEventsEvent(
            id=raw.get("id", ""),
            title=raw.get("title", "").strip(),
            description=raw.get("description", "").strip(),
            slug=raw.get("slug", ""),
            scheduling=raw.get("scheduling", {}),
            registration=raw.get("registration", {}),
        )
