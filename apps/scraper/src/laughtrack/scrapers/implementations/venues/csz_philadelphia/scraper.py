"""
CSz Philadelphia (ComedySportz) scraper implementation.

CSz Philadelphia sells tickets through the VBO Tickets platform embedded on
their Squarespace calendar page (https://www.comedysportzphilly.com/calendar).
The plugin exposes two server-rendered HTML endpoints that we exploit directly:

  1. showevents  — returns all upcoming events for the venue.  We filter to
     events with ``data-event-subcategory="Comedy"`` to skip improv classes.

  2. load_eventdate_slider  — for a given event ID returns a slider widget
     listing every individual upcoming performance (month / day / time).

Pipeline
--------
  1. collect_scraping_targets()
       → fetch showevents HTML
       → return one target string per comedy-show event:
         ``"{eid}|{initial_edid}|{title}"``

  2. get_data(target)
       → parse eid / edid / title from the target string
       → fetch the date-slider HTML for that event
       → parse individual show instances
       → return CszPhillyPageData

  3. transformation_pipeline (CszPhillyEventTransformer)
       → CszPhillyShowInstance → Show

Configuration
-------------
The ``club.scraping_url`` field stores the full VBO plugin URL including the
venue-specific session key (``s=`` parameter), e.g.:
  ``https://plugin.vbotickets.com/Plugin/events?s=4610c334-...``
"""

from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import CszPhillyEventExtractor
from .page_data import CszPhillyPageData
from .transformer import CszPhillyEventTransformer


_SHOWEVENTS_URL = (
    "https://plugin.vbotickets.com/Plugin/events/showevents"
    "?ViewType=list&EventType=current&day=&s={session_key}"
)

_DATE_SLIDER_URL = (
    "https://plugin.vbotickets.com/v5.0/controls/events.asp"
    "?a=load_eventdate_slider&eid={eid}&edid={edid}&tza=3&s={session_key}"
)

_TARGET_SEP = "|"


class CszPhiladelphiaScraper(BaseScraper):
    """
    Scraper for CSz Philadelphia (ComedySportz) via the VBO Tickets plugin API.
    """

    key = "csz_philadelphia"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._session_key = self._extract_session_key(club.scraping_url or "")
        self.transformation_pipeline.register_transformer(
            CszPhillyEventTransformer(club, session_key=self._session_key)
        )

    # ------------------------------------------------------------------
    # Public pipeline methods
    # ------------------------------------------------------------------

    async def collect_scraping_targets(self) -> List[str]:
        """
        Fetch the VBO events list and return one target per comedy show.

        Each target is ``"{eid}|{edid}|{title}"``.
        """
        try:
            url = _SHOWEVENTS_URL.format(session_key=self._session_key)
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(f"{self._log_prefix}: empty response from showevents endpoint", self.logger_context)
                return []

            if not self._is_valid_events_page(html):
                Logger.warn(
                    f"{self._log_prefix}: showevents response missing expected structure "
                    f"('CurrentEvents' / 'EventListWrapper') — "
                    f"session key may be stale (s={self._session_key}). "
                    f"Refresh scraping_url to resolve.",
                    self.logger_context,
                )
                return []

            comedy_events = CszPhillyEventExtractor.parse_comedy_events(html)
            targets = [
                f"{eid}{_TARGET_SEP}{edid}{_TARGET_SEP}{title}"
                for eid, edid, title in comedy_events
            ]
            Logger.info(f"{self._log_prefix}: discovered {len(targets)} comedy show(s)", self.logger_context)
            return targets

        except Exception as e:
            Logger.error(f"{self._log_prefix}: collect_scraping_targets failed: {e}", self.logger_context)
            return []

    async def get_data(self, target: str) -> Optional[CszPhillyPageData]:
        """
        Fetch individual show dates for one comedy-show event.

        Args:
            target: A ``"{eid}|{edid}|{title}"`` string from collect_scraping_targets().

        Returns:
            CszPhillyPageData with one CszPhillyShowInstance per upcoming performance.
        """
        try:
            eid, edid, title = self._parse_target(target)
        except ValueError as e:
            Logger.error(f"{self._log_prefix}: malformed target '{target}': {e}", self.logger_context)
            return None

        try:
            url = _DATE_SLIDER_URL.format(
                eid=eid, edid=edid, session_key=self._session_key
            )
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(f"{self._log_prefix}: empty date-slider response for eid={eid}", self.logger_context)
                return None

            instances = CszPhillyEventExtractor.parse_show_dates(html, eid, title)
            if not instances:
                Logger.warn(f"{self._log_prefix}: no upcoming dates for '{title}' (eid={eid})", self.logger_context)
                return CszPhillyPageData(event_list=[])

            Logger.info(f"{self._log_prefix}: {len(instances)} upcoming date(s) for '{title}'", self.logger_context)
            return CszPhillyPageData(event_list=instances)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for target '{target}': {e}", self.logger_context)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_events_page(html: str) -> bool:
        """
        Return True if the showevents HTML looks like a genuine events page.

        A stale or invalid session key typically causes VBO to return a redirect
        page or an empty shell that lacks the expected structural markers.
        We accept the page if it contains either the outer ``CurrentEvents``
        container or at least one ``EventListWrapper`` item div.
        """
        return "CurrentEvents" in html or "EventListWrapper" in html

    @staticmethod
    def _extract_session_key(scraping_url: str) -> str:
        """
        Extract the VBO session key (``s=`` param) from ``club.scraping_url``.

        Falls back to treating the whole value as the session key for
        backward compatibility if no URL structure is found.
        """
        if not scraping_url:
            return ""
        try:
            parsed = urlparse(scraping_url)
            params = parse_qs(parsed.query)
            if "s" in params:
                return params["s"][0]
        except Exception:
            pass
        # Treat the raw value as the key itself (plain UUID stored directly)
        return scraping_url.strip()

    @staticmethod
    def _parse_target(target: str):
        """Parse ``"{eid}|{edid}|{title}"`` into ``(eid: int, edid: int, title: str)``."""
        parts = target.split(_TARGET_SEP, 2)
        if len(parts) != 3:
            raise ValueError(f"expected 3 pipe-separated parts, got {len(parts)}")
        eid = int(parts[0])
        edid = int(parts[1])
        title = parts[2]
        return eid, edid, title
