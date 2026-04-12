"""Generic TicketWeb scraper for clubs using the TicketWeb calendar WordPress plugin.

Scrapes directly from the club's own website rather than from TicketWeb/Ticketmaster
APIs, so that show_page_url points to the club's site and drives traffic to the venue.

Two-phase approach:
  1. Calendar page: parse the inline `var all_events = [...]` JS array to discover
     event names, dates, and detail page URLs on the club's site.
  2. Detail pages: extract the TicketWeb ticket purchase URL and sold-out status
     from each event's detail page.
"""

from typing import Dict, List, Optional, TYPE_CHECKING

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from .extractor import TicketWebExtractor
from .transformer import TicketWebTransformer

if TYPE_CHECKING:
    from .data import TicketWebPageData


class TicketWebScraper(BaseScraper):
    """Generic scraper for TicketWeb-powered club calendar pages."""

    key = "ticketweb"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TicketWebTransformer(club))
        self._calendar_events: Dict[str, Dict] = {}

    async def collect_scraping_targets(self) -> List[str]:
        """Fetch the calendar page and discover event detail URLs."""
        calendar_url = self.club.scraping_url
        if not calendar_url:
            Logger.error(
                f"{self._log_prefix}: No scraping_url configured",
                self.logger_context,
            )
            return []

        html = await self.fetch_html(calendar_url)
        if not html:
            return []

        events = TicketWebExtractor.extract_calendar_events(html)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: No events found in calendar JS on {calendar_url}"
            )
            return []

        # Cache calendar data keyed by detail page URL for use in get_data
        for ev in events:
            self._calendar_events[ev["url"]] = ev

        Logger.info(
            f"{self._log_prefix}: Found {len(events)} events on calendar page",
            self.logger_context,
        )
        return [ev["url"] for ev in events]

    async def get_data(self, target: str) -> Optional["TicketWebPageData"]:
        """Fetch a detail page and extract the TicketWeb ticket URL."""
        from .data import TicketWebPageData
        from laughtrack.core.entities.event.ticketweb import TicketWebEvent

        cal_event = self._calendar_events.get(target)
        if not cal_event:
            Logger.warn(
                f"{self._log_prefix}: No cached calendar data for {target}"
            )
            return None

        html = await self.fetch_html(target)
        ticket_url, sold_out = (None, False)
        if html:
            ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        if not ticket_url:
            Logger.warn(
                f"{self._log_prefix}: No TicketWeb buy link found on {target}"
            )

        event = TicketWebEvent(
            name=cal_event["title"],
            start_date=cal_event["start_date"],
            show_page_url=target,
            ticket_url=ticket_url,
            sold_out=sold_out,
            performers=[cal_event["title"]],
        )

        return TicketWebPageData(event_list=[event])
