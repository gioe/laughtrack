"""
Comedy Cellar Service

Handles all Comedy Cellar-specific API interactions and data fetching.
This service encapsulates the network requests and API logic for Comedy Cellar,
allowing the scraper to focus on orchestration and data flow.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.models.api.comedy_cellar.models import (
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
)
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.scrapers.implementations.venues.comedy_cellar.extractor import ComedyCellarExtractor
from laughtrack.core.clients.base import BaseApiClient



class ComedyCellarAPIClient(BaseApiClient):
    """
    Service class for Comedy Cellar API interactions.

    This class handles all the Comedy Cellar-specific network requests,
    headers, and API configurations. It uses the HttpConvenienceMixin
    to get standard HTTP methods with error handling and retries.
    """

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        super().__init__(club, proxy_pool=proxy_pool)

        # API endpoints
        self.lineup_api_url = "https://www.comedycellar.com/lineup/api/"
        self.ticket_api_url = "https://www.comedycellar.com/reservations/api/getShows"

        # Setup headers and payload templates
        self._setup_headers()
        self.lineup_payload_template = 'action=cc_get_shows&json={{"date":"{}","venue":"newyork","type":"lineup"}}'

    def _setup_headers(self) -> None:
        # Lineup request configuration
        self.lineup_headers = BaseHeaders.get_headers(
            base_type="comedy_cellar_lineup",
            domain="https://www.comedycellar.com",
            referer="https://www.comedycellar.com/new-york-line-up/",
            cookies=(
                "_ga=GA1.2.1634276111.1750210095; _gid=GA1.2.2124858909.1750210095; "
                "_gat_gtag_UA_66066650_1=1; _ga_2EBVDX89EN=GS2.1.s1750210094$o1$g0$t1750210129$j25$l0$h0; "
                "AWSALB=2kJNlEzybtjaucn+1MymdVfcM4QsIWZLdRUQ+0ozLrQ4Zu2Ct5Y7AirKah/R/hOs8OXuF+gmuVm33HXbUfby8iaLJnRaf/abUrsGPUBOsIwYVuV/xf0tv19XQt94; "
                "AWSALBCORS=2kJNlEzybtjaucn+1MymdVfcM4QsIWZLdRUQ+0ozLrQ4Zu2Ct5Y7AirKah/R/hOs8OXuF+gmuVm33HXbUfby8iaLJnRaf/abUrsGPUBOsIwYVuV/xf0tv19XQt94; "
                "AWSALB=GQMreGWX00nMIzKWDc1QTYgROruqbLndq2prlTzkEigWZu7dRKjEpR5gBJ53Nddn7yXfItfbN5dfImG6TxnOKzN+IgruwF8Mv4EzDu8kyZIJ+kGnJ8bCkCjFlupz; "
                "AWSALBCORS=GQMreGWX00nMIzKWDc1QTYgROruqbLndq2prlTzkEigWZu7dRKjEpR5gBJ53Nddn7yXfItfbN5dfImG6TxnOKzN+IgruwF8Mv4EzDu8kyZIJ+kGnJ8bCkCjFlupz"
            ),
        )

        # Shows API request configuration
        self.shows_headers = BaseHeaders.get_headers(
            base_type="comedy_cellar_shows",
            domain="https://www.comedycellar.com",
            referer="https://www.comedycellar.com/reservations-newyork/",
            cookies=(
                "_gid=GA1.2.2027625403.1750264817; _gat_gtag_UA_66066650_1=1; "
                "_ga_2EBVDX89EN=GS2.1.s1750264816$o1$g1$t1750264938$j50$l0$h0; "
                "_ga=GA1.2.669091607.1750264817; "
                "AWSALB=7ZpaPdgV26KqR9Tjle9+nYo9DQiDww6KQIl+815o2qgkGOhrf4tDy1F2qt1Uv7qMYTPN3BUBrJXIcBzs4QCcMxinViZgDmJw9UDvO6CqmEYtNYzEli/rGNhn6+Ky; "
                "AWSALBCORS=7ZpaPdgV26KqR9Tjle9+nYo9DQiDww6KQIl+815o2qgkGOhrf4tDy1F2qt1Uv7qMYTPN3BUBrJXIcBzs4QCcMxinViZgDmJw9UDvO6CqmEYtNYzEli/rGNhn6+Ky; "
                "AWSALB=1wxUxLgS+RMjtVRX2M6Z+Kejv1H9v5fSAfYuVsOUQgddmCrBRIxt4KqVuGzz4jK9hGOSu7xe0RzU8J6O3B6WZLROh925spdLnxVpeUyVyxzUjeaNnCgaHIpWhcFY; "
                "AWSALBCORS=1wxUxLgS+RMjtVRX2M6Z+Kejv1H9v5fSAfYuVsOUQgddmCrBRIxt4KqVuGzz4jK9hGOSu7xe0RzU8J6O3B6WZLROh925spdLnxVpeUyVyxzUjeaNnCgaHIpWhcFY"
            ),
        )
        # Add headers with hyphenated names after creation
        self.shows_headers["x-code-localize"] = (
            "5e49d74493acf322b0167e9e7b872651df8a589f499047190a418f91bded7849.MTc1MDI2ODU1My0xODUuMTk5LjEwMy4xMzE="
        )
        self.shows_headers["x-page-creation"] = "1750264947"

    async def get_lineup_data(self, date_key: str) -> ComedyCellarLineupAPIResponse:
        """Get lineup HTML data for a specific date.

        Raises:
            ValueError: If the response is empty or invalid.
            Exception: Propagates any extractor/network exceptions for caller to handle.
        """
        payload = self.lineup_payload_template.format(date_key)
        response_text = await self.post_form(self.lineup_api_url, payload, headers=self.lineup_headers)

        if not response_text:
            raise ValueError(f"Empty lineup response for {date_key}")

    # Generic response logging is handled at BaseApiClient level (DEBUG only)

        # Use extractor to extract lineup data from response
        lineup = ComedyCellarExtractor.extract_lineup_data(response_text)
        if lineup is None:
            raise ValueError(f"Invalid lineup data extracted for {date_key}")
        return lineup

    async def get_shows_data(self, date_key: str) -> ComedyCellarShowsAPIResponse:
        """Get show details and tickets for a specific date.

        Raises:
            ValueError: If the response is empty or invalid.
            Exception: Propagates any extractor/network exceptions for caller to handle.
        """
        payload = {"date": date_key}
        response_data = await self.post_json(self.ticket_api_url, payload, headers=self.shows_headers)

        if not response_data or not isinstance(response_data, dict):
            raise ValueError(f"Empty or invalid shows response for {date_key}")

    # Generic response logging is handled at BaseApiClient level (DEBUG only)

        # Use extractor to extract shows data from response
        shows = ComedyCellarExtractor.extract_shows_data(response_data)
        if shows is None:
            raise ValueError(f"Invalid shows data extracted for {date_key}")
        return shows

    async def discover_available_dates(self) -> list[str]:
        """
        Discover available dates to scrape from Comedy Cellar's API.

        Returns:
            List of date strings that can be processed
        """
        try:
            # Make initial request to discover dates
            payload = self.lineup_payload_template.format("today")
            response_text = await self.post_form(self.lineup_api_url, payload, headers=self.lineup_headers)

            # Use extractor to extract dates from response
            if not response_text:
                self.log_warning("Empty response when discovering dates")
                return []

            dates = ComedyCellarExtractor.extract_available_dates(response_text)

            self.log_info(f"Discovered {len(dates)} dates from Comedy Cellar API")
            return dates

        except Exception as e:
            self.log_error(f"Error discovering dates: {e}")
            return []
