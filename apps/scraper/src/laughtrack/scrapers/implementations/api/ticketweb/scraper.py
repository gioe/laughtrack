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
        """Fetch the calendar page and discover event detail URLs.

        Tries the inline ``var all_events`` JS array first. If absent, falls
        back to parsing the HTML-based ``tw-plugin-upcoming-event-list`` markup
        and follows pagination links to gather all pages.
        """
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

        # Primary: try the JS-based calendar array
        events = TicketWebExtractor.extract_calendar_events(html)

        # Fallback: parse the server-rendered HTML event list with pagination
        if not events:
            events = TicketWebExtractor.extract_html_calendar_events(html)
            # Follow pagination links (up to 10 pages to avoid runaway loops)
            page_html = html
            for _ in range(9):
                next_url = TicketWebExtractor.extract_next_page_url(page_html)
                if not next_url:
                    break
                page_html = await self.fetch_html(next_url)
                if not page_html:
                    break
                page_events = TicketWebExtractor.extract_html_calendar_events(page_html)
                if not page_events:
                    break
                events.extend(page_events)

        if not events:
            Logger.warn(
                f"{self._log_prefix}: No events found on {calendar_url}"
            )
            return []

        events = self._filter_calendar_events(events)
        if not events:
            Logger.info(
                f"{self._log_prefix}: no calendar events matched the configured "
                f"title filters on {calendar_url}",
                self.logger_context,
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

    def _filter_calendar_events(self, events: List[Dict]) -> List[Dict]:
        """Apply the opt-in title allow/block filter to discovered calendar events.

        Mixed-use TicketWeb venues (live-music rooms that also host a comedy
        series) expose every event on the same calendar. This filter keeps only
        the comedy shows when configured via ``scraping_sources.metadata``:

        - ``include_title_patterns`` — keep only events whose title matches at
          least one pattern (the comedy-series allowlist, e.g.
          ``["Clement St Comedy", "Best of San Francisco Stand-up"]``).
        - ``exclude_title_patterns`` — drop events whose title matches any
          pattern.

        Both are off by default, so existing pure-comedy TicketWeb sources
        (e.g. The Stand Up Comedy Club) are unchanged — the method returns the
        events untouched when neither key is configured. Pattern parsing /
        compilation (str-or-list, case-insensitive, re.error-guarded) is the
        shared :meth:`BaseScraper.compile_title_patterns` helper (TASK-3250);
        the include-then-exclude loop mirrors sellingticket / showare.
        """
        include = self.compile_title_patterns("include_title_patterns")
        exclude = self.compile_title_patterns("exclude_title_patterns")
        if not include and not exclude:
            return events

        kept: List[Dict] = []
        for ev in events:
            title = ev.get("title") or ""
            if include and not any(p.search(title) for p in include):
                continue
            if exclude and any(p.search(title) for p in exclude):
                continue
            kept.append(ev)

        dropped = len(events) - len(kept)
        if dropped:
            Logger.info(
                f"{self._log_prefix}: title filter dropped {dropped} of "
                f"{len(events)} calendar event(s); {len(kept)} kept",
                self.logger_context,
            )
        return kept

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
        ticket_url, sold_out, price = (None, False, None)
        if html:
            ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)
            price = TicketWebExtractor.extract_price(html)

        if ticket_url:
            ticket_html = await self.fetch_html(ticket_url)
            if ticket_html:
                sold_out = sold_out or TicketWebExtractor.is_event_sold_out(
                    ticket_html
                )

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
            price=price,
            performers=[cal_event["title"]],
        )

        return TicketWebPageData(event_list=[event])
