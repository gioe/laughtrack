"""Laugh Boston data extraction utilities."""

from typing import Any, Dict, List

from laughtrack.foundation.infrastructure.logger.logger import Logger


class LaughBostonEventExtractor:
    """Utility class for extracting Laugh Boston event data."""

    @staticmethod
    def extract_tixr_urls_from_pixl(data: Dict[str, Any]) -> List[str]:
        """
        Extract Tixr event URLs from a Pixl Calendar API response.

        The Pixl Calendar API returns events with a ``ticketUrl`` field pointing
        to tixr.com. This method collects all such URLs for downstream fetching
        via TixrClient.

        Args:
            data: Parsed JSON from https://pixlcalendar.com/api/events/{slug}

        Returns:
            List of unique Tixr event URLs, in response order
        """
        try:
            events = data.get("events", [])
            urls = []
            for event in events:
                ticket_url = event.get("ticketUrl", "")
                if ticket_url and "tixr.com" in ticket_url and "/events/" in ticket_url:
                    urls.append(ticket_url)
            # Preserve order, deduplicate
            return list(dict.fromkeys(urls))
        except Exception as e:
            Logger.error(f"Error extracting Tixr URLs from Pixl Calendar response: {e}")
            return []
