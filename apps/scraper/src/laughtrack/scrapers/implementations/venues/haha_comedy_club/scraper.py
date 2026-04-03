"""
HAHA Comedy Club scraper.

HAHA Comedy Club's calendar page (hahacomedyclub.com/calendar) is a
Webflow-built site that embeds both:
  - A JSON-LD Event block per show (name, date, performer, ticket URL,
    availability) inside a <script type="application/ld+json"> tag
  - The event start time in a visible HTML element:
    <div class="month day time">8:00 pm</div>

The individual Tixr event pages (tixr.com/e/{id}) that these links point to
are served through Tixr's DataDome WAF, which blocks GitHub Actions IP ranges
and caused 31/31 (100%) HTTP 403 failures in the 2026-04-01 nightly run.

This scraper avoids the per-event Tixr fetches entirely by extracting all
necessary show data (name, date+time, performer, ticket URL, availability)
directly from the calendar page HTML.
"""

import asyncio
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from laughtrack.core.clients.tixr import TixrVenueEventTransformer
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.exceptions import NetworkError
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.tixr.page_data import TixrPageData
from laughtrack.shared.types import ScrapingTarget

# HAHA Comedy Club is in North Hollywood, CA
_TIMEZONE = "America/Los_Angeles"

# Matches <script type="application/ld+json">…</script>
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

# Matches the time element: <div class="month day time">8:00 pm</div>
_TIME_RE = re.compile(r'class="month day time"[^>]*>\s*([^<]+)', re.IGNORECASE)

# Date formats produced by the HAHA calendar JSON-LD (e.g. "Apr 01, 2026")
_DATE_FMTS = ["%b %d, %Y", "%B %d, %Y"]


