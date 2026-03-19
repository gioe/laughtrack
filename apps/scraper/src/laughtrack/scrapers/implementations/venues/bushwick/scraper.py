"""
Bushwick Comedy Club scraper implementation using standardized project patterns.

This implementation leverages the project's architectural abstractions:
- BaseScraper pipeline for standard workflow
- Built-in fetch methods with error handling and retries
- Standardized error handling and logging
- Proper session management and cleanup

Clean single-responsibility architecture:
- BushwickEventExtractor: Wix API response → BushwickEvent objects
- BushwickEventTransformer: BushwickEvent objects → Show objects
- BushwickComedyClubScraper: Orchestrates extraction and transformation
"""

from typing import Dict, List, Optional

from laughtrack.core.clients.wix.response_models.wix_access_token_response import WixAccessTokenResponse
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.venues.bushwick.models.factory import WixResponseFactory
from laughtrack.foundation.utilities.url import URLUtils

from .data import BushwickEventData
from .extractor import BushwickEventExtractor
from .transformer import BushwickEventTransformer


class BushwickComedyClubScraper(BaseScraper):
    """
    Bushwick Comedy Club scraper using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (discover_urls → extract_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Follows established error handling and logging patterns
    4. Separates concerns: extraction vs transformation
    """

    key = "bushwick"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(BushwickEventTransformer(club))
        self.domain = URLUtils.get_base_domain_with_protocol(club.scraping_url)
        self.access_token = None

    async def collect_scraping_targets(self) -> List[str]:
        """Discover Wix API URLs for event data."""
        try:
            await self._ensure_authenticated()
            if not self.access_token:
                return []

            # Build Wix API URL with parameters
            api_url = f"{self.domain}/_api/wix-one-events-server/web/paginated-events/viewer"
            params = {
                "filter": 1,
                "byEventId": "false",
                "members": "true",
                "paidPlans": "false",
                "locale": "en-us",
                "categoryId": "41b1dace-b9ba-49dd-a961-f48839c0fce0",
                "recurringFilter": 2,
                "filterType": 2,
                "sortOrder": 0,
                "fetchBadges": "false",
                "draft": "false",
                "compId": "comp-lzt5zlma",
                "limit": 50,
                "offset": 0,
            }

            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            return [f"{api_url}?{query_string}"]

        except Exception as e:
            Logger.error(f"Failed to discover URLs: {e}", self.logger_context)
            return []

    async def get_data(self, url: str) -> Optional[BushwickEventData]:
        """Extract Bushwick event data from Wix API using standardized fetch methods."""
        try:
            headers = self._build_auth_headers()
            api_response = await self.fetch_json(url, headers=headers)

            if not api_response:
                return None

            typed_response = WixResponseFactory.create_wix_events_response(api_response)
            event_list = BushwickEventExtractor.extract_events(typed_response)
            return BushwickEventData(event_list) if event_list else None

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if self.access_token:
            return

        token_url = f"{self.domain}/_api/v1/access-tokens"
        token_headers = {
            **BaseHeaders.get_headers(base_type="mobile_browser", domain=self.domain),
            "client-binding": "e2814456-fed7-4d1b-a36c-ded753a23ca3",
            "Cookie": "server-session-bind=e2814456-fed7-4d1b-a36c-ded753a23ca3",
        }

        try:
            # Use BaseScraper's fetch_json method with error handling and retries
            data = await self.fetch_json(token_url, headers=token_headers)
            token_response = WixAccessTokenResponse.from_dict(data)

            # Look for app with intId 24 and get its instance token
            access_token = token_response.get_access_token_for_app(24)
            if access_token:
                self.access_token = access_token
                Logger.info("Successfully obtained access token", self.logger_context)
                return

            Logger.error("Failed to get access token", self.logger_context)
        except Exception as e:
            Logger.error(f"Error fetching access token: {e}", self.logger_context)

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build headers with authorization token using BaseHeaders."""
        headers = BaseHeaders.get_headers(base_type="wix_api", domain=self.domain)

        # Add Wix-specific authorization token
        if self.access_token:
            headers["authorization"] = self.access_token

        return headers
