"""
Generic SeatEngine white-label website scraper.

Some SeatEngine venues serve shows through a white-label frontend
(e.g., bananascomedyclub.com) while the SeatEngine v1 API returns 0 events.
This scraper bypasses the API entirely and scrapes the venue's own website:

1. Fetches the /events listing page to discover event detail URLs
2. Fetches each event detail page for its JSON-LD Event markup
3. Reuses the standard JsonLd extraction and transformation pipeline

To onboard a new club: set scraper='seatengine_web' and scraping_url to
the venue's website root (e.g., 'https://www.bananascomedyclub.com').
No Python changes needed.
"""

import json
import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import Offer
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.implementations.json_ld.data import JsonLdPageData
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.shared.types import ScrapingTarget


class SeatEngineWebScraper(JsonLdScraper):
    """Scrapes SeatEngine white-label sites via their /events listing page."""

    key = "seatengine_web"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Fetch the /events page and extract individual event page URLs."""
        events_url = f"{self.club.scraping_url.rstrip('/')}/events"
        html = await self.fetch_html(events_url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: could not fetch events listing at {events_url}",
                self.logger_context,
            )
            return []

        event_ids = sorted(set(re.findall(r'/events/(\d+)', html)))
        if not event_ids:
            Logger.warn(
                f"{self._log_prefix}: no event links found on {events_url}",
                self.logger_context,
            )
            return []

        base = self.club.scraping_url.rstrip("/")
        targets = [f"{base}/events/{eid}" for eid in event_ids]
        Logger.info(
            f"{self._log_prefix}: discovered {len(targets)} event pages to scrape",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[JsonLdPageData]:
        """Extract JSON-LD events and enrich them from SeatEngine cart config."""
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)

            event_list = EventExtractor.extract_events(html_content)
            if not event_list:
                if html_content:
                    Logger.warn(
                        f"{self._log_prefix}: Page loaded but contained no JSON-LD events: {normalized_url}",
                        self.logger_context,
                    )
                return None

            offers = self._extract_offers_from_app_config(html_content, normalized_url)
            if offers:
                for event in event_list:
                    if not event.offers:
                        event.offers = offers

            return JsonLdPageData(event_list)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None

    @classmethod
    def _extract_offers_from_app_config(cls, html: str, event_url: str) -> List[Offer]:
        """Extract ticket tiers from SeatEngine's embedded cart configuration."""
        config = cls._parse_app_config(html)
        if not config:
            return cls._sold_out_fallback_offer(html, event_url)

        showtime = config.get("showtime")
        if not isinstance(showtime, dict):
            return cls._sold_out_fallback_offer(html, event_url)

        inventories = showtime.get("inventories") or []
        sold_out = bool(showtime.get("sold_out"))
        if not isinstance(inventories, list):
            inventories = []

        offers: List[Offer] = []
        for inventory in inventories:
            if not isinstance(inventory, dict):
                continue

            available = int(inventory.get("available") or 0)
            price_cents = int(inventory.get("price") or 0)
            service_charge_cents = int(inventory.get("service_charge") or 0)
            all_in_price = (price_cents + service_charge_cents) / 100
            availability = "https://schema.org/SoldOut" if sold_out or available <= 0 else "https://schema.org/InStock"
            ticket_type = inventory.get("title") or inventory.get("name") or "General Admission"

            offers.append(
                Offer(
                    url=event_url,
                    price_currency="USD",
                    price=f"{all_in_price:.2f}",
                    availability=availability,
                    name=str(ticket_type),
                )
            )

        if not offers and sold_out:
            offers.append(
                Offer(
                    url=event_url,
                    price_currency="USD",
                    price="0.00",
                    availability="https://schema.org/SoldOut",
                    name="General Admission",
                )
            )

        return offers or cls._sold_out_fallback_offer(html, event_url)

    @staticmethod
    def _sold_out_fallback_offer(html: str, event_url: str) -> List[Offer]:
        if not re.search(r">\s*Currently\s*<br\s*/?>\s*Sold\s+Out\s*<", html, re.IGNORECASE):
            return []

        return [
            Offer(
                url=event_url,
                price_currency="USD",
                price="0.00",
                availability="https://schema.org/SoldOut",
                name="General Admission",
            )
        ]

    @staticmethod
    def _parse_app_config(html: str) -> Optional[dict]:
        marker = "window.seat_engine_app_config ="
        start = html.find(marker)
        if start == -1:
            return None

        json_start = html.find("{", start + len(marker))
        if json_start == -1:
            return None

        try:
            config, _ = json.JSONDecoder().raw_decode(html[json_start:])
        except json.JSONDecodeError:
            return None

        return config if isinstance(config, dict) else None
