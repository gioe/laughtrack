"""
Esther's Follies scraper implementation.

Esther's Follies (525 E. 6th St, Austin TX) is an Austin comedy institution
since 1977, staging sketch comedy, political satire, and award-winning magic
Thursday–Saturday nights. Tickets are sold via VBO Tickets (vbotickets.com).

VBO Tickets uses a session-based plugin system embedded in the venue website.
There is no unauthenticated public JSON API for event listings. The flow:

  1. GET https://plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>
       → Returns a small HTML page that embeds the session UUID in JavaScript.

  2. GET https://plugin.vbotickets.com/v5.0/controls/events.asp
       ?a=load_eventdate_slider&page=seatmap.asp&eid=<EID>&edid=0&req=1&s=<SESSION>
       → Returns a server-rendered HTML fragment listing upcoming show dates and
         times as "SelectorBox" divs (~6 week window).

Ticket URL is the stable venue tickets page (https://www.esthersfollies.com/tickets)
since per-show VBO URLs are session-dependent and non-shareable.

Pipeline:
  1. collect_scraping_targets() → [_VBO_LOADPLUGIN_URL]  (dummy target for base compat)
  2. get_data(url)              → acquires session, fetches date slider HTML,
                                  returns EsthersFolliesPageData
  3. transformation_pipeline   → EsthersFolliesEvent.to_show() → Show objects
"""

import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import EsthersFolliesPageData
from .extractor import EsthersFolliesEventExtractor
from .transformer import EsthersFolliesEventTransformer

# VBO Tickets configuration for Esther's Follies
_SITE_ID = "5D695E7C-1246-4F54-BF57-B1D92D1E6B83"
_EID = "39242"

_VBO_LOADPLUGIN_URL = (
    f"https://plugin.vbotickets.com/plugin/loadplugin"
    f"?siteid={_SITE_ID}&page=ListEvents"
)
_VBO_DATE_SLIDER_URL = (
    "https://plugin.vbotickets.com/v5.0/controls/events.asp"
    "?a=load_eventdate_slider&page=seatmap.asp"
    f"&eid={_EID}&edid=0&req=1&s={{session}}"
)

# Regex to extract the UUID session from the VBO loadplugin JS response.
# VBO embeds the session as an unquoted JS object key: `value: "uuid"`.
_SESSION_RE = re.compile(
    r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.IGNORECASE,
)


class EsthersFolliesScraper(BaseScraper):
    """Scraper for Esther's Follies (Austin, TX) via VBO Tickets."""

    key = "esthers_follies"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            EsthersFolliesEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[EsthersFolliesPageData]:
        """
        Acquire a VBO session and fetch the date slider listing upcoming shows.

        Args:
            url: Unused — kept for BaseScraper interface compatibility.
                 The scraper always hits VBO Tickets endpoints directly.

        Returns:
            EsthersFolliesPageData containing upcoming show slots, or None.
        """
        # Step 1: acquire a session UUID from the VBO loadplugin endpoint
        try:
            loadplugin_html = await self.fetch_html(_VBO_LOADPLUGIN_URL)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: failed to fetch VBO loadplugin: {e}",
                self.logger_context,
            )
            return None

        if not loadplugin_html:
            Logger.warn(
                f"{self._log_prefix}: empty response from VBO loadplugin",
                self.logger_context,
            )
            return None

        m = _SESSION_RE.search(loadplugin_html)
        if not m:
            Logger.warn(
                f"{self._log_prefix}: could not extract session UUID from loadplugin response",
                self.logger_context,
            )
            return None

        session = m.group(1)
        Logger.debug(
            f"{self._log_prefix}: acquired VBO session {session[:8]}...",
            self.logger_context,
        )

        # Step 2: fetch the date slider HTML using the session
        slider_url = _VBO_DATE_SLIDER_URL.format(session=session)
        try:
            slider_html = await self.fetch_html(slider_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: failed to fetch VBO date slider: {e}",
                self.logger_context,
            )
            return None

        if not slider_html:
            Logger.warn(
                f"{self._log_prefix}: empty date slider response from VBO",
                self.logger_context,
            )
            return None

        # Step 3: parse show slots from the date slider HTML
        events = EsthersFolliesEventExtractor.extract_shows(
            slider_html, self.logger_context
        )

        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming show slots found",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {len(events)} upcoming show slots",
            self.logger_context,
        )
        return EsthersFolliesPageData(event_list=events)
