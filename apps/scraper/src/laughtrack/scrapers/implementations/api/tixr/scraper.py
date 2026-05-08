"""
Generic Tixr scraper for venues whose calendar page links to Tixr events.

Any venue that lists shows by embedding tixr.com/e/{id} short URLs or
tixr.com/groups/*/events/* long-form URLs can be onboarded with only a
DB row (scraper='tixr', scraping_url=<calendar page>) — no Python changes needed.

Pipeline:
1. Fetch club.scraping_url as HTML.
2. Extract all Tixr event URLs (short and long form) via TixrExtractor.
2.5. If the page embeds an Organization JSON-LD block, filter to only URLs whose
     event ID appears in that block — these are the events Tixr has fully configured
     server-side (reliable JSON-LD on individual event pages).  Falls back to all
     HTML-extracted URLs when the Org JSON-LD block is absent.
3. Batch-resolve each URL to a TixrEvent via TixrClient.get_event_detail_from_url().
4. Return TixrPageData containing the resolved events.
"""

from datetime import datetime
import html
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pytz
from bs4 import BeautifulSoup

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.clients.tixr import TixrVenueEventTransformer
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.infrastructure.monitoring import create_monitored_tixr_client
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper

from .extractor import TixrExtractor
from .data import TixrPageData

_MAX_DISCOVERY_PAGES = 12
_HOUSE_OF_COMEDY_BLOOMINGTON_HOST = "moa.houseofcomedy.net"
_ST_MARKS_COMEDY_HOST = "www.stmarkscomedyclub.com"
_IMPROV_ASYLUM_PIXL_EVENTS_URL = "https://calendar.improvasylum.com/api/events/improv-asylum"
_MONTH_FORMATS = ("%b", "%B")
_TIME_FORMATS = ("%I:%M %p", "%I %p")
_MAX_YEAR_ROLLOVER_DAYS = 180