class HahaComedyClubScraper(BaseScraper):
    """
    Scraper for HAHA Comedy Club (North Hollywood, CA).

    Parses show data directly from the venue's calendar page HTML — no
    Tixr event-page fetches. Each show block on the calendar embeds a
    JSON-LD Event object (name, date, performer, ticket URL, availability)
    alongside an HTML element with the start time.
    """

    key = "haha_comedy_club"
    _RETRY_ATTEMPTS = 2   # retries after the initial attempt
    _RETRY_DELAY = 3.0    # seconds between retries

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TixrVenueEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        url = self.club.scraping_url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return [url]

    async def get_data(self, url: str) -> Optional[TixrPageData]:
        """
        Fetch the HAHA Comedy Club calendar page and parse all events from
        the embedded JSON-LD + time HTML elements.

        Args:
            url: Venue calendar page URL (from scraping_url)

        Returns:
            TixrPageData containing TixrEvent objects, or None if no events found
        """
        html_content: Optional[str] = None
        attempt = 0
        while attempt <= self._RETRY_ATTEMPTS:
            try:
                html_content = await self.fetch_html(url)
                break
            except NetworkError as e:
                if e.status_code is not None and 500 <= e.status_code < 600:
                    attempt += 1
                    if attempt <= self._RETRY_ATTEMPTS:
                        Logger.warning(
                            f"{self._log_prefix}: HTTP {e.status_code} fetching calendar page — retrying ({attempt}/{self._RETRY_ATTEMPTS})",
                            self.logger_context,
                        )
                        await asyncio.sleep(self._RETRY_DELAY)
                    else:
                        Logger.error(
                            f"{self._log_prefix}: Network error fetching {url} after {self._RETRY_ATTEMPTS} retries: {e}",
                            self.logger_context,
                        )
                        return None
                else:
                    Logger.error(f"{self._log_prefix}: Network error fetching {url}: {e}", self.logger_context)
                    return None
            except Exception as e:
                Logger.error(f"{self._log_prefix}: Unexpected error fetching calendar page {url}: {e}", self.logger_context)
                return None

        if not html_content:
            Logger.info(f"{self._log_prefix}: No HTML returned from {url}", self.logger_context)
            return None

        events = self._parse_events_from_html(html_content)

        if not events:
            Logger.info(f"{self._log_prefix}: No events parsed from {url}", self.logger_context)
            return None

        Logger.info(
            f"{self._log_prefix}: Parsed {len(events)} events from calendar page",
            self.logger_context,
        )
        return TixrPageData(event_list=events)

    def _parse_events_from_html(self, html_content: str) -> List[TixrEvent]:
        """
        Extract TixrEvent objects from the calendar page HTML.

        Each event occupies a block that contains:
        - A JSON-LD <script> with name, startDate, performer, offers
        - A <div class="month day time"> with the start time

        Args:
            html_content: Full HTML of the venue calendar page

        Returns:
            List of parsed TixrEvent objects
        """
        # Split the page at each event-item div boundary.
        # We look for the opening of each event-item block and process
        # everything up to the next one (or end of string).
        parts = re.split(r'(?=class="event-item)', html_content)

        events: List[TixrEvent] = []
        seen_ids: set = set()

        for part in parts:
            jsonld_match = _JSONLD_RE.search(part)
            if not jsonld_match:
                continue

            try:
                raw = jsonld_match.group(1).strip()
                parsed = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue

            # Unwrap list wrappers
            items = parsed if isinstance(parsed, list) else [parsed]
            event_data: Optional[Dict[str, Any]] = None
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "Event":
                    event_data = item
                    break

            if event_data is None:
                continue

            # Extract start time from HTML (e.g. "8:00 pm")
            time_match = _TIME_RE.search(part)
            time_str = time_match.group(1).strip() if time_match else None

            tixr_event = self._build_tixr_event(event_data, time_str)
            if tixr_event is None:
                continue

            # Deduplicate by event_id
            if tixr_event.event_id and tixr_event.event_id in seen_ids:
                continue
            if tixr_event.event_id:
                seen_ids.add(tixr_event.event_id)

            events.append(tixr_event)

        return events

    def _build_tixr_event(
        self, event_data: Dict[str, Any], time_str: Optional[str]
    ) -> Optional[TixrEvent]:
        """
        Build a TixrEvent from a JSON-LD Event dict and an optional time string.

        Args:
            event_data: JSON-LD Event dict from the calendar page
            time_str: Start time string from the HTML (e.g. "8:00 pm"), or None

        Returns:
            TixrEvent if successful, None otherwise
        """
        try:
            name = html.unescape(event_data.get("name", "").strip())
            if not name:
                return None

            date_str = event_data.get("startDate", "")
            if not date_str:
                Logger.warning(f"[{self.club.name}] JSON-LD Event has no startDate for '{name}'; skipping")
                return None

            date = self._parse_date(date_str, time_str)
            if date is None:
                Logger.warning(
                    f"[{self.club.name}] Could not parse date '{date_str}' + time '{time_str}' for '{name}'; skipping"
                )
                return None

            # Extract ticket URL from offers
            offers = event_data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            ticket_url = offers.get("url", "") if isinstance(offers, dict) else ""
            availability = offers.get("availability", "") if isinstance(offers, dict) else ""
            sold_out = "SoldOut" in availability
            price_raw = offers.get("price", "") if isinstance(offers, dict) else ""
            try:
                price = float(price_raw) if price_raw else 0.0
            except (ValueError, TypeError):
                price = 0.0

            ticket_type = offers.get("name", "General Admission") if isinstance(offers, dict) else "General Admission"
            tickets = [
                Ticket(
                    price=price,
                    purchase_url=ticket_url or self.club.website or "",
                    sold_out=sold_out,
                    type=ticket_type,
                )
            ]

            # Extract performer lineup
            performer = event_data.get("performer")
            lineup: List[Comedian] = []
            if isinstance(performer, dict):
                performer_name = html.unescape(performer.get("name", "").strip())
                if performer_name:
                    lineup.append(Comedian(name=performer_name))
            elif isinstance(performer, list):
                for p in performer:
                    if isinstance(p, dict):
                        pn = html.unescape(p.get("name", "").strip())
                        if pn:
                            lineup.append(Comedian(name=pn))

            show_page_url = event_data.get("url") or ticket_url or self.club.website or ""

            # Extract event ID from ticket URL (tixr.com/e/{id})
            event_id = ""
            if ticket_url:
                id_match = re.search(r'/e/(\d+)', ticket_url)
                if id_match:
                    event_id = id_match.group(1)
                else:
                    event_id = URLUtils.extract_id_from_url(ticket_url, ["/events/"]) or ""

            show = Show(
                name=name,
                club_id=self.club.id,
                date=date,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=["event"],
                description=None,
                timezone=_TIMEZONE,
                room="",
            )

            return TixrEvent.from_tixr_show(show=show, source_url=ticket_url, event_id=event_id)

        except Exception as e:
            Logger.error(f"[{self.club.name}] Error building TixrEvent: {e}")
            return None

    @staticmethod
    def _parse_date(date_str: str, time_str: Optional[str]) -> Optional[datetime]:
        """
        Parse a date string (e.g. "Apr 01, 2026") and optional time string
        (e.g. "8:00 pm") into a timezone-aware datetime for America/Los_Angeles.

        Args:
            date_str: Date string from JSON-LD startDate
            time_str: Time string from HTML, or None (defaults to midnight)

        Returns:
            Timezone-aware datetime, or None on parse failure
        """
        tz = pytz.timezone(_TIMEZONE)

        # Parse the date portion
        dt: Optional[datetime] = None
        for fmt in _DATE_FMTS:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                continue

        if dt is None:
            return None

        # Combine with time if available
        if time_str:
            time_str_clean = time_str.strip().lower()
            # Normalize: "6:00 pm" → try %I:%M %p
            for time_fmt in ("%I:%M %p", "%I %p"):
                try:
                    t = datetime.strptime(time_str_clean, time_fmt)
                    dt = dt.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                    break
                except ValueError:
                    continue

        return tz.localize(dt)
