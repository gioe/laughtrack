"""
Nick's Comedy Stop scraper.

Nick's Comedy Stop (100 Warrenton St, Boston, MA) uses Wix Events for native
ticketing.  All upcoming shows are available via Wix's paginated-events API
using the events widget compId found on the homepage.

Pipeline:
  1. collect_scraping_targets() → authenticate with Wix, return API URL
  2. get_data(url)              → fetch events JSON, extract NicksEvents
  3. transformation_pipeline    → NicksEvent.to_show() → Show objects
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import NicksPageData
from .extractor import NicksEventExtractor
from .transformer import NicksEventTransformer

# Wix Events widget component ID for the events list on the Nick's homepage.
_COMP_ID = "comp-m4t1prev"

# Wix client-binding GUID used for session authentication (same across Wix sites).
_CLIENT_BINDING = "e2814456-fed7-4d1b-a36c-ded753a23ca3"


class NicksComedyStopScraper(BaseScraper):
    """Scraper for Nick's Comedy Stop (Boston, MA) via Wix Events API."""

    key = "nicks_comedy_stop"
    _MAX_PAGES = 20

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(NicksEventTransformer(club))
        self.domain = URLUtils.get_base_domain_with_protocol(
            URLUtils.normalize_url(club.scraping_url)
        )
        self._access_token: Optional[str] = None

    async def collect_scraping_targets(self) -> List[str]:
        """Authenticate with Wix and return the paginated-events API URL."""
        try:
            await self._ensure_authenticated()
            if not self._access_token:
                return []

            api_url = f"{self.domain}/_api/wix-one-events-server/web/paginated-events/viewer"
            params = {
                "filter": "1",
                "byEventId": "false",
                "members": "true",
                "paidPlans": "false",
                "locale": "en-us",
                "recurringFilter": "2",
                "filterType": "2",
                "sortOrder": "0",
                "limit": "50",
                "draft": "false",
                "fetchBadges": "false",
                "compId": _COMP_ID,
                "offset": "0",
            }
            query = "&".join(f"{k}={v}" for k, v in params.items())
            return [f"{api_url}?{query}"]

        except Exception as e:
            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: failed to build target URL: {e}", self.logger_context)
            return []

    async def get_data(self, url: str) -> Optional[NicksPageData]:
        """Fetch all events from the Wix Events API, following hasMore pagination."""
        try:
            headers = self._build_auth_headers()
            all_events = []
            current_url = url

            parsed = urlparse(current_url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            limit = int(params.get("limit", ["50"])[0])

            for page in range(self._MAX_PAGES):
                response = await self.fetch_json(current_url, headers=headers)
                if response is None:
                    break

                all_events.extend(NicksEventExtractor.extract_events(response))

                if not response.get("hasMore", False):
                    break

                parsed = urlparse(current_url)
                params = parse_qs(parsed.query, keep_blank_values=True)
                current_offset = int(params.get("offset", ["0"])[0])
                params["offset"] = [str(current_offset + limit)]
                current_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in params.items()})))
            else:
                Logger.warn(
                    f"{self.__class__.__name__} [{self._club.name}]: reached MAX_PAGES ({self._MAX_PAGES}) — pagination stopped early",
                    self.logger_context,
                )

            if not all_events:
                Logger.warn(f"{self.__class__.__name__} [{self._club.name}]: no events extracted", self.logger_context)
                return None

            Logger.info(f"{self.__class__.__name__} [{self._club.name}]: extracted {len(all_events)} events", self.logger_context)
            return NicksPageData(event_list=all_events)

        except Exception as e:
            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: error fetching events: {e}", self.logger_context)
            return None

    async def _ensure_authenticated(self) -> None:
        """Fetch a short-lived Wix access token if not already obtained."""
        if self._access_token:
            return

        token_url = f"{self.domain}/_api/v1/access-tokens"
        token_headers = {
            **BaseHeaders.get_headers(base_type="mobile_browser", domain=self.domain),
            "client-binding": _CLIENT_BINDING,
            "Cookie": f"server-session-bind={_CLIENT_BINDING}",
        }

        try:
            data = await self.fetch_json(token_url, headers=token_headers)
            if not data:
                Logger.error(f"{self.__class__.__name__} [{self._club.name}]: no data from access-tokens endpoint", self.logger_context)
                return

            apps = data.get("apps", {})
            for app_data in apps.values():
                if app_data.get("intId") == 24:
                    self._access_token = app_data.get("instance")
                    Logger.info(f"{self.__class__.__name__} [{self._club.name}]: access token obtained", self.logger_context)
                    return

            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: app intId=24 not found in access-tokens response", self.logger_context)

        except Exception as e:
            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: failed to fetch access token: {e}", self.logger_context)

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build Wix API request headers with the bearer token."""
        headers = BaseHeaders.get_headers(base_type="wix_api", domain=self.domain)
        if self._access_token:
            headers["authorization"] = self._access_token
        return headers
