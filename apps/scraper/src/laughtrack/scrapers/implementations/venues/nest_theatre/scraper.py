"""
The Nest Theatre scraper (Columbus, OH) via VBO Tickets.

The Nest Theatre (2643 N High St) is a Columbus improv + stand-up comedy
theatre that sells tickets through VBO Tickets (vbotickets.com), embedded as a
plugin iframe on https://nesttheatre.com/shows/. Unlike Esther's Follies (the
other VBO venue, a single recurring show scraped via the date slider), The Nest
runs many distinct shows, so this scraper reads the multi-event "showevents"
grid.

VBO uses a session-based plugin flow:

  1. GET https://plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>&page=ListEvents
       → small HTML page embedding a session UUID in JavaScript.
  2. GET https://plugin.vbotickets.com/Plugin/events/showevents
       ?ViewType=grid&EventType=current&day=&s=<SESSION>
       → server-rendered grid of upcoming events (shows + classes).

The extractor keeps only data-event-category="Live Shows" entries (classes,
camps and workshops are excluded) and expands recurring listings into one show
per upcoming date. Per-show VBO URLs are session-scoped and non-shareable, so
show_page_url is the stable venue shows page.

Pipeline:
  1. collect_scraping_targets() → [loadplugin URL]  (fixed; site self-contained)
  2. get_data(url)              → acquire session, fetch the showevents grid,
                                  return NestTheatrePageData
  3. transformation_pipeline   → NestTheatreEvent.to_show() → Show objects
"""

import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import NestTheatrePageData
from .extractor import NestTheatreEventExtractor
from .transformer import NestTheatreEventTransformer

# VBO Tickets site id for The Nest Theatre.
_SITE_ID = "5D584EB6-2A49-4AFD-9430-259D26127F0B"

_VBO_LOADPLUGIN_URL = (
    f"https://plugin.vbotickets.com/plugin/loadplugin?siteid={_SITE_ID}&page=ListEvents"
)
_VBO_SHOWEVENTS_URL = (
    "https://plugin.vbotickets.com/Plugin/events/showevents"
    "?ViewType=grid&EventType=current&day=&s={session}"
)

# VBO embeds the session as a JS object value: `value: "<uuid>"`.
_SESSION_RE = re.compile(
    r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.IGNORECASE,
)


class NestTheatreScraper(BaseScraper):
    """Scraper for The Nest Theatre (Columbus, OH) via the VBO showevents grid."""

    key = "nest_theatre"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            NestTheatreEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the fixed VBO loadplugin URL (the site is self-contained)."""
        return [_VBO_LOADPLUGIN_URL]

    async def get_data(self, url: str) -> Optional[NestTheatrePageData]:
        """Acquire a VBO session and fetch the upcoming-events grid.

        Args:
            url: The loadplugin URL from collect_scraping_targets().

        Returns:
            NestTheatrePageData with upcoming shows, or None when the session
            cannot be acquired or no Live Shows are listed.
        """
        loadplugin_html = await self.fetch_html(url)
        if not loadplugin_html:
            Logger.warn(
                f"{self._log_prefix}: empty response from VBO loadplugin",
                self.logger_context,
            )
            return None

        m = _SESSION_RE.search(loadplugin_html)
        if not m:
            Logger.warn(
                f"{self._log_prefix}: could not extract VBO session UUID",
                self.logger_context,
            )
            return None
        session = m.group(1)

        showevents_url = _VBO_SHOWEVENTS_URL.format(session=session)
        grid_html = await self.fetch_html(showevents_url)
        if not grid_html:
            Logger.warn(
                f"{self._log_prefix}: empty showevents grid from VBO",
                self.logger_context,
            )
            return None

        events = NestTheatreEventExtractor.extract_shows(grid_html, self.logger_context)
        if not events:
            self._warn_empty_extraction("VBO showevents grid", html=grid_html)
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} upcoming show occurrence(s)",
            self.logger_context,
        )
        return NestTheatrePageData(event_list=events)
