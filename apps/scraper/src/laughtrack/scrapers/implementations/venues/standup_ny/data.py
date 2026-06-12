"""
Data model representing extracted data from StandUp NY's multi-step workflow.

This contains the raw events data after GraphQL extraction and VenuePilot enhancement.
"""

from dataclasses import dataclass
from typing import List, Optional

from laughtrack.core.entities.event.standup_ny import StandupNYEvent



@dataclass
class StandupNYPageData:
    """
    Data model representing raw extracted data from StandUp NY's workflow.

    Contains events from both GraphQL discovery phase and VenuePilot enhancement phase.
    """

    event_list: List[StandupNYEvent]

    # Convenience helpers used by scraper
    def get_venue_pilot_urls(self) -> List[str]:
        """Return VenuePilot ticket URLs for events that have them."""
        urls: List[str] = []
        for ev in self.event_list:
            url = getattr(ev, "ticket_url", None)
            if url and isinstance(url, str) and "venuepilot" in url.lower():
                urls.append(url)
        return urls

    def get_enhancement_urls(self) -> List[str]:
        """Return ticket URLs that have a price-enhancement path.

        VenuePilot pages carry pinia ticket data; square.link pages redirect to
        checkout.square.site whose embedded JSON carries price_money tiers
        (the venue moved paid checkout to Square ~May 2026, TASK-2836).
        """
        urls: List[str] = []
        for ev in self.event_list:
            url = getattr(ev, "ticket_url", None)
            if not url or not isinstance(url, str):
                continue
            lowered = url.lower()
            if "venuepilot" in lowered or "square.link" in lowered:
                urls.append(url)
        return urls

    def get_event_count(self) -> int:
        """Return total number of events extracted."""
        return len(self.event_list)

    def find_event_by_ticket_url(self, url: str) -> Optional[StandupNYEvent]:
        """Find an event by its ticket URL."""
        for ev in self.event_list:
            if getattr(ev, "ticket_url", None) == url:
                return ev
        return None