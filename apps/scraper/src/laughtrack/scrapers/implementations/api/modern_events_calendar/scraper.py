"""Generic scraper for WordPress Modern Events Calendar sites.

Modern Events Calendar stores events as the ``mec-events`` custom post type and
exposes a WordPress REST collection at ``/wp-json/wp/v2/mec-events``. The public
REST payload does not include event datetimes on all sites, but each event detail
page renders schema.org Event JSON-LD with start/end dates and ticket offers.
This scraper uses the REST collection as the index and JSON-LD detail pages as
the canonical event source.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent, Offer, Place, PostalAddress
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.data import JsonLdPageData
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer

_DEFAULT_PER_PAGE = 20
_DEFAULT_MAX_PAGES = 3
_DEFAULT_MAX_DETAIL_PAGES = 60


class ModernEventsCalendarScraper(BaseScraper):
    """Scraper for Modern Events Calendar WordPress REST + JSON-LD detail pages."""

    key = "modern_events_calendar"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def get_data(self, url: str) -> Optional[JsonLdPageData]:
        """Fetch MEC REST pages, then parse JSON-LD from each event detail page."""
        event_urls = await self._collect_event_urls(url)
        if not event_urls:
            self._warn_empty_extraction(url, extra={"source": "mec-events REST"})
            return None

        events: list[JsonLdEvent] = []
        max_details = self._metadata_int("max_detail_pages", _DEFAULT_MAX_DETAIL_PAGES)
        for event_url in event_urls[:max_details]:
            html = await self._fetch_detail_html(event_url)
            if not html:
                continue
            extracted = EventExtractor.extract_events(
                html,
                same_as_override=event_url if self._set_same_as_to_detail_url() else None,
            )
            future_events = [event for event in extracted if self._is_future_event(event)]
            if not future_events:
                fallback_event = self._extract_mec_html_event(html, event_url)
                if fallback_event and self._is_future_event(fallback_event):
                    future_events.append(fallback_event)
            events.extend(future_events)

        if not events:
            self._warn_empty_extraction(
                url,
                extra={"detail_pages": min(len(event_urls), max_details)},
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} future MEC JSON-LD events "
            f"from {min(len(event_urls), max_details)} detail pages",
            self.logger_context,
        )
        return JsonLdPageData(event_list=events)

    async def _collect_event_urls(self, source_url: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        max_pages = self._metadata_int("max_pages", _DEFAULT_MAX_PAGES)
        per_page = self._metadata_int("per_page", _DEFAULT_PER_PAGE)

        for page in range(1, max_pages + 1):
            api_url = self._with_query_params(
                source_url,
                {
                    "per_page": str(per_page),
                    "page": str(page),
                    "status": "publish",
                },
            )
            payload = await self.fetch_json(api_url)
            if not payload:
                break
            if isinstance(payload, dict):
                if payload.get("code") == "rest_post_invalid_page_number":
                    break
                Logger.warn(
                    f"{self._log_prefix}: unexpected MEC REST payload type dict from {api_url}",
                    self.logger_context,
                )
                break
            if not isinstance(payload, list):
                Logger.warn(
                    f"{self._log_prefix}: unexpected MEC REST payload type "
                    f"{type(payload).__name__} from {api_url}",
                    self.logger_context,
                )
                break
            if not payload:
                break

            for raw in payload:
                if not isinstance(raw, dict):
                    continue
                event_url = str(raw.get("link") or "").strip()
                if event_url and event_url not in seen:
                    seen.add(event_url)
                    urls.append(event_url)

            if len(payload) < per_page:
                break

        Logger.info(
            f"{self._log_prefix}: collected {len(urls)} MEC detail URLs from {source_url}",
            self.logger_context,
        )
        return urls

    async def _fetch_detail_html(self, url: str) -> Optional[str]:
        if self._force_js_rendering():
            return await self._fetch_html_with_js(url)
        return await self.fetch_html(url)

    def _force_js_rendering(self) -> bool:
        return bool((self.club.source_metadata or {}).get("force_js_rendering"))

    def _set_same_as_to_detail_url(self) -> bool:
        return (self.club.source_metadata or {}).get("set_same_as_to_detail_url") is not False

    def _extract_mec_html_event(self, html: str, detail_url: str) -> Optional[JsonLdEvent]:
        """Parse a Modern Events Calendar detail page when Event JSON-LD is absent."""
        soup = BeautifulSoup(html or "", "html.parser")
        title = self._text_from_first(soup, [".mec-single-title", "h1"])
        date_text = self._text_from_first(soup, [".mec-single-event-date"])
        time_text = self._text_from_first(soup, [".mec-single-event-time"])
        start_date = self._parse_mec_datetime(date_text, time_text)
        if not title or start_date is None:
            return None

        ticket_url = self._href_from_first(
            soup,
            [
                ".mec-booking-button",
                ".mec-events-event-more-info a",
                ".mec-event-more-info a",
            ],
        )
        event_url = ticket_url or detail_url
        price = self._parse_price(self._text_from_first(soup, [".mec-events-event-cost", ".mec-event-cost"]))
        offers = [
            Offer(
                url=event_url,
                price_currency="USD",
                price=price or "",
                availability="https://schema.org/InStock",
                name="General Admission",
            )
        ]

        return JsonLdEvent(
            name=title,
            start_date=start_date,
            location=Place(
                name=self.club.name,
                address=PostalAddress(
                    street_address=self.club.address or "",
                    address_locality=self.club.city or "",
                    address_region=self.club.state or "",
                    postal_code=self.club.zip_code or "",
                    address_country="US",
                ),
            ),
            offers=offers,
            url=event_url,
            description=self._text_from_first(
                soup,
                [".mec-single-event-description", ".mec-events-content"],
            ),
            same_as=detail_url if self._set_same_as_to_detail_url() else None,
        )

    def _parse_mec_datetime(self, date_text: str, time_text: str) -> Optional[datetime]:
        date_match = re.search(r"\b([A-Z][a-z]{2,8})\s+(\d{1,2})\s+(\d{4})\b", date_text or "")
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)\b", time_text or "", re.IGNORECASE)
        if not date_match:
            return None

        date_part = " ".join(date_match.groups())
        try:
            parsed_date = datetime.strptime(date_part, "%b %d %Y")
        except ValueError:
            try:
                parsed_date = datetime.strptime(date_part, "%B %d %Y")
            except ValueError:
                return None

        hour = 0
        minute = 0
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or "0")
            meridiem = time_match.group(3).lower().replace(".", "")
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

        timezone = self.club.timezone or "America/New_York"
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("America/New_York")
        return parsed_date.replace(hour=hour, minute=minute, tzinfo=tz)

    @staticmethod
    def _text_from_first(soup: BeautifulSoup, selectors: list[str]) -> str:
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _href_from_first(soup: BeautifulSoup, selectors: list[str]) -> str:
        for selector in selectors:
            node = soup.select_one(selector)
            if node and node.get("href"):
                return str(node["href"]).strip()
        return ""

    @staticmethod
    def _parse_price(raw: str) -> str:
        match = re.search(r"\d+(?:\.\d{1,2})?", (raw or "").replace(",", ""))
        return match.group(0) if match else ""

    def _metadata_int(self, key: str, default: int) -> int:
        raw = (self.club.source_metadata or {}).get(key)
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _is_future_event(event: JsonLdEvent) -> bool:
        event_date = event.start_date
        now = datetime.now(event_date.tzinfo) if event_date.tzinfo else datetime.now()
        return event_date >= now

    @staticmethod
    def _with_query_params(url: str, params: dict[str, str]) -> str:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(params)
        return urlunparse(parsed._replace(query=urlencode(query)))
