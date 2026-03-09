import json
from datetime import datetime, timedelta
from typing import Any, List, Optional

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils


class VenuePilotClient(BaseApiClient):
    """Specialized scraper for VenuePilot."""

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """Initialize the client with club data."""
        super().__init__(club, proxy_pool=proxy_pool)
        self.events_url = "https://www.venuepilot.co/graphql"

    async def fetch_events(self, venue_id: str) -> List[JSONDict]:
        payload = self.build_payload(venue_id)
        data = await self.post_json(self.events_url, payload=payload, headers=self.headers)
        return data.get("data", {}).get("publicEvents", []) if data else []

    def create_show(self, object: Any) -> Optional[Show]:
        """Create a Show object from the event data."""
        try:
            json_data = HtmlScraper.find_script_elements(object.text, "application/json")
            if not json_data:
                self.log_warning("No JSON script data found")
                return None

            json_content = json.loads(json_data[0].get_text())
            json_dict = json_content.get("_piniaInitialState").get("checkout")
            event_data = json_dict.get("selectedEvent")

            if not event_data:
                self.log_warning("No event data found")
                return None

            name = event_data.get("name")
            date = event_data.get("startTime")
            formatted_date_time = DateTimeUtils.format_utc_iso_date(date)
            description = event_data.get("description")
            slug = event_data.get("slug")
            show_page_url = f"https://tickets.venuepilot.com/e/{slug}"

            # Get tickets
            tickets = self.extract_ticket_data(json_dict, show_page_url)

            artists = event_data.get("artists", [])
            lineup = [a["name"] for a in artists if isinstance(a, dict) and "name" in a]

            show_data = {
                "name": name,
                "date": formatted_date_time,
                "description": description,
                "show_page_url": show_page_url,
                "lineup": lineup,
                "tickets": tickets,
                "supplied_tags": [],
                "timezone": None,
                "club_id": self.club.id,
                "room": "",
            }

            return Show.create(**show_data)
        except Exception as e:
            self.log_error(f"Failed to create show from {object.url}: {e}")
            return None

    def extract_ticket_data(self, event_data: JSONDict, url: str) -> List[Ticket]:
        """Extract ticket information from the event data."""
        try:
            tickets = []
            if "tickets" not in event_data:
                return tickets
            tickets_array = event_data.get("tickets", [])
            if len(tickets_array) == 0:
                return tickets

            for ticket in tickets_array:
                tickets.append(
                    Ticket(
                        price=ticket.get("breakdown", {}).get("price"),
                        purchase_url=url,
                        sold_out=ticket.get("soldOut"),
                        type=ticket.get("type"),
                    )
                )
            return tickets
        except Exception as e:
            self.log_error(f"Failed to extract ticket data: {e}")
            return []

    def build_payload(self, venue_id: str) -> str:
                today = datetime.now()
                end_date = today + timedelta(days=180)
                return json.dumps(
                        {
                                "operationName": None,
                                "variables": {
                                        "accountIds": [venue_id],
                                        "startDate": today.strftime("%Y-%m-%d"),
                                        "endDate": end_date.strftime("%Y-%m-%d"),
                                        "search": "",
                                        "searchScope": "",
                                },
                                "query": """
                                query (
                                        $accountIds: [Int!]!,
                                        $startDate: String!,
                                        $endDate: String,
                                        $search: String,
                                        $searchScope: String,
                                        $limit: Int
                                ) {
                                    publicEvents(
                                        accountIds: $accountIds,
                                        startDate: $startDate,
                                        endDate: $endDate,
                                        search: $search,
                                        searchScope: $searchScope,
                                        limit: $limit
                                    ) {
                                        id
                                        name
                                        date
                                        doorTime
                                        startTime
                                        endTime
                                        minimumAge
                                        promoter
                                        support
                                        description
                                        websiteUrl
                                        twitterUrl
                                        instagramUrl
                                        images
                                        status
                                        venue {
                                            name
                                            __typename
                                        }
                                        footerContent
                                        highlightedImage
                                        ticketsUrl
                                        __typename
                                    }
                                }
                """,
            }
        )

    def _initialize_headers(self) -> JSONDict:
        """Override to initialize VenuePilot-specific headers."""
        domain = URLUtils.get_formatted_domain(self.club.scraping_url)
        from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
        return BaseHeaders.get_headers(
            base_type="mobile_browser", domain=domain, additional_headers={"content-type": "application/json"}
        )
