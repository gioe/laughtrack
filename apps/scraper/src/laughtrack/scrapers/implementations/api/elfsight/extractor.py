"""Elfsight Event Calendar event extraction from the widget events API."""

import re
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.elfsight import ElfsightEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.html.utils import HtmlUtils
from laughtrack.utilities.domain.show.factory import is_comedy_event

_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


class ElfsightExtractor:
    """Converts the Elfsight events API payload into ElfsightEvent objects."""

    @staticmethod
    def extract_events(
        payload: Optional[List[Dict[str, Any]]],
        page_url: str,
        comedy_filter: bool = False,
    ) -> List[ElfsightEvent]:
        """Extract ElfsightEvent objects from the events API ``payload`` array.

        ``page_url`` is the venue's own calendar page; it becomes each show's
        ``show_page_url`` and the ticket fallback when an event carries no link.

        When ``comedy_filter`` is True (opt-in via the source's ``comedy_filter``
        metadata flag for mixed-use venues), events whose name and description
        carry no comedy keyword are dropped so non-comedy programming (film
        screenings, live music, drama) does not surface.
        """
        if not isinstance(payload, list):
            return []

        events: List[ElfsightEvent] = []
        for raw in payload:
            try:
                event = ElfsightExtractor._parse_event(raw, page_url, comedy_filter)
                if event:
                    events.append(event)
            except Exception as e:
                Logger.warn(f"ElfsightExtractor: skipping event due to error: {e}")
        return events

    @staticmethod
    def _parse_event(
        raw: Dict[str, Any], page_url: str, comedy_filter: bool
    ) -> Optional[ElfsightEvent]:
        """Parse a single raw Elfsight event dict, or None to skip."""
        if not isinstance(raw, dict):
            return None

        name = (raw.get("name") or "").strip()
        start = raw.get("start") or {}
        start_iso = (start.get("dateTime") or start.get("date") or "").strip()
        if not name or not start_iso:
            return None

        description_html = raw.get("description") or ""

        if comedy_filter and not is_comedy_event(name, HtmlUtils.strip_tags(description_html)):
            Logger.info(f"Skipping non-comedy Elfsight event: {name!r}")
            return None

        return ElfsightEvent(
            name=name,
            start_iso=start_iso,
            page_url=page_url,
            description_html=description_html,
            ticket_url=ElfsightExtractor._ticket_url(raw, description_html),
            image_url=((raw.get("image") or {}).get("url") or ""),
        )

    @staticmethod
    def _ticket_url(raw: Dict[str, Any], description_html: str) -> str:
        """Best-effort ticket URL: explicit button link, else first href in the blurb."""
        button = (raw.get("buttonLink") or "").strip()
        if button:
            return button
        match = _HREF_RE.search(description_html or "")
        return match.group(1).strip() if match else ""
