"""
Generic TicketsCandy platform scraper.

TicketsCandy (ticketscandy.com) is a ticketing platform. Venues link out to
per-show TicketsCandy event pages from their own websites; each TicketsCandy
page carries a standard schema.org Event JSON-LD block (name, startDate,
location, offers). There is no TicketsCandy organizer/venue aggregation
endpoint, so this scraper discovers the event URLs by crawling the venue's own
listing page (and, optionally, its per-show sub-pages — a "two-hop" crawl for
WordPress sites like Funny Pharm whose /shows/ index links to /shows/<slug>/
pages that each carry the TicketsCandy links).

Config (scraping_sources):
  source_url : the venue's shows-listing page (e.g. https://.../shows/)
  metadata.detail_link_prefix : optional path prefix (e.g. "/shows/"); when set,
      same-host sub-pages under that prefix are also crawled for TicketsCandy
      links (two-hop). Omit for venues that link to TicketsCandy directly from
      the listing (one-hop).

Timezone quirk (important): TicketsCandy emits startDate as the venue-local
wall-clock time but mislabels the offset as +00:00 (e.g. "2026-07-10T19:30:00
+00:00" for a 7:30 PM Eastern show). This scraper strips that bogus offset and
re-localizes the wall-clock to the club's timezone, so the show lands at the
correct instant (mirrors the localize pattern in revolution_hall).
"""

import re
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

from .data import TicketsCandyPageData
from .extractor import TicketsCandyExtractor
from .transformer import TicketsCandyTransformer

# Bound the per-show sub-page crawl so a malformed listing can't fan out forever.
_MAX_SUBPAGES = 100

# Matches a clock time in the event title, e.g. "7:30PM", "7:30 PM", "7PM".
_TITLE_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([AaPp])\.?[Mm]\.?")


class TicketsCandyScraper(BaseScraper):
    """Scraper for venues that ticket via TicketsCandy."""

    key = "ticketscandy"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TicketsCandyTransformer(club))
        # Map each TicketsCandy event URL back to the venue page it was found on,
        # so show_page_url points at the venue's own site (drives traffic there)
        # while the ticket purchase URL stays the TicketsCandy link.
        self._source_page_by_event_url: dict[str, str] = {}

    async def scrape_async(self) -> List[Show]:
        """Discover TicketsCandy event URLs by crawling the venue site, then
        fetch + transform each via the standard BaseScraper pipeline."""
        try:
            listing_url = URLUtils.normalize_url(self.club.scraping_url)
            event_urls = await self._discover_event_urls(listing_url)
            if not event_urls:
                Logger.warn(
                    f"{self._log_prefix}: no TicketsCandy event URLs found from {listing_url}",
                    self.logger_context,
                )
                return []

            Logger.info(
                f"{self._log_prefix}: found {len(event_urls)} TicketsCandy event pages",
                self.logger_context,
            )
            raw_data_results = await self._fetch_all_raw_data(sorted(event_urls))
            shows = self._transform_all_raw_data(raw_data_results)
            Logger.info(
                f"{self._log_prefix}: scraped {len(shows)} shows", self.logger_context
            )
            return shows
        except Exception as e:
            Logger.error(f"{self._log_prefix}: scraping failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    async def get_data(self, url: str) -> Optional[TicketsCandyPageData]:
        """Fetch one TicketsCandy event page, parse its Event JSON-LD, and fix
        the mislabeled timezone offset."""
        try:
            html = await self.fetch_html(url)
            if not html:
                return None

            same_as = self._source_page_by_event_url.get(url)
            events = EventExtractor.extract_events(html, same_as_override=same_as)
            if not events:
                Logger.warn(
                    f"{self._log_prefix}: no Event JSON-LD on {url}", self.logger_context
                )
                return None

            for event in events:
                self._fix_start_date(event)
            return TicketsCandyPageData(event_list=events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}", self.logger_context
            )
            return None

    def _fix_start_date(self, event: JsonLdEvent) -> None:
        """Anchor the show to the correct local instant.

        Two TicketsCandy data quirks are corrected here:
        1. The startDate offset is mislabeled +00:00 even though the time is
           venue-local wall-clock, so the parsed zone is wrong.
        2. The startDate *time* component is sometimes wrong (e.g. 07:00 for a
           7:30 PM show) while the title reliably reads "(... - 7:30PM)".

        Strategy: keep the date from startDate, prefer the title's clock time
        when present (else fall back to the startDate wall-clock), and localize
        the result to the club timezone.
        """
        start: Optional[datetime] = event.start_date
        if start is None:
            return
        naive = start.replace(tzinfo=None)
        match = _TITLE_TIME_RE.search(event.name or "")
        if match:
            hour = int(match.group(1)) % 12
            if match.group(3).lower() == "p":
                hour += 12
            minute = int(match.group(2) or 0)
            naive = naive.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            # No title time to fall back on, so the (sometimes-wrong) startDate
            # time is used as-is. Log it so a title-format change is observable.
            Logger.warn(
                f"{self._log_prefix}: no clock time in title {event.name!r}; "
                f"using startDate time {naive.strftime('%H:%M')} verbatim",
                self.logger_context,
            )
        tz_name = self.club.timezone or "America/New_York"
        event.start_date = naive.replace(tzinfo=ZoneInfo(tz_name))

    async def _discover_event_urls(self, listing_url: str) -> set[str]:
        """Collect TicketsCandy event URLs from the listing page and, when a
        detail_link_prefix is configured, from its same-host sub-pages."""
        event_urls: set[str] = set()
        listing_html = await self.fetch_html(listing_url)
        if not listing_html:
            return event_urls

        # One-hop: TicketsCandy links present directly on the listing.
        for u in TicketsCandyExtractor.extract_event_urls(listing_html):
            event_urls.add(u)
            self._source_page_by_event_url.setdefault(u, listing_url)

        # Two-hop: crawl same-host sub-pages under detail_link_prefix.
        prefix = (self.club.source_metadata or {}).get("detail_link_prefix")
        if isinstance(prefix, str) and prefix:
            all_subpages = TicketsCandyExtractor.extract_subpage_urls(
                listing_html, listing_url, prefix
            )
            subpages = all_subpages[:_MAX_SUBPAGES]
            if len(all_subpages) > _MAX_SUBPAGES:
                Logger.warn(
                    f"{self._log_prefix}: sub-page crawl capped at {_MAX_SUBPAGES}; "
                    f"dropped {len(all_subpages) - _MAX_SUBPAGES}",
                    self.logger_context,
                )
            sub_results = await self._fetch_all_raw_subpages(subpages)
            for sub_url, sub_html in sub_results:
                if not sub_html:
                    continue
                for u in TicketsCandyExtractor.extract_event_urls(sub_html):
                    event_urls.add(u)
                    self._source_page_by_event_url.setdefault(u, sub_url)
        return event_urls

    async def _fetch_all_raw_subpages(self, urls: List[str]) -> List[tuple[str, Optional[str]]]:
        """Fetch sub-pages serially through the shared rate limiter, returning
        (url, html) pairs."""
        results: List[tuple[str, Optional[str]]] = []
        for url in urls:
            await self.rate_limiter.await_if_needed(url)
            try:
                results.append((url, await self.fetch_html(url)))
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: sub-page fetch failed for {url}: {e}",
                    self.logger_context,
                )
                results.append((url, None))
        return results
