"""
The Lost Church scraper implementation.

The Lost Church (988 Columbus Avenue, San Francisco CA) is a nonprofit arts venue
hosting comedy, music, and literary events. Tickets are sold via Salesforce
PatronTicket, a Visualforce Remoting SPA at:

  https://thelostchurch.my.salesforce-sites.com/ticket

The PatronTicket API requires per-method authorization tokens extracted from the
page HTML at load time. The scraper:

  1. Fetches the ticket page HTML to extract the fetchEvents auth config
     (CSRF token, JWT authorization, namespace, version, VID).
  2. POSTs to the apexremote endpoint with the correct auth context.
  3. Filters the response to Comedy-category events at the SF venue.

Pipeline:
  1. collect_scraping_targets() → [ticket_page_url]
  2. get_data(url)              → fetches page, extracts auth, calls API,
                                  returns LostChurchPageData
  3. transformation_pipeline   → LostChurchEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import LostChurchPageData
from .extractor import LostChurchEventExtractor
from .transformer import LostChurchEventTransformer

_TICKET_PAGE_URL = "https://thelostchurch.my.salesforce-sites.com/ticket"
_APEXREMOTE_URL = f"{_TICKET_PAGE_URL}/apexremote"


class LostChurchScraper(BaseScraper):
    """Scraper for The Lost Church (San Francisco, CA) via Salesforce PatronTicket."""

    key = "lost_church"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            LostChurchEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[LostChurchPageData]:
        """Fetch the PatronTicket page, extract auth config, and call fetchEvents.

        Args:
            url: The ticket page URL (used to load auth config).

        Returns:
            LostChurchPageData containing upcoming comedy events, or None.
        """
        # Step 1: fetch the ticket page HTML to extract auth config
        try:
            page_html = await self.fetch_html(_TICKET_PAGE_URL)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: failed to fetch PatronTicket page: {e}",
                self.logger_context,
            )
            return None

        if not page_html:
            Logger.warn(
                f"{self._log_prefix}: empty response from PatronTicket page",
                self.logger_context,
            )
            return None

        auth_config = LostChurchEventExtractor.extract_auth_config(page_html)
        if not auth_config:
            Logger.warn(
                f"{self._log_prefix}: could not extract fetchEvents auth config from page",
                self.logger_context,
            )
            return None

        # Step 2: call fetchEvents via Visualforce Remoting
        payload = {
            "action": "PatronTicket.Controller_PublicTicketApp",
            "method": "fetchEvents",
            "data": [f"{_TICKET_PAGE_URL}/", "", ""],
            "type": "rpc",
            "tid": 5,
            "ctx": {
                "csrf": auth_config["csrf"],
                "vid": auth_config["vid"],
                "ns": auth_config["ns"],
                "ver": auth_config["ver"],
                "authorization": auth_config["authorization"],
            },
        }

        try:
            api_response = await self.post_json(
                _APEXREMOTE_URL,
                payload,
                headers={"Referer": _TICKET_PAGE_URL},
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: fetchEvents API call failed: {e}",
                self.logger_context,
            )
            return None

        if not api_response:
            Logger.warn(
                f"{self._log_prefix}: empty response from fetchEvents API",
                self.logger_context,
            )
            return None

        # Step 3: extract comedy events at the SF venue
        events = LostChurchEventExtractor.extract_events(
            api_response, self.logger_context
        )

        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming comedy events found",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {len(events)} upcoming comedy events",
            self.logger_context,
        )
        return LostChurchPageData(event_list=events)
