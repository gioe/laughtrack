"""
Generic Wix Events platform scraper.

Serves all venues that use Wix Events for native ticketing. Per-venue config
(compId, optional categoryId) is read from the Club model.

Venues served:
- Bushwick Comedy Club (comp-lzt5zlma, categoryId=41b1dace-...)
- Nick's Comedy Stop (comp-m4t1prev)
- RED ROOM Comedy Club (comp-j9ny0yyr)
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import WixEventsPageData
from .extractor import WixEventsExtractor
from .transformer import WixEventsEventTransformer

# Wix client-binding GUID used for session authentication (same across all Wix sites).
_CLIENT_BINDING = "e2814456-fed7-4d1b-a36c-ded753a23ca3"


class WixEventsScraper(BaseScraper):
    """
    Generic scraper for venues using Wix Events for ticketing.

    Reads wix_comp_id (required) and wix_category_id (optional) from the Club model.
    The club's scraping_url should be the venue's Wix website root (e.g., https://www.bushwickcomedy.com).
    """

    key = "wix_events"
    _MAX_PAGES = 20

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(WixEventsEventTransformer(club))
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
                "offset": "0",
            }
            # compId is required for widget-based venues but optional for
            # schedule-page venues where the API returns all events without it.
            if self.club.wix_comp_id:
                params["compId"] = self.club.wix_comp_id
            # Add optional categoryId
            if self.club.wix_category_id:
                params["categoryId"] = self.club.wix_category_id

            query = "&".join(f"{k}={v}" for k, v in params.items())
            return [f"{api_url}?{query}"]

        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to build target URL: {e}", self.logger_context)
            return []

    async def get_data(self, url: str) -> Optional[WixEventsPageData]:
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

                all_events.extend(WixEventsExtractor.extract_events(response))

                if not response.get("hasMore", False):
                    break

                parsed = urlparse(current_url)
                params = parse_qs(parsed.query, keep_blank_values=True)
                current_offset = int(params.get("offset", ["0"])[0])
                params["offset"] = [str(current_offset + limit)]
                current_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in params.items()})))
            else:
                Logger.warn(
                    f"{self._log_prefix}: reached MAX_PAGES ({self._MAX_PAGES}) — pagination stopped early",
                    self.logger_context,
                )

            if not all_events:
                Logger.warn(f"{self._log_prefix}: no events extracted", self.logger_context)
                return None

            Logger.info(f"{self._log_prefix}: extracted {len(all_events)} events", self.logger_context)
            return WixEventsPageData(event_list=all_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: error fetching events: {e}", self.logger_context)
            return None

    async def _ensure_authenticated(self) -> None:
        """Fetch a short-lived Wix access token (intId=24) if not already obtained."""
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
                Logger.error(f"{self._log_prefix}: no data from access-tokens endpoint", self.logger_context)
                return

            apps = data.get("apps", {})
            for app_data in apps.values():
                if app_data.get("intId") == 24:
                    self._access_token = app_data.get("instance")
                    Logger.info(f"{self._log_prefix}: access token obtained", self.logger_context)
                    return

            Logger.error(f"{self._log_prefix}: app intId=24 not found in access-tokens response", self.logger_context)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch access token: {e}", self.logger_context)

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build Wix API request headers with the bearer token."""
        headers = BaseHeaders.get_headers(base_type="wix_api", domain=self.domain)
        if self._access_token:
            headers["authorization"] = self._access_token
        return headers
