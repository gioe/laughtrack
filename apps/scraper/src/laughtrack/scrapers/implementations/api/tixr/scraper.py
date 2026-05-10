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
import os
import re
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
from .webflow_day_card import (
    WebflowDayCardConfig,
    WebflowDayCardExtractor,
    WebflowDayCardPageData,
    WebflowDayCardTransformer,
)

_MAX_DISCOVERY_PAGES = 12
_IMPROV_ASYLUM_PIXL_EVENTS_URL = "https://calendar.improvasylum.com/api/events/improv-asylum"
_GROUP_EVENTS_API_FLAG = "TIXR_GROUP_EVENTS_API_FALLBACK"
_MONTH_FORMATS = ("%b", "%B")
_TIME_FORMATS = ("%I:%M %p", "%I %p")
_MAX_YEAR_ROLLOVER_DAYS = 180
_STAND_SHOW_PATH_RE = re.compile(
    r"/shows/show/\d+/(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})"
)


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
                fallback_events = await self._fetch_group_api_events_if_enabled(url)
                if fallback_events:
                    Logger.info(
                        f"{self._log_prefix}: Parsed {len(fallback_events)} events from Tixr group-events API "
                        "fallback after group-page fetch returned no HTML",
                        self.logger_context,
                    )
                    return TixrPageData(event_list=fallback_events)

                fallback_events = await self._fetch_improv_asylum_pixl_events(url)
                if fallback_events:
                    Logger.info(
                        f"{self._log_prefix}: Parsed {len(fallback_events)} events from Improv Asylum Pixl Calendar "
                        "fallback after Tixr group-page fetch returned no HTML",
                        self.logger_context,
                    )
                    return TixrPageData(event_list=fallback_events)

                Logger.info(f"{self._log_prefix}: No HTML content returned from {url}", self.logger_context)
                return None

            all_tixr_urls = TixrExtractor.extract_tixr_urls(html_content)

            if not all_tixr_urls:
                fallback_events = await self._fetch_group_api_events_if_enabled(url)
                if fallback_events:
                    Logger.info(
                        f"{self._log_prefix}: Parsed {len(fallback_events)} events from Tixr group-events API "
                        "fallback after group-page extraction returned no URLs",
                        self.logger_context,
                    )
                    return TixrPageData(event_list=fallback_events)

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

    async def _fetch_group_api_events_if_enabled(self, url: str) -> List[TixrEvent]:
        if not self._group_events_api_fallback_enabled():
            return []

        group_id = (
            self.club.metadata_value("tixr_group_id")
            or self.club.metadata_value("tixr_group_slug")
            or self._group_slug_from_url(url)
            or ""
        ).strip()
        if not group_id:
            Logger.warn(
                f"{self._log_prefix}: Tixr group-events API fallback is enabled but "
                "no tixr_group_id metadata, tixr_group_slug metadata, or URL group slug is available",
                self.logger_context,
            )
            return []

        return await self.tixr_client.fetch_group_events(group_id)

    def _group_events_api_fallback_enabled(self) -> bool:
        metadata_value = (self.club.source_metadata or {}).get("tixr_group_events_api_fallback")
        if isinstance(metadata_value, bool):
            return metadata_value
        if isinstance(metadata_value, str):
            return metadata_value.strip().lower() in {"1", "true", "yes", "on"}

        raw = os.environ.get(_GROUP_EVENTS_API_FLAG, "")
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _group_slug_from_url(url: str) -> Optional[str]:
        parsed = urlparse(URLUtils.normalize_url(url))
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")

        match = re.search(r"(?:^|/)groups/([^/?#]+)", parsed.path)
        if match:
            return match.group(1)

        if host.endswith(".tixr.com") and host != "www.tixr.com":
            return host.split(".", 1)[0]

        if path:
            return path.split("/", 1)[0]
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

    def _parse_public_calendar_events(self, html_content: str) -> List[TixrEvent]:
        """Parse venue-owned public cards that carry complete event data.

        Tries Webflow-style cards first (Bloomington, St Marks); if none
        match, falls through to The Stand NYC's Bootstrap-style ``.show_row``
        layout. Each format returns events from its own selectors and an
        empty list when the HTML doesn't match, so the union is safe.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        events = self._parse_webflow_public_cards(soup)
        if events:
            return events
        return self._parse_stand_public_cards(soup)

    def _parse_webflow_public_cards(self, soup: BeautifulSoup) -> List[TixrEvent]:
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

    def _parse_stand_public_cards(self, soup: BeautifulSoup) -> List[TixrEvent]:
        """Parse The Stand NYC's Bootstrap-style ``.show_row`` cards.

        The title link's href encodes a ``/shows/show/<id>/<YYYY-MM-DD>-<HHMMSS>-...``
        slug — that is the source of truth for date/time. The Tixr ticket URL
        lives on ``a.btn-stand``; sold-out shows replace the buy button with a
        ``span.btn-outline-danger`` and are skipped (no Tixr URL means the
        Tixr API path can't reach them either).
        """
        events: List[TixrEvent] = []
        seen_ids: set[str] = set()

        for row in soup.select(".show_row"):
            title_el = row.select_one("h2.showtitle a")
            buy_btn = row.select_one('a.btn-stand[href*="tixr.com"]')
            if not title_el or not buy_btn:
                continue

            title = title_el.get_text(" ", strip=True)
            title_href = str(title_el.get("href") or "")
            ticket_url = str(buy_btn.get("href") or "").strip()
            if not title or not ticket_url:
                continue

            event_id = TixrExtractor.get_event_id(ticket_url) or ""
            if event_id and event_id in seen_ids:
                continue

            show_date = self._parse_stand_show_datetime(title_href)
            if show_date is None:
                Logger.warn(
                    f"{self._log_prefix}: Skipping Stand card with unparseable show URL "
                    f"for '{title}' at {ticket_url} (href={title_href!r})",
                    self.logger_context,
                )
                continue

            if event_id:
                seen_ids.add(event_id)

            room_el = row.select_one(".list-show-room") or row.select_one(".list-show-room-new")
            room = room_el.get_text(" ", strip=True) if room_el else ""

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
                room=room,
            )
            events.append(TixrEvent.from_tixr_show(show=show, source_url=ticket_url, event_id=event_id))

        return events

    def _parse_stand_show_datetime(self, href: str) -> Optional[datetime]:
        """Extract a localized datetime from The Stand's `/shows/show/<id>/<YYYY-MM-DD>-<HHMMSS>-...` path."""
        match = _STAND_SHOW_PATH_RE.search(href)
        if not match:
            return None
        try:
            year, month, day, hour, minute, second = (int(g) for g in match.groups())
            tz = pytz.timezone(self.club.timezone or "America/New_York")
            return tz.localize(datetime(year, month, day, hour, minute, second))
        except (ValueError, pytz.UnknownTimeZoneError):
            return None

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


class TixrPublicCardScraper(TixrScraper):
    """
    Scraper for venue-owned public calendar cards that link to Tixr tickets.

    Unlike ``TixrScraper``, this key never fetches Tixr-hosted event detail
    pages. It is for venue pages whose cards already expose title, date/time,
    and ticket URL, making Tixr only the ticket URL provider.
    """

    key = "tixr_public_card"

    async def get_data(self, url: str) -> Optional[TixrPageData]:
        normalized_url = URLUtils.normalize_url(str(url))
        try:
            parsed = urlparse(normalized_url)
            if "tixr.com" in parsed.netloc.lower():
                Logger.warn(
                    f"{self._log_prefix}: tixr_public_card requires a venue-owned source URL, got {normalized_url}",
                    self.logger_context,
                )
                return None

            html_content = await self.fetch_html(normalized_url)
            if not html_content:
                Logger.info(
                    f"{self._log_prefix}: No HTML content returned from public-card source {normalized_url}",
                    self.logger_context,
                )
                return None

            events = self._parse_public_calendar_events(html_content)
            if not events:
                tixr_url_count = len(TixrExtractor.extract_tixr_urls(html_content))
                Logger.warn(
                    f"{self._log_prefix}: Found {tixr_url_count} Tixr URL(s) but no parseable "
                    f"venue-owned public cards at {normalized_url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: Parsed {len(events)} events from venue-owned public cards on {normalized_url}; "
                "Tixr detail pages were not fetched",
                self.logger_context,
            )
            return TixrPageData(event_list=events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting public-card data from {normalized_url}: {str(e)}",
                self.logger_context,
            )
            return None


class TixrWebflowDayCardScraper(BaseScraper):
    """Generic scraper for Webflow ``a.day-card`` calendars with Tixr ticket links.

    Reads the venue homepage URL from ``scraping_sources.source_url`` and the
    Tixr group URL fragment used to filter foreign cards from
    ``scraping_sources.metadata.tixr_group_fragment``. Onboarding a new venue
    that follows the same Webflow + Tixr pattern is a DB-only change.
    """

    key = "tixr_webflow_day_card"

    def __init__(self, club: Club, **kwargs):
        fragment = (club.metadata_value("tixr_group_fragment") or "").strip()
        if not fragment:
            raise ValueError(
                f"TixrWebflowDayCardScraper requires "
                f"scraping_sources.metadata.tixr_group_fragment for "
                f"club_id={club.id} ('{club.name}')"
            )
        if not (club.scraping_url or "").strip():
            raise ValueError(
                f"TixrWebflowDayCardScraper requires "
                f"scraping_sources.source_url for "
                f"club_id={club.id} ('{club.name}')"
            )

        self.config = WebflowDayCardConfig(tixr_group_fragment=fragment)
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(WebflowDayCardTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return [self.club.scraping_url]

    async def get_data(self, target: ScrapingTarget) -> Optional[WebflowDayCardPageData]:
        url = str(target or self.club.scraping_url)
        html_content = await self.fetch_html(url)
        if not html_content:
            Logger.warn(
                f"{self._log_prefix}: empty Webflow homepage response: {url}",
                self.logger_context,
            )
            return None

        events = WebflowDayCardExtractor.extract_events(
            html_content, source_url=url, config=self.config
        )
        if not events:
            Logger.warn(
                f"{self._log_prefix}: no Webflow event cards matched "
                f"fragment={self.config.tixr_group_fragment!r} at {url}",
                self.logger_context,
            )
            return None

        return WebflowDayCardPageData(event_list=events)
