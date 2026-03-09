"""
Showclix API client for fetching event web pages and API data.

This client handles interactions with Showclix event pages and API endpoints
to fetch HTML content and structured event data for events hosted on the
Showclix platform.
"""

from typing import Dict, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.clients.showclix.models import ShowclixEventData
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ShowclixAPIClient(BaseApiClient):
    """
    Client for interacting with Showclix event pages.

    This class handles:
    - Fetching HTML content from Showclix event pages
    - Proper headers for Showclix requests
    - Error handling and logging
    """

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """
        Initialize the Showclix client.

        Args:
            club: Club instance for context
            proxy_pool: Optional ProxyPool for rotating proxy support.
        """
        super().__init__(club, proxy_pool=proxy_pool)

    def _initialize_headers(self) -> Dict[str, str]:
        """Initialize headers optimized for Showclix requests."""
        return BaseHeaders.get_headers(
            base_type="desktop_browser",
            domain="https://www.showclix.com",
            Accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            Accept_Language="en-US,en;q=0.9",
            Cache_Control="no-cache",
            Pragma="no-cache",
            Priority="u=0, i",
            Sec_Ch_Ua='"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            Sec_Ch_Ua_Mobile="?0",
            Sec_Ch_Ua_Platform='"macOS"',
            Sec_Fetch_Dest="document",
            Sec_Fetch_Mode="navigate",
            Sec_Fetch_Site="none",
            Sec_Fetch_User="?1",
            Upgrade_Insecure_Requests="1",
        )

    async def get_web_page_for_event(self, event_slug: str) -> Optional[str]:
        """
        Fetch the HTML content for a Showclix event page.

        Args:
            event_slug: The event slug/identifier from GothamEvent (e.g., "mixtape-comedy229eoyj9")

        Returns:
            HTML content as string, or None if fetch failed
        """
        if not event_slug:
            self.log_warning("Event slug is empty or None")
            return None

        # Construct the Showclix event URL
        event_url = f"https://www.showclix.com/event/{event_slug}"

        try:
            self.log_info(f"Fetching Showclix event page: {event_url}")

            # Use the base class fetch_html method with proper error handling
            html_content = await self.fetch_html(
                url=event_url,
                headers=self.headers,
                timeout=30,
                logger_context={"event_slug": event_slug, "service": "showclix"},
            )

            if html_content:
                self.log_info(f"Successfully fetched {len(html_content)} characters from {event_url}")
                return html_content
            else:
                self.log_warning(f"Failed to fetch content from {event_url}")
                return None

        except Exception as e:
            self.log_error(f"Error fetching Showclix event page {event_url}: {e}")
            return None

    async def get_web_page_for_event_url(self, event_url: str) -> Optional[str]:
        """
        Fetch the HTML content for a complete Showclix event URL.

        Args:
            event_url: The complete Showclix event URL (e.g., "https://www.showclix.com/event/mixtape-comedy229eoyj9")

        Returns:
            HTML content as string, or None if fetch failed
        """
        if not event_url:
            self.log_warning("Event URL is empty or None")
            return None

        try:
            self.log_info(f"Fetching Showclix event page: {event_url}")

            # Use the base class fetch_html method with proper error handling
            html_content = await self.fetch_html(
                url=event_url,
                headers=self.headers,
                timeout=30,
                logger_context={"event_url": event_url, "service": "showclix"},
            )

            if html_content:
                self.log_info(f"Successfully fetched {len(html_content)} characters from {event_url}")
                return html_content
            else:
                self.log_warning(f"Failed to fetch content from {event_url}")
                return None

        except Exception as e:
            self.log_error(f"Error fetching Showclix event page {event_url}: {e}")
            return None

    async def get_event_data(self, event_id: str) -> Optional[ShowclixEventData]:
        """
        Fetch event data from Showclix API for seating and ticketing information.

        Args:
            event_id: The Showclix event ID (e.g., "10071730")

        Returns:
            ShowclixEventData instance with structured event details, or None if fetch failed
        """
        if not event_id:
            self.log_warning("Event ID is empty or None")
            return None

        # Construct the Showclix API URL with all required methods and follows
        api_url = (
            f"https://www.showclix.com/api/events/seated/{event_id}"
            "?methods%5B%5D=tickets_available"
            "&methods%5B%5D=date_title"
            "&methods%5B%5D=total_by_level"
            "&methods%5B%5D=all_levels"
            "&methods%5B%5D=bos_levels"
            "&methods%5B%5D=display_ages"
            "&methods%5B%5D=getNotes"
            "&methods%5B%5D=remaining_by_level"
            "&methods%5B%5D=held_by_level"
            "&methods%5B%5D=purchase_limit"
            "&methods%5B%5D=locale"
            "&methods%5B%5D=getGAHoldsByCategory"
            "&methods%5B%5D=getGAHoldsByCategoryExcludeThirdParty"
            "&methods%5B%5D=seatsio_category_keys"
            "&methods%5B%5D=seatingChartPublicKey"
            "&methods%5B%5D=scsBoxOfficeData"
            "&methods%5B%5D=chartService"
            "&methods%5B%5D=seatsIoHoldColors"
            "&methods%5B%5D=seatedPriceLevelFees"
            "&methods%5B%5D=decimals"
            "&methods%5B%5D=allowOrphanSeats"
            "&methods%5B%5D=orphanSeatMessage"
            "&methods%5B%5D=getDefaultName"
            "&methods%5B%5D=seatedLevels"
            "&methods%5B%5D=seatsioChartUsesLabels"
            "&methods%5B%5D=restTimeslotBuyouts"
            "&methods%5B%5D=hasActiveTimeslotBuyout"
            "&methods%5B%5D=disclose_fee"
            "&follow%5B%5D=sections"
            "&follow%5B%5D=venue"
            "&follow%5B%5D=section_price_levels"
            "&follow%5B%5D=bundles"
            "&follow%5B%5D=products"
            "&follow%5B%5D=event_sections"
            "&cache=1"
        )

        try:
            self.log_info(f"Fetching Showclix event data: {api_url}")

            # Create API-specific headers for this request
            api_headers = BaseHeaders.get_headers(
                base_type="json",
                domain="https://www.showclix.com",
                referer="https://www.showclix.com/event/mixtape-comedy229eoyj9/pyos",
                Accept="application/json, text/javascript, */*; q=0.01",
                Accept_Language="en-US,en;q=0.9",
                Cache_Control="no-cache",
                Content_Type="text/javascript",
                Pragma="no-cache",
                Priority="u=1, i",
                Sec_Ch_Ua='"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
                Sec_Ch_Ua_Mobile="?0",
                Sec_Ch_Ua_Platform='"macOS"',
                Sec_Fetch_Dest="empty",
                Sec_Fetch_Mode="cors",
                Sec_Fetch_Site="same-origin",
                X_Requested_With="XMLHttpRequest",
            )

            # Use the base class fetch_json method with proper error handling
            json_data = await self.fetch_json(
                url=api_url,
                headers=api_headers,
                timeout=30,
                logger_context={"event_id": event_id, "service": "showclix_api"},
            )

            if json_data:
                self.log_info(f"Successfully fetched event data for event {event_id}")
                # Convert JSON response to structured dataclass
                try:
                    event_data = ShowclixEventData.from_dict(json_data)
                    return event_data
                except Exception as parse_error:
                    self.log_error(f"Failed to parse Showclix event data for {event_id}: {parse_error}")
                    return None
            else:
                self.log_warning(f"Failed to fetch event data for event {event_id}")
                return None

        except Exception as e:
            self.log_error(f"Error fetching Showclix event data for {event_id}: {e}")
            return None