class TixrScraper(BaseScraper):
    """
    Generic scraper for venues that list Tixr event links on a calendar page.

    Supports both short-form (tixr.com/e/{id}) and long-form
    (tixr.com/groups/*/events/*-{id}) Tixr URLs. A new venue can be onboarded
    by inserting a DB row with scraper='tixr' and scraping_url set to its
    calendar page — no code changes required.
    """

    key = "tixr"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TixrVenueEventTransformer(club))
        self.tixr_client = create_monitored_tixr_client(club)
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_comedy_venue_config(),
            logger_context=club.as_context(),
        )

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Discover the venue calendar pages to scrape.

        Most Tixr-backed venues expose all event links on a single page, but some
        paginate venue-owned calendar pages ("more shows", month navigation, etc.).
        Crawl a bounded same-site pagination graph first, then extract Tixr event
        links from each discovered page in ``get_data()``.
        """
        url = self.club.scraping_url
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        pending = [url]
        seen: set[str] = set()
        targets: List[ScrapingTarget] = []

        while pending and len(targets) < _MAX_DISCOVERY_PAGES:
            current = URLUtils.normalize_url(pending.pop(0))
            if current in seen:
                continue
            seen.add(current)
            targets.append(current)

            html_content = await self._fetch_calendar_html(current)
            if not html_content:
                continue

            for next_url in TixrExtractor.extract_pagination_urls(html_content, current):
                normalized_next = URLUtils.normalize_url(next_url)
                if normalized_next not in seen and normalized_next not in pending:
                    pending.append(normalized_next)

        if len(targets) > 1:
            Logger.info(
                f"{self._log_prefix}: Discovered {len(targets)} calendar pages before Tixr extraction",
                self.logger_context,
            )

        return targets

    async def _fetch_calendar_html(self, url: str) -> Optional[str]:
        """
        Fetch a venue calendar page through the appropriate HTTP path.

        Tixr-hosted group pages use the DataDome-aware Tixr client path; venue-owned
        pages stay on the standard HttpClient path with shared retry/fallback logic.
        """
        normalized = URLUtils.normalize_url(url)
        if "tixr.com" in normalized:
            return await self.tixr_client._fetch_tixr_page(normalized)
        return await self.fetch_html(normalized)

    async def get_data(self, url: str) -> Optional[TixrPageData]:
        """
        Fetch the calendar page, extract Tixr URLs, and resolve each to a TixrEvent.

        Args:
            url: Venue calendar page URL (from scraping_url)

        Returns:
            TixrPageData containing resolved TixrEvent objects, or None if no events found
        """
        try:
            html_content = await self._fetch_calendar_html(url)

            if not html_content:
                Logger.info(f"{self._log_prefix}: No HTML content returned from {url}", self.logger_context)
                return None

            all_tixr_urls = TixrExtractor.extract_tixr_urls(html_content)

            if not all_tixr_urls:
                fallback_events = await self._fetch_improv_asylum_pixl_events(url)
                if fallback_events:
                    Logger.info(
                        f"{self._log_prefix}: Parsed {len(fallback_events)} events from Improv Asylum Pixl Calendar "
                        "fallback after Tixr group-page extraction returned no URLs",
                        self.logger_context,
                    )
                    return TixrPageData(event_list=fallback_events)

                Logger.warn(
                    f"{self._log_prefix}: page fetch succeeded (html_len={len(html_content)}) "
                    f"but no Tixr URLs were extracted from {url} — either a bot-block "
                    f"interstitial or a genuinely-empty calendar",
                    self.logger_context,
                )
                return None

            # Filter to only events listed in the Organization JSON-LD block — these
            # are the ones Tixr has fully configured server-side and reliably embed
            # JSON-LD on their individual event pages.  Fall back to all HTML URLs
            # when the Org JSON-LD block is absent (non-group-page calendars).
            #
            # Match by numeric event ID rather than URL string: the JSON-LD block may
            # list long-form URLs while the calendar page HTML contains short-form URLs
            # for the same events (or vice versa).  A string-equality check would
            # produce an empty intersection even when the event sets overlap perfectly.
            org_jsonld_urls = TixrExtractor.extract_org_jsonld_event_urls(html_content)
            if org_jsonld_urls:
                org_event_ids = {
                    TixrExtractor.get_event_id(u) for u in org_jsonld_urls
                } - {None}
                tixr_urls = [
                    u for u in all_tixr_urls
                    if TixrExtractor.get_event_id(u) in org_event_ids
                ]
                skipped = len(all_tixr_urls) - len(tixr_urls)
                if skipped > 0:
                    Logger.info(
                        f"{self._log_prefix}: Skipping {skipped} of {len(all_tixr_urls)} URLs "
                        f"not in group JSON-LD (no server-side event data available)",
                        self.logger_context,
                    )
            else:
                tixr_urls = all_tixr_urls

            if not tixr_urls:
                Logger.info(f"{self._log_prefix}: No processable Tixr URLs after filtering on {url}", self.logger_context)
                return None

            fallback_events = self._parse_public_calendar_events(html_content, url)
            if fallback_events:
                Logger.info(
                    f"{self._log_prefix}: Parsed {len(fallback_events)} events from venue-owned public cards on {url}; "
                    "skipping blocked Tixr detail fetches",
                    self.logger_context,
                )
                return TixrPageData(event_list=fallback_events)

            Logger.info(f"{self._log_prefix}: Extracted {len(tixr_urls)} Tixr URLs from {url}", self.logger_context)

            results = await self.batch_scraper.process_batch(
                tixr_urls,
                lambda u: self.tixr_client.get_event_detail_from_url(u),
                "Tixr event extraction",
            )
            tixr_events = results

            if not tixr_events:
                Logger.info(
                    f"{self._log_prefix}: No TixrEvents returned from {len(tixr_urls)} URLs on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: Successfully processed {len(tixr_events)} TixrEvents from {len(tixr_urls)} URLs",
                self.logger_context,
            )
            return TixrPageData(event_list=tixr_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None

    async def _fetch_improv_asylum_pixl_events(self, url: str) -> List[TixrEvent]:
        """
        Fetch Improv Asylum events from its venue-owned Pixl Calendar API.

        The active DB source still points at the Tixr group page, which is
        DataDome-blocked in automation. The public Improv Asylum site links to
        calendar.improvasylum.com, whose API exposes complete event/ticket data.
        """
        if not self._is_improv_asylum_tixr_source(url):
            return []

        data = await self.fetch_json(_IMPROV_ASYLUM_PIXL_EVENTS_URL)
        if not isinstance(data, dict):
            return []

        return self._parse_pixl_calendar_events(data)

    def _is_improv_asylum_tixr_source(self, url: str) -> bool:
        normalized = URLUtils.normalize_url(url).lower()
        return (
            self.club.id == 141
            or self.club.name.strip().lower() == "improv asylum"
        ) and "tixr.com/groups/improvasylum" in normalized

    def _parse_pixl_calendar_events(self, data: Dict[str, Any]) -> List[TixrEvent]:
        events = data.get("events")
        if not isinstance(events, list):
            return []

        parsed: List[TixrEvent] = []
        seen_ids: set[str] = set()
        for event in events:
            if not isinstance(event, dict):
                continue

            tixr_event = self._build_pixl_tixr_event(event)
            if tixr_event is None:
                continue

            if tixr_event.event_id and tixr_event.event_id in seen_ids:
                continue
            if tixr_event.event_id:
                seen_ids.add(tixr_event.event_id)

            parsed.append(tixr_event)

        return parsed

    def _build_pixl_tixr_event(self, event: Dict[str, Any]) -> Optional[TixrEvent]:
        title = html.unescape(str(event.get("title") or "").strip())
        start_str = str(event.get("start") or "").strip()
        ticket_url = str(event.get("ticketUrl") or "").strip()
        if not title or not start_str or not ticket_url:
            return None

        timezone_name = str(event.get("timezone") or self.club.timezone or "America/New_York")
        try:
            date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            local_tz = pytz.timezone(timezone_name)
            date = date.astimezone(local_tz)
        except Exception as exc:
            Logger.warn(
                f"{self._log_prefix}: Skipping Pixl event '{title}' with unparseable start {start_str!r}: {exc}",
                self.logger_context,
            )
            return None

        raw_desc = event.get("description")
        description = html.unescape(str(raw_desc)) if raw_desc else None
        tickets = self._build_pixl_tickets(event, ticket_url)
        event_id = TixrExtractor.get_event_id(ticket_url) or ""

        show = Show(
            name=title,
            club_id=self.club.id,
            date=date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            description=description,
            timezone=timezone_name,
            room=str(event.get("venue") or ""),
        )
        return TixrEvent.from_tixr_show(show=show, source_url=ticket_url, event_id=event_id)

    def _build_pixl_tickets(self, event: Dict[str, Any], ticket_url: str) -> List[Ticket]:
        tickets: List[Ticket] = []
        sales = event.get("sales")
        if isinstance(sales, list):
            for sale in sales:
                if not isinstance(sale, dict):
                    continue
                price = self._parse_price(sale.get("currentPrice"))
                ticket_type = str(sale.get("name") or "General Admission")
                state = str(sale.get("state") or "OPEN").upper()
                tickets.append(
                    Ticket(
                        price=price,
                        purchase_url=ticket_url,
                        sold_out=state != "OPEN",
                        type=ticket_type,
                    )
                )

        if tickets:
            return tickets

        status = str(event.get("status") or "available").lower()
        return [
            Ticket(
                price=self._parse_price(event.get("price")),
                purchase_url=ticket_url,
                sold_out=status not in ("available", "open"),
                type="General Admission",
            )
        ]

    @staticmethod
    def _parse_price(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_public_calendar_events(self, html_content: str, url: str) -> List[TixrEvent]:
        """Parse venue-owned Webflow cards when Tixr detail pages are blocked."""
        if urlparse(URLUtils.normalize_url(url)).netloc.lower() not in {
            _HOUSE_OF_COMEDY_BLOOMINGTON_HOST,
            _ST_MARKS_COMEDY_HOST,
        }:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        events: List[TixrEvent] = []
        seen_ids: set[str] = set()

        for item in soup.select(".event-item"):
            link = item.select_one('a.ticket-links[href*="tixr.com"]')
            title_el = item.select_one(".text-block-35")
            month_el = item.select_one(".date-info .month.grid:not(.date):not(.custom-filter)")
            day_el = item.select_one(".date-info .month.day.grid")
            time_el = item.select_one(".date-info .month.day.time")

            if not all((link, title_el, month_el, day_el, time_el)):
                continue

            ticket_url = str(link.get("href") or "").strip()
            title = title_el.get_text(" ", strip=True)
            event_id = TixrExtractor.get_event_id(ticket_url) or ""
            if not title or not ticket_url or (event_id and event_id in seen_ids):
                continue

            show_date = self._parse_public_card_datetime(
                month_el.get_text(" ", strip=True),
                day_el.get_text(" ", strip=True),
                time_el.get_text(" ", strip=True),
            )
            if show_date is None:
                Logger.warn(
                    f"{self._log_prefix}: Skipping public card with unparseable date/time "
                    f"for '{title}' at {ticket_url}",
                    self.logger_context,
                )
                continue

            if event_id:
                seen_ids.add(event_id)

            show = Show(
                name=title,
                club_id=self.club.id,
                date=show_date,
                show_page_url=ticket_url,
                lineup=[],
                tickets=[
                    Ticket(
                        price=None,
                        purchase_url=ticket_url,
                        sold_out=False,
                        type="General Admission",
                    )
                ],
                supplied_tags=["event"],
                description=None,
                timezone=self.club.timezone,
                room="",
            )
            events.append(TixrEvent.from_tixr_show(show=show, source_url=ticket_url, event_id=event_id))

        return events

    def _parse_public_card_datetime(self, month_text: str, day_text: str, time_text: str) -> Optional[datetime]:
        timezone_name = self.club.timezone or "UTC"
        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)

        month_num: Optional[int] = None
        for month_format in _MONTH_FORMATS:
            try:
                month_num = datetime.strptime(month_text.strip(), month_format).month
                break
            except ValueError:
                continue

        if month_num is None:
            return None

        try:
            day_num = int(day_text.strip())
        except ValueError:
            return None

        parsed_time = None
        normalized_time = time_text.strip().upper()
        for time_format in _TIME_FORMATS:
            try:
                parsed_time = datetime.strptime(normalized_time, time_format).time()
                break
            except ValueError:
                continue

        if parsed_time is None:
            return None

        candidate = tz.localize(
            datetime(
                now.year,
                month_num,
                day_num,
                parsed_time.hour,
                parsed_time.minute,
            )
        )
        if candidate < now:
            next_year = tz.localize(
                datetime(
                    now.year + 1,
                    month_num,
                    day_num,
                    parsed_time.hour,
                    parsed_time.minute,
                )
            )
            if (next_year - now).days > _MAX_YEAR_ROLLOVER_DAYS:
                return None
            candidate = next_year
        return candidate
