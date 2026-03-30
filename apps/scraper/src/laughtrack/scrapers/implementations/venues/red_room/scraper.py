"""
RED ROOM Comedy Club scraper — Wix native events.

RED ROOM Comedy Club (7442 N. Western Ave, Chicago, IL) uses Wix's built-in
events calendar widget. Event data is served by the Wix paginated-events API:
  GET /_api/wix-one-events-server/web/paginated-events/viewer?compId=comp-j9ny0yyr&...

compId comp-j9ny0yyr was discovered via Playwright DOM traversal from the
EVENTS_ROOT_NODE element. No categoryId is required — the venue has no Wix
event categories configured.
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from laughtrack.core.clients.wix.response_models.wix_access_token_response import WixAccessTokenResponse
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.venues.bushwick.models.factory import WixResponseFactory

from .data import RedRoomPageData
from .extractor import RedRoomEventExtractor
from .transformer import RedRoomEventTransformer


class RedRoomComedyClubScraper(BaseScraper):
    """
    RED ROOM Comedy Club scraper — Wix native events.

    Authenticates via the Wix access-token endpoint (intId=24), then fetches
    events from the paginated-events viewer API using compId=comp-j9ny0yyr.
    """

    key = "red_room"

    _COMP_ID = "comp-j9ny0yyr"

    def __init__(self, club: Club, **kwargs):
        raw_url = club.scraping_url
        domain = URLUtils.get_base_domain_with_protocol(raw_url)
        if not domain or not domain.startswith("http"):
            raise ValueError("RedRoom: scraping_url is missing or produced an invalid domain")
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(RedRoomEventTransformer(club))
        self.domain = domain
        self.access_token = None

    async def collect_scraping_targets(self) -> List[str]:
        """Return the Wix paginated-events API URL after authenticating."""
        try:
            await self._ensure_authenticated()
            if not self.access_token:
                return []

            api_url = f"{self.domain}/_api/wix-one-events-server/web/paginated-events/viewer"
            params = {
                "filter": 1,
                "byEventId": "false",
                "members": "true",
                "paidPlans": "false",
                "locale": "en-us",
                "recurringFilter": 2,
                "filterType": 2,
                "sortOrder": 0,
                "fetchBadges": "false",
                "draft": "false",
                "compId": self._COMP_ID,
                "limit": 50,
                "offset": 0,
            }
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            return [f"{api_url}?{query_string}"]

        except Exception as e:
            Logger.error(
                f"RedRoomComedyClubScraper: failed to build API URL: {e}",
                self.logger_context,
            )
            return []

    _MAX_PAGES = 20

    async def get_data(self, url: str) -> Optional[RedRoomPageData]:
        """Fetch all events from the Wix paginated-events API, following hasMore pagination."""
        try:
            headers = self._build_auth_headers()
            all_events = []
            current_url = url

            parsed = urlparse(current_url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            limit = int(params.get("limit", ["50"])[0])

            for page in range(self._MAX_PAGES):
                api_response = await self.fetch_json(current_url, headers=headers)
                if api_response is None:
                    break

                typed_response = WixResponseFactory.create_wix_events_response(api_response)
                all_events.extend(RedRoomEventExtractor.extract_events(typed_response))

                if not typed_response.hasMore:
                    break

                parsed = urlparse(current_url)
                params = parse_qs(parsed.query, keep_blank_values=True)
                current_offset = int(params.get("offset", ["0"])[0])
                params["offset"] = [str(current_offset + limit)]
                current_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in params.items()})))
            else:
                Logger.warn(
                    f"RedRoomComedyClubScraper: reached MAX_PAGES ({self._MAX_PAGES}) — pagination stopped early",
                    self.logger_context,
                )

            return RedRoomPageData(event_list=all_events) if all_events else None

        except Exception as e:
            Logger.error(
                f"RedRoomComedyClubScraper: error fetching {url}: {e}",
                self.logger_context,
            )
            return None

    async def _ensure_authenticated(self) -> None:
        """Obtain a Wix access token (intId=24) if not already cached."""
        if self.access_token:
            return

        token_url = f"{self.domain}/_api/v1/access-tokens"
        token_headers = {
            **BaseHeaders.get_headers(base_type="mobile_browser", domain=self.domain),
            "client-binding": "e2814456-fed7-4d1b-a36c-ded753a23ca3",
            "Cookie": "server-session-bind=e2814456-fed7-4d1b-a36c-ded753a23ca3",
        }
        try:
            data = await self.fetch_json(token_url, headers=token_headers)
            token_response = WixAccessTokenResponse.from_dict(data)
            access_token = token_response.get_access_token_for_app(24)
            if access_token:
                self.access_token = access_token
                Logger.info(
                    "RedRoomComedyClubScraper: access token obtained",
                    self.logger_context,
                )
                return
            Logger.error(
                "RedRoomComedyClubScraper: intId=24 app not found in token response",
                self.logger_context,
            )
        except Exception as e:
            Logger.error(
                f"RedRoomComedyClubScraper: error fetching access token: {e}",
                self.logger_context,
            )

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build Wix API headers with the cached authorization token."""
        headers = BaseHeaders.get_headers(base_type="wix_api", domain=self.domain)
        if self.access_token:
            headers["authorization"] = self.access_token
        return headers
