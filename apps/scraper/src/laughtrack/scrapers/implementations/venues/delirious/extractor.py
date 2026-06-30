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

    @staticmethod
    def extract_package_hash(pkgs_response: dict) -> Optional[str]:
        """Pull the package hashId from a /rest/pkgs response.

        The ``findByGameIdAndUrlName`` branch returns ``{"data": {"hashId": ...}}``
        where ``data.hashId`` is the package hash needed by the firstPage call.
        Returns ``None`` when the envelope is missing or malformed.
        """
        if not isinstance(pkgs_response, dict):
            return None
        data = pkgs_response.get("data")
        if not isinstance(data, dict):
            return None
        pkg_hash = data.get("hashId")
        return pkg_hash if isinstance(pkg_hash, str) and pkg_hash else None

    @staticmethod
    def extract_min_price(firstpage_response: dict) -> Optional[float]:
        """Return the minimum face price from a /rest/onlinePageDispatcher/firstPage response.

        Prices live at ``data.targetPkgItems[*].item.price`` (face price, one
        entry per price level). The minimum is the show's starting price.
        Returns ``None`` when no parseable price is present so the caller can
        degrade to a price-less ticket.
        """
        if not isinstance(firstpage_response, dict):
            return None
        data = firstpage_response.get("data")
        if not isinstance(data, dict):
            return None
        items = data.get("targetPkgItems")
        if not isinstance(items, list):
            return None

        prices: List[float] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            item = entry.get("item")
            if not isinstance(item, dict):
                continue
            raw = item.get("price")
            if raw is None:
                continue
            try:
                prices.append(float(raw))
            except (TypeError, ValueError):
                continue

        return min(prices) if prices else None
