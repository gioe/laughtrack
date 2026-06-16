"""Squarespace event extraction from GetItemsByMonth API response."""

from typing import Any, Dict, List, Optional, Pattern

from laughtrack.core.entities.event.squarespace import SquarespaceEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class SquarespaceExtractor:
    """Converts raw Squarespace GetItemsByMonth JSON into SquarespaceEvent objects."""

    @staticmethod
    def extract_events(
        api_response: List[Dict[str, Any]],
        base_domain: str,
        exclude_title_re: Optional[Pattern[str]] = None,
    ) -> List[SquarespaceEvent]:
        """Extract SquarespaceEvent objects from the GetItemsByMonth API response.

        Args:
            api_response: JSON array returned by the GetItemsByMonth endpoint.
            base_domain: Base URL of the venue site (e.g. "https://thedentheatre.com").
            exclude_title_re: Optional compiled regex; events whose title matches
                are skipped. Used by venues whose events collection mixes public
                shows with non-show entries (e.g. improv-theatre class sessions /
                workshops). Default None keeps every event.

        Returns:
            List of SquarespaceEvent objects.
        """
        if not isinstance(api_response, list):
            return []

        events = []
        for raw in api_response:
            try:
                event = SquarespaceExtractor._parse_event(raw, base_domain)
                if not event:
                    continue
                if exclude_title_re is not None and exclude_title_re.search(event.title):
                    Logger.debug(
                        f"SquarespaceExtractor: excluding non-show '{event.title}' "
                        f"(matched exclude_title_patterns)"
                    )
                    continue
                events.append(event)
            except Exception as e:
                Logger.warn(f"SquarespaceExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any], base_domain: str) -> SquarespaceEvent | None:
        """Parse a single raw event dict, returning None to skip invalid entries."""
        event_id = raw.get("id") or ""
        if not event_id:
            return None

        title = (raw.get("title") or "").strip()
        if not title:
            return None

        start_date_ms = raw.get("startDate")
        if not isinstance(start_date_ms, (int, float)):
            return None

        full_url = raw.get("fullUrl") or ""
        excerpt = raw.get("excerpt") or ""

        return SquarespaceEvent(
            id=str(event_id),
            title=title,
            start_date_ms=int(start_date_ms),
            full_url=full_url,
            base_domain=base_domain,
            excerpt=excerpt,
        )
