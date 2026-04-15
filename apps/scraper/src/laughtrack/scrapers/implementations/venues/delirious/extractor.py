"""Extraction helpers for Delirious Comedy Club / FriendlySky API responses."""

from typing import List, Optional

from laughtrack.core.entities.event.friendlysky import FriendlySkyEvent


class DeliriousExtractor:
    """Static methods for extracting events from FriendlySky API data."""

    @staticmethod
    def extract_events(
        api_response: dict, base_url: str
    ) -> Optional[List[FriendlySkyEvent]]:
        """Extract FriendlySkyEvent objects from the API response envelope.

        Args:
            api_response: Parsed JSON from the FriendlySky events endpoint.
                Expected shape: ``{"data": {"games": [...]}, ...}``
            base_url: Base URL of the ticketing site (for constructing ticket links).

        Returns:
            List of FriendlySkyEvent objects, or None if the response has no games.
        """
        data = api_response.get("data")
        if not isinstance(data, dict):
            return None

        games = data.get("games")
        if not isinstance(games, list) or not games:
            return None

        events: List[FriendlySkyEvent] = []
        for game in games:
            if not isinstance(game, dict):
                continue
            # Only include active games
            if game.get("status") != "Y":
                continue
            events.append(FriendlySkyEvent.from_api_response(game, base_url))

        return events if events else None
