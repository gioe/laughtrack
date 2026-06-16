"""Generic scraper for venues whose listings are hosted by VBO Tickets.

VBO Tickets (vbotickets.com) embeds a per-venue plugin in the venue's own site
via ``connect.vbotickets.com/_assets/js/plugin.js`` keyed by a ``SiteID`` GUID.
This scraper reproduces the plugin's multi-event ``ListEvents`` flow:

  1. GET ``plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>&page=ListEvents``
     → returns a short HTML doc that posts a per-visit user-session UUID.
  2. GET ``plugin.vbotickets.com/Plugin/events/showevents?ViewType=list``
     ``&EventType=current&day=&s=<session>`` → the rendered list of upcoming
     events (name, date, price, eid).

Any VBO-hosted venue can be onboarded by pointing its
``scraping_sources.source_url`` at the step-1 loadplugin URL (with the venue's
SiteID) — no per-venue code required. This differs from the venue-specific VBO
scrapers (esthers_follies / nest_theatre / csz_philadelphia), which model a
single recurring show via the per-event date slider; this scraper reads the
multi-event listing instead.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import VboTicketsPageData
from .extractor import VboTicketsExtractor
from .transformer import VboTicketsTransformer

_SHOWEVENTS_URL = (
    "https://plugin.vbotickets.com/Plugin/events/showevents"
    "?ViewType=list&EventType=current&day=&s={session}"
)


class VboTicketsScraper(BaseScraper):
    """Scraper for venues using the VBO Tickets ListEvents listing."""

    key = "vbo_tickets"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(VboTicketsTransformer(club))

    async def get_data(self, url: str) -> Optional[VboTicketsPageData]:
        """
        Acquire a VBO session from the loadplugin URL, then fetch + parse the
        current-events listing.

        Args:
            url: The venue's loadplugin URL (from scraping_sources.source_url),
                 e.g. ``.../plugin/loadplugin?siteid=<GUID>&page=ListEvents``.

        Returns:
            VboTicketsPageData containing the upcoming events, or None.
        """
        # Step 1: acquire the per-visit session UUID from the loadplugin endpoint.
        try:
            loadplugin_html = await self.fetch_html(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch VBO loadplugin: {e}", self.logger_context)
            return None

        session = VboTicketsExtractor.extract_session(loadplugin_html or "")
        if not session:
            Logger.warn(
                f"{self._log_prefix}: could not extract VBO session from loadplugin response",
                self.logger_context,
            )
            return None

        Logger.debug(f"{self._log_prefix}: acquired VBO session {session[:8]}...", self.logger_context)

        # Step 2: fetch the current-events listing using the session.
        try:
            listing_html = await self.fetch_html(_SHOWEVENTS_URL.format(session=session))
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed to fetch VBO showevents listing: {e}", self.logger_context)
            return None

        events = VboTicketsExtractor.extract_events(listing_html or "")
        if not events:
            self._warn_empty_extraction(url, html=listing_html)
            return None

        Logger.info(f"{self._log_prefix}: extracted {len(events)} events from VBO listing", self.logger_context)
        return VboTicketsPageData(event_list=events)
