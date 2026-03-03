from typing import Any, Dict, List, Optional

from asynciolimiter import Limiter

from laughtrack.core.entities.event.twenty_two_rams import TwentyTwoRamsEvent
from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.core.clients.base import BaseApiClient


class TwentyTwoRamsClient(BaseApiClient):
    """Client for scraping 22Rams ticketing pages."""

    def __init__(self, club: Club):
        # Initialize with rate limiter
        super().__init__(club, Limiter(1 / 3, max_burst=1))

        # Override headers for web scraping
        self.headers = BaseHeaders.get_headers("desktop_browser")

    async def fetch_event_data(self, event_url: str) -> Optional[TwentyTwoRamsEvent]:
        """
        Fetch event data from a 22Rams event URL.

        Args:
            event_url: The 22Rams event URL

        Returns:
            TwentyTwoRamsEvent containing event data, or None if failed
        """
        try:
            # Use BaseApiClient's fetch_html method with built-in error handling
            html_content = await self.fetch_html(event_url, headers=self.headers)

            if html_content is None:
                self.log_error(f"Failed to fetch HTML from {event_url}")
                return None

            # Extract JSON-LD data using shared EventExtractor
            events = EventExtractor.extract_events(html_content)

            if not events:
                self.log_warning(f"No JSON-LD event data found in {event_url}")
                return None

            # Convert the first Event to TwentyTwoRamsEvent
            first_event = events[0]
            event_dict = first_event.__dict__  # Convert Event object to dict
            return TwentyTwoRamsEvent.from_json_ld(event_dict, event_url)

        except Exception as e:
            self.log_error(f"Failed to fetch event data from {event_url}: {e}")
            return None

    async def fetch_events(self, url: Optional[str] = None) -> List[Any]:
        """Fetch events from TwentyTwoRams. This client works with direct URLs."""
        # TwentyTwoRamsClient works by getting shows from specific URLs
        # This method is required by the interface but implementation depends on usage
        return []

    async def get_show(self, url: str) -> Optional[Show]:
        """Get a Show object from a 22Rams URL."""
        event_data = await self.fetch_event_data(url)
        if not event_data:
            return None
        return self.create_show(event_data, url)

    def create_show(self, event: TwentyTwoRamsEvent, url: str) -> Optional[Show]:
        """Create a Show object from a TwentyTwoRamsEvent."""
        try:
            show_info = self._extract_basic_show_info(event, url)
            return Show.create(**show_info, timezone=self.club.timezone, club_id=self.club.id)

        except Exception as e:
            self.log_error(f"Failed to create show from {url}: {e}")
            return None

    def _extract_basic_show_info(self, event: TwentyTwoRamsEvent, url: str) -> JSONDict:
        """Extract basic show information from TwentyTwoRamsEvent."""
        return {
            "name": event.name,
            "date": event.start_date,
            "show_page_url": url,
            "description": event.description or "",
            "tickets": self._extract_ticket_data(event, url),
        }

    def _extract_ticket_data(self, event: TwentyTwoRamsEvent, url: str) -> List:
        """Extract ticket information from TwentyTwoRamsEvent."""
        from laughtrack.core.entities.ticket.model import Ticket

        tickets: List[Ticket] = []

        if not event.offers:
            return tickets

        for offer in event.offers:
            try:
                price_str = offer.get("price", "0")
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    price = 0.0

                # Check availability
                availability = offer.get("availability", "")
                sold_out = "InStock" not in availability

                ticket = Ticket(
                    price=price, purchase_url=url, sold_out=sold_out, type=offer.get("name", "General Admission")
                )
                tickets.append(ticket)

            except Exception as e:
                self.log_warning(f"Failed to extract ticket from offer: {e}")
                continue

        return tickets
