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
       → fetch fresh VBO session key from loadplugin endpoint
       → fetch showevents HTML using the fresh key
       → return one target string per comedy-show event:
         ``"{eid}|{initial_edid}|{title}"``

  2. get_data(target)
       → parse eid / edid / title from the target string
       → fetch the date-slider HTML for that event
       → parse individual show instances
       → return CszPhillyPageData

  3. transformation_pipeline (CszPhillyEventTransformer)
       → CszPhillyShowInstance → Show

Session Key
-----------
The VBO session key (``s=`` parameter) is fetched dynamically on each run by
calling ``plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>``.  This
makes the scraper self-healing: it acquires the current key from VBO rather
than relying on a static value stored in ``club.scraping_url``.  If the
loadplugin call fails, the scraper falls back to the key stored in
``club.scraping_url`` so that a transient network error does not silence the
venue entirely.
"""

import re
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import CszPhillyEventExtractor
from .page_data import CszPhillyPageData
from .transformer import CszPhillyEventTransformer


_SITE_ID = "50F7AC53-FC8E-4EB7-9C09-810A40F1181A"

_VBO_LOADPLUGIN_URL = (
    f"https://plugin.vbotickets.com/plugin/loadplugin?siteid={_SITE_ID}&page=ListEvents"
)

_SHOWEVENTS_URL = (
    "https://plugin.vbotickets.com/Plugin/events/showevents"
    "?ViewType=list&EventType=current&day=&s={session_key}"
)

_DATE_SLIDER_URL = (
    "https://plugin.vbotickets.com/v5.0/controls/events.asp"
    "?a=load_eventdate_slider&eid={eid}&edid={edid}&tza=3&s={session_key}"
)

# Regex to extract the UUID session from the VBO loadplugin JS response.
# VBO embeds the session as an unquoted JS object key: `value: "uuid"`.
_SESSION_RE = re.compile(
    r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.IGNORECASE,
)

_TARGET_SEP = "|"


class CszPhiladelphiaScraper(BaseScraper):
    """
    Scraper for CSz Philadelphia (ComedySportz) via the VBO Tickets plugin API.
    """

    key = "csz_philadelphia"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        # Seed with the static key from scraping_url as a fallback.  The real
        # key is refreshed dynamically in collect_scraping_targets().
        self._session_key = self._extract_session_key(club.scraping_url or "")
        self._csz_transformer = CszPhillyEventTransformer(club, session_key=self._session_key)
        self.transformation_pipeline.register_transformer(self._csz_transformer)

    # ------------------------------------------------------------------
    # Public pipeline methods
    # ------------------------------------------------------------------

    async def collect_scraping_targets(self) -> List[str]:
        """
        Fetch the VBO events list and return one target per comedy show.

        Acquires a fresh VBO session key from the loadplugin endpoint before
        fetching events.  Falls back to the static key from ``scraping_url``
        if the loadplugin call fails.

        Each target is ``"{eid}|{edid}|{title}"``.
        """
        fresh_key = await self._acquire_session_key()
        if fresh_key:
            self._session_key = fresh_key
            self._csz_transformer._session_key = fresh_key
        else:
            Logger.warn(
                f"{self._log_prefix}: loadplugin did not return a session key — "
                f"falling back to static scraping_url key (s={self._session_key[:8]}...)",
                self.logger_context,
            )

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
                    f"session key may be stale (s={self._session_key[:8]}...). "
                    f"VBO loadplugin may be returning an unexpected response.",
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

    async def _acquire_session_key(self) -> str:
        """
        Fetch a fresh VBO session key from the loadplugin endpoint.

        Returns the UUID string on success, or an empty string if the
        loadplugin call fails or does not contain a recognisable UUID.
        """
        try:
            html = await self.fetch_html(_VBO_LOADPLUGIN_URL)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: failed to fetch VBO loadplugin: {e} — will fall back to static key",
                self.logger_context,
            )
            return ""

        if not html:
            Logger.warn(
                f"{self._log_prefix}: empty response from VBO loadplugin",
                self.logger_context,
            )
            return ""

        m = _SESSION_RE.search(html)
        if not m:
            Logger.warn(
                f"{self._log_prefix}: could not extract session UUID from loadplugin response",
                self.logger_context,
            )
            return ""

        session_key = m.group(1)
        Logger.debug(
            f"{self._log_prefix}: acquired VBO session {session_key[:8]}...",
            self.logger_context,
        )
        return session_key

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
