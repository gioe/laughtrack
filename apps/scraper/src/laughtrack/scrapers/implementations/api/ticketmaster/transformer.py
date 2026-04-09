"""
Transformer for Ticketmaster API event data to Show objects.

This integrates Ticketmaster with the shared transformation pipeline.
Filters non-comedy events using Ticketmaster classifications metadata.
"""

from typing import List, Optional

from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.clients.ticketmaster.client import TicketmasterClient

_COMEDY_GENRE_NAMES = {"comedy", "stand-up comedy", "standup comedy"}

# Genres that are effectively uncategorised — treat the same as missing genre
_UNCATEGORISED_GENRE_NAMES = {"miscellaneous", "undefined", "other"}


class TicketmasterEventTransformer(DataTransformer[JSONDict]):
    def can_transform(self, raw_data: JSONDict) -> bool:  # type: ignore[override]
        # Basic shape check for Ticketmaster API events
        return isinstance(raw_data, dict) and ("id" in raw_data or "dates" in raw_data)

    def transform_to_show(self, raw_data: JSONDict, source_url: Optional[str] = None) -> Optional[Show]:  # type: ignore[override]
        try:
            if not self._is_comedy_event(raw_data):
                event_name = raw_data.get("name", "unknown")
                genres = self._get_genre_names(raw_data)
                Logger.info(
                    f"{self._log_prefix}: Skipping non-comedy event '{event_name}' "
                    f"(genres: {', '.join(genres) if genres else 'none'})"
                )
                return None

            client = TicketmasterClient(self.club)
            return client.create_show(raw_data)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}")
            return None

    @staticmethod
    def _get_genre_names(event_data: JSONDict) -> List[str]:
        """Extract all genre names from event classifications."""
        genres = []
        for classification in event_data.get("classifications", []):
            genre = classification.get("genre", {})
            if genre and genre.get("name"):
                genres.append(genre["name"])
            sub_genre = classification.get("subGenre", {})
            if sub_genre and sub_genre.get("name"):
                genres.append(sub_genre["name"])
        return genres

    @staticmethod
    def _is_comedy_event(event_data: JSONDict) -> bool:
        """Check if a Ticketmaster event is a comedy event.

        Inspects classifications[].genre.name and classifications[].subGenre.name
        for comedy-related genres. Events with no classifications — or with only
        uncategorised/empty genre metadata — are allowed through to avoid dropping
        events that lack proper tagging (e.g. The Second City uses segment
        "Arts & Theatre" with empty or "Miscellaneous" genre).
        """
        classifications = event_data.get("classifications", [])
        if not classifications:
            return True

        for classification in classifications:
            genre = classification.get("genre", {})
            genre_name = genre.get("name", "").lower() if genre else ""
            if genre_name in _COMEDY_GENRE_NAMES:
                return True
            sub_genre = classification.get("subGenre", {})
            sub_genre_name = sub_genre.get("name", "").lower() if sub_genre else ""
            if sub_genre_name in _COMEDY_GENRE_NAMES:
                return True

        # If every classification has empty or uncategorised genre info, treat the
        # event as unclassified and allow it through — the venue was explicitly
        # onboarded as a comedy club, so the event is very likely comedy.
        for classification in classifications:
            genre = classification.get("genre", {})
            genre_name = genre.get("name", "").lower() if genre else ""
            if genre_name and genre_name not in _UNCATEGORISED_GENRE_NAMES:
                return False
        return True
