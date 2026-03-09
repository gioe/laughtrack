"""
Data model representing a single event from StandUp NY's multi-source workflow.

This model combines data from GraphQL API responses (ShowTix4U/VenuePilot)
and enhanced VenuePilot ticket data into a unified event structure.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StandupNYEvent:
    """
    Data model representing a single event from StandUp NY's multi-source workflow.

    This combines data from:
    - GraphQL API (ShowTix4U/VenuePilot public events)
    - VenuePilot ticket page data (enhanced ticket information)
    """

    # Core event information (from GraphQL)
    id: str
    name: str
    date: str  # ISO date string
    start_time: str  # Time string from GraphQL
    ticket_url: str

    # Optional GraphQL fields
    description: Optional[str] = None
    door_time: Optional[str] = None
    end_time: Optional[str] = None
    minimum_age: Optional[int] = None
    venue_name: Optional[str] = None
    footer_content: Optional[str] = None
    images: Optional[List[str]] = None
    website_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    promoter: Optional[str] = None  # Headliner comedian name(s) from GraphQL
    support: Optional[str] = None  # Supporting comedian name(s) from GraphQL

    # VenuePilot enhanced data (if available)
    venue_pilot_event: Optional[Dict[str, Any]] = None
    venue_pilot_tickets: Optional[List[Dict[str, Any]]] = None
    venue_pilot_slug: Optional[str] = None

    # Source tracking
    has_venue_pilot_data: bool = False
    graphql_source: str = "unknown"  # "showtix4u" or "venuepilot"

    # Raw data preservation for debugging
    _raw_graphql_data: Optional[Dict[str, Any]] = None
    _raw_venue_pilot_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_graphql_event(cls, graphql_data: Dict[str, Any], source: str = "unknown") -> "StandupNYEvent":
        """
        Create StandupNYEvent from GraphQL API response data.

        Args:
            graphql_data: Raw event data from GraphQL response
            source: Source API ("showtix4u" or "venuepilot")

        Returns:
            StandupNYEvent instance
        """
        return cls(
            id=str(graphql_data.get("id", "")),
            name=graphql_data.get("name", ""),
            date=graphql_data.get("date", ""),
            start_time=graphql_data.get("startTime", ""),
            ticket_url=graphql_data.get("ticketsUrl", ""),
            description=graphql_data.get("description"),
            door_time=graphql_data.get("doorTime"),
            end_time=graphql_data.get("endTime"),
            minimum_age=graphql_data.get("minimumAge"),
            venue_name=graphql_data.get("venue", {}).get("name") if graphql_data.get("venue") else None,
            footer_content=graphql_data.get("footerContent"),
            images=graphql_data.get("images"),
            website_url=graphql_data.get("websiteUrl"),
            instagram_url=graphql_data.get("instagramUrl"),
            twitter_url=graphql_data.get("twitterUrl"),
            promoter=graphql_data.get("promoter"),
            support=graphql_data.get("support"),
            graphql_source=source,
            _raw_graphql_data=graphql_data,
        )

    def add_venue_pilot_data(self, venue_pilot_data: Dict[str, Any]) -> None:
        """
        Add VenuePilot enhancement data to this event.

        Args:
            venue_pilot_data: Combined venue pilot data from extract_data
        """
        if not venue_pilot_data:
            return

        self.has_venue_pilot_data = True

        # Extract VenuePilot specific data
        pinia_data = venue_pilot_data.get("venue_pilot_data", {})
        selected_event = pinia_data.get("selectedEvent", {})

        if selected_event:
            self.venue_pilot_event = selected_event
            self.venue_pilot_slug = selected_event.get("slug")

        # Extract ticket data
        tickets_array = pinia_data.get("tickets", [])
        if tickets_array:
            self.venue_pilot_tickets = tickets_array

        # Store raw data
        self._raw_venue_pilot_data = venue_pilot_data

    def get_effective_name(self) -> str:
        """Get the best available event name."""
        if self.venue_pilot_event and self.venue_pilot_event.get("name"):
            return self.venue_pilot_event["name"]
        return self.name

    def get_effective_description(self) -> Optional[str]:
        """Get the best available description."""
        if self.venue_pilot_event and self.venue_pilot_event.get("description"):
            return self.venue_pilot_event["description"]
        return self.description or self.footer_content

    def get_effective_ticket_url(self) -> str:
        """Get the best available ticket URL."""
        if self.venue_pilot_slug:
            return f"https://tickets.venuepilot.com/e/{self.venue_pilot_slug}"
        return self.ticket_url

    def has_enhanced_ticket_data(self) -> bool:
        """Check if this event has enhanced VenuePilot ticket information."""
        return bool(self.venue_pilot_tickets)

    def get_ticket_count(self) -> int:
        """Get the number of ticket types available."""
        if self.venue_pilot_tickets:
            return len(self.venue_pilot_tickets)
        return 1 if self.ticket_url else 0

    def get_lineup_names(self) -> List[str]:
        """
        Return comedian names for the show lineup.

        Priority:
        1. VenuePilot selectedEvent performers list
        2. GraphQL promoter / support fields (comma-separated strings)
        """
        # 1. VenuePilot performers
        if self.venue_pilot_event:
            performers = self.venue_pilot_event.get("performers") or []
            if performers and isinstance(performers, list):
                names = []
                for p in performers:
                    if isinstance(p, dict):
                        name = p.get("name") or p.get("displayName") or ""
                    else:
                        name = str(p)
                    if name.strip():
                        names.append(name.strip())
                if names:
                    return names

        # 2. GraphQL promoter / support fields
        names: List[str] = []
        for field_value in [self.promoter, self.support]:
            if not field_value:
                continue
            for name in field_value.split(","):
                cleaned = name.strip()
                if cleaned:
                    names.append(cleaned)
        return names
