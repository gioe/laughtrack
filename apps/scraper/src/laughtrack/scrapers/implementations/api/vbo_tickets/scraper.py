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
SiteID) — no per-venue code required. An optional ``category_filter`` in
``scraping_sources.metadata`` restricts the listing to matching
``data-event-category`` values (e.g. "Live Shows" to drop a venue's classes).
The extractor parses both VBO's structured per-occurrence rows
("Tue, 6/16/2026 @ 7:00 PM") and free-form / recurring date text entered by
hand ("Fri 9:30pm 6/5, 6/12, ..."), expanding the latter into one show per
upcoming date.

Consolidation note (TASK-2938): The Nest Theatre — formerly the venue-specific
``nest_theatre`` scraper — was migrated onto this generic scraper, since it reads
the same ``showevents`` listing and differed only in its category filter and
free-form recurring dates (both now handled here). The remaining venue-specific
VBO scrapers (``esthers_follies``, ``csz_philadelphia``) stay separate: they use
the single-event date-slider endpoint with per-show seat-tier enrichment
(esthers_follies) / dynamic session self-healing + per-event date expansion
(csz_philadelphia), neither of which the multi-event listing flow models.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.vbo_tickets import VboEvent
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

        # Optional per-source config: a ``category_filter`` in
        # scraping_sources.metadata restricts the listing to matching
        # ``data-event-category`` values (e.g. "Live Shows" to drop classes).
        category_filter = self.club.source_metadata.get("category_filter")
        events = VboTicketsExtractor.extract_events(
            listing_html or "",
            category_filter=category_filter,
            club_name=self.club.name or "",
        )
        if not events:
            self._warn_empty_extraction(url, html=listing_html)
            return None

        # Optional per-source title filter for mixed-use venues (concerts /
        # films / theatre / magic alongside comedy) whose VBO categories don't
        # isolate comedy — e.g. a performing-arts center running only a
        # "Comedy Under the Stars" series. ``include_title_patterns`` keeps only
        # matching event names; ``exclude_title_patterns`` drops matches. Both
        # are OFF by default, so existing single-purpose VBO venues are
        # unaffected.
        events = self._filter_events_by_title(events)
        if not events:
            Logger.info(
                f"{self._log_prefix}: no VBO events matched configured title filters",
                self.logger_context,
            )
            return None

        Logger.info(f"{self._log_prefix}: extracted {len(events)} events from VBO listing", self.logger_context)
        return VboTicketsPageData(event_list=events)

    def _filter_events_by_title(self, events: List[VboEvent]) -> List[VboEvent]:
        """Keep/drop events by name via metadata-driven title regexes.

        Reads ``include_title_patterns`` / ``exclude_title_patterns`` from
        ``scraping_sources.metadata`` (single regex or list, case-insensitive)
        through the shared ``BaseScraper.compile_title_patterns`` helper. When
        neither key is configured the list passes through unchanged.
        """
        include_patterns = self.compile_title_patterns("include_title_patterns")
        exclude_patterns = self.compile_title_patterns("exclude_title_patterns")
        if not include_patterns and not exclude_patterns:
            return events

        filtered: List[VboEvent] = []
        for event in events:
            title = event.name or ""
            if include_patterns and not any(p.search(title) for p in include_patterns):
                continue
            if exclude_patterns and any(p.search(title) for p in exclude_patterns):
                continue
            filtered.append(event)
        return filtered
