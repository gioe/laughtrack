"""Generic SimpleTix scraper for clubs using SimpleTix for ticketing.

Two page shapes are supported:

1. **Single event page** (``www.simpletix.com/e/{slug}-tickets-{id}``) — a
   recurring show whose dates live in an inline ``var timeArray = [...]``. Each
   future entry becomes a show. This is the original, default behaviour.
2. **Organizer/listing page** (``{org}.simpletix.com/``) — a venue with a full
   rotating calendar of one-off bookings. The listing has no showtimes itself;
   ``collect_scraping_targets`` enumerates its per-event ``/e/...`` links and
   each event page is scraped individually.

Single-date events render no ``timeArray``; for those the scraper falls back to
the page's JSON-LD ``Event`` data (converted from the JSON-LD UTC instant to the
venue's local wall-clock to match the timeArray convention).
"""

from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.simpletix import SimpleTixEvent
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from .data import SimpleTixPageData
from .extractor import SimpleTixExtractor
from .transformer import SimpleTixTransformer

_DEFAULT_TIMEZONE = "America/New_York"


class SimpleTixScraper(BaseScraper):
    """Generic scraper for SimpleTix-powered event pages."""

    key = "simpletix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SimpleTixTransformer(club))

    @staticmethod
    def _is_listing_url(url: str) -> bool:
        """True when ``url`` is a SimpleTix organizer/listing page.

        Organizer pages live on a per-venue subdomain (``{org}.simpletix.com``)
        and never contain a ``/e/`` event path. Single-event rows
        (``www.simpletix.com/e/...``) are excluded, so existing single-event
        clubs keep their original behaviour.
        """
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        return (
            host.endswith(".simpletix.com")
            and host != "www.simpletix.com"
            and "/e/" not in (parsed.path or "")
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Return per-event SimpleTix URLs to scrape.

        For an organizer/listing page, enumerate its ``/e/...`` event links;
        otherwise return the single configured event URL.
        """
        url = self.club.scraping_url
        if not url:
            Logger.error(
                f"{self._log_prefix}: No scraping_url configured",
                self.logger_context,
            )
            return []

        if not self._is_listing_url(url):
            return [url]

        html = await self.fetch_html(url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: empty response from listing page {url}",
                self.logger_context,
            )
            return []

        targets = SimpleTixExtractor.extract_listing_event_urls(html)
        if not targets:
            Logger.warn(
                f"{self._log_prefix}: no event links found on listing {url}",
                self.logger_context,
            )
            return []

        Logger.info(
            f"{self._log_prefix}: found {len(targets)} event(s) from listing {url}",
            self.logger_context,
        )
        return targets

    def _venue_timezone(self) -> ZoneInfo:
        """IANA timezone for converting JSON-LD UTC instants to local wall-clock."""
        try:
            return ZoneInfo(self.club.timezone or _DEFAULT_TIMEZONE)
        except Exception:
            return ZoneInfo(_DEFAULT_TIMEZONE)

    async def get_data(self, target: str) -> Optional[SimpleTixPageData]:
        """Fetch a SimpleTix event page and extract show times."""
        html = await self.fetch_html(target)
        if not html:
            return None

        time_entries, title, price = SimpleTixExtractor.extract_events(html)
        event_name = title or self.club.name
        now = datetime.now()

        if time_entries:
            events = self._events_from_time_array(time_entries, event_name, target, price, now)
        else:
            # Single-date bookings carry no timeArray — fall back to JSON-LD.
            events = self._events_from_jsonld(html, target, price, now)

        if not events:
            Logger.warn(
                f"{self._log_prefix}: no upcoming shows found on {target}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: Found {len(events)} upcoming shows on {target}",
            self.logger_context,
        )

        return SimpleTixPageData(event_list=events)

    def _events_from_time_array(
        self,
        time_entries: list,
        event_name: str,
        target: str,
        price: Optional[float],
        now: datetime,
    ) -> List[SimpleTixEvent]:
        events: List[SimpleTixEvent] = []
        for entry in time_entries:
            start_date = SimpleTixExtractor.parse_time_entry(entry.get("Time", ""))
            if not start_date:
                continue
            if start_date < now:  # Skip past events
                continue
            events.append(SimpleTixEvent(
                name=event_name,
                start_date=start_date,
                show_page_url=target,
                ticket_url=target,
                price=price,
                performers=[],
            ))
        return events

    def _events_from_jsonld(
        self,
        html: str,
        target: str,
        price: Optional[float],
        now: datetime,
    ) -> List[SimpleTixEvent]:
        tz = self._venue_timezone()
        events: List[SimpleTixEvent] = []
        for jl in SimpleTixExtractor.extract_jsonld_events(html):
            start_date = jl.start_date
            if not start_date:
                continue
            # JSON-LD startDate is a UTC instant; convert to the venue's local
            # wall-clock (naive) so it persists like the timeArray dates.
            if start_date.tzinfo is not None:
                start_date = start_date.astimezone(tz).replace(tzinfo=None)
            if start_date < now:  # Skip past events
                continue
            events.append(SimpleTixEvent(
                name=jl.name or self.club.name,
                start_date=start_date,
                show_page_url=target,
                ticket_url=target,
                price=price,
                performers=[],
            ))
        return events
