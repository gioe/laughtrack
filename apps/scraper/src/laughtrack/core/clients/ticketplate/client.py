import json
from typing import Any, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class TicketplateClient(BaseApiClient):
    """Specialized scraper for Eventbrite pages."""

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """Initialize the client with club data."""
        super().__init__(club, proxy_pool=proxy_pool)
        # Headers are initialized via _initialize_headers

    async def get_event_detail(self, slug: str) -> Any:
        new_url = f"https://get.ticketplate.com/clients-api/events/{slug}/detail-by-slug/"
        # Use BaseApiClient helper to fetch JSON
        return await self.fetch_json(new_url, headers=self.headers)

    async def fetch_events(self, slug: str = "") -> List[Any]:
        """Fetch events from Ticketplate. This client works with event slugs."""
        # TicketplateClient works by getting event details from specific slugs
        # This method is required by the interface but implementation depends on usage
        return []

    def create_show(self, response: Any) -> Optional[Show]:
        """Create a Show object from the Eventbrite response data."""
        try:
            # If response is a JSON string, load it; if it's already a dict, use directly
            json_response = json.loads(response) if isinstance(response, str) else response
            show_info = self._extract_basic_show_info(json_response)
            tickets = self._extract_ticket_data(show_info.get("offers", []), show_info.get("url", ""))

            return Show.create(**show_info, tickets=tickets, timezone=self.club.timezone, club_id=self.club.id)

        except KeyError as key:
            self.log_warning(f"Error finding key {key} while creating show")
        except Exception as e:
            self.log_warning(f"Scraping show failed with error: {e}")

        return None

    def _extract_basic_show_info(self, primary_dict: JSONDict) -> JSONDict:
        return {
            "name": primary_dict.get("name", ""),
            "date": DateTimeUtils.format_iso8601_date(primary_dict.get("datetime", "")),
            "url": f"https://ticketplate.com/checkout/{primary_dict.get('slug')}",
            "offers": primary_dict.get("sections", []),
        }

    def _extract_ticket_data(self, offers: List[JSONDict], url: str) -> List[Ticket]:
        """Extract ticket information from the ticket data."""
        try:
            if not offers:
                return []

            # Use a dictionary to deduplicate tickets by type
            tickets_by_type = {}

            for offer in offers:
                try:
                    ticket_type = offer.get("type")
                    # Only keep the first occurrence of each ticket type
                    if ticket_type not in tickets_by_type and offer.get("isOnSale") is True:
                        tickets_by_type[ticket_type] = Ticket(
                            price=offer.get("price", 0),
                            sold_out=offer.get("sold_out", False),
                            purchase_url=url,
                            type=str(ticket_type or "General Admission"),
                        )
                except Exception as e:
                    self.log_warning(f"Failed to extract ticket data from ticket: {e}")
                    continue

            return list(tickets_by_type.values())
        except Exception as e:
            self.log_warning(f"Failed to extract ticket data: {e}")
            return []

    def _initialize_headers(self) -> JSONDict:
        """Override to initialize Ticketplate-specific headers."""
        return BaseHeaders.get_headers(base_type="mobile_browser", domain="https://ticketplate.com")


def scrape_ticketplate_page(response: Any, club: Club) -> Optional[Show]:
    """Factory function to create and use the TicketplateClient."""
    scraper = TicketplateClient(club)
    return scraper.create_show(response)
