"""Combine The PIT's PatronTicket inventory with its WordPress event feed."""

from dataclasses import replace
import re
from typing import Optional

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.scrapers.implementations.venues.patron_ticket.scraper import (
    PatronTicketScraper,
)


_PATRONTICKET_SOURCE_URL_KEY = "patronticket_source_url"
_PATRONTICKET_VENUE_ID_KEY = "patronticket_venue_id"

# The WordPress descriptions use these phrases for cash-only events whose
# schema.org offers have no price. Keep the patterns intentionally narrow: a
# generic dollar matcher would turn food minimums and unrelated dollar amounts
# into ticket prices.
_CASH_PRICE_PATTERNS = (
    re.compile(
        r"\$(\d+(?:\.\d{1,2})?)\s+cash\b(?!\s+prize\b)",
        re.IGNORECASE,
    ),
    re.compile(r"\$(\d+(?:\.\d{1,2})?)\s+for\s+the\s+evening\b", re.IGNORECASE),
)


class ThePitScraper(JsonLdScraper):
    """Merge PIT online tickets with WordPress-only cash and community events."""

    key = "the_pit"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._patron_ticket_scraper = PatronTicketScraper(
            self._patron_ticket_club(club),
            proxy_pool=self.proxy_pool,
        )

    @staticmethod
    def _patron_ticket_club(club: Club) -> Club:
        metadata = club.source_metadata or {}
        source_url = str(metadata.get(_PATRONTICKET_SOURCE_URL_KEY) or "").strip()
        venue_id = metadata.get(_PATRONTICKET_VENUE_ID_KEY)

        if not source_url:
            raise ValueError(
                "ThePitScraper requires metadata.patronticket_source_url"
            )
        if not venue_id:
            raise ValueError(
                "ThePitScraper requires metadata.patronticket_venue_id"
            )

        active_source = club.scraping_source
        patron_ticket_source = ScrapingSource(
            id=active_source.id if active_source else None,
            club_id=club.id,
            platform="patron_ticket",
            scraper_key="patron_ticket",
            source_url=source_url,
            priority=active_source.priority if active_source else 0,
            metadata={
                _PATRONTICKET_VENUE_ID_KEY: venue_id,
                # PIT uses Improv, Variety, Theater, and blank categories for
                # valid shows, so the generic Comedy-only default is unsafe.
                "patronticket_categories": "*",
            },
        )
        return replace(
            club,
            scraping_sources=[patron_ticket_source],
            active_scraping_source=patron_ticket_source,
        )

    async def scrape_async(self) -> list[Show]:
        patron_ticket_shows = await self._scrape_patron_ticket()
        wordpress_shows = await self._scrape_wordpress()

        self._apply_cash_prices(wordpress_shows)

        # Keep PatronTicket first so an overlap retains its direct Salesforce
        # URL, allocation tiers, prices, and sold-out state. PIT's WordPress
        # JSON-LD occasionally emits local wall-clock values as UTC, making the
        # same show four hours earlier than PatronTicket. The Salesforce
        # instance URL is authoritative across that offset; date/room remains
        # the fallback identity for shows without an online instance.
        combined: list[Show] = []
        seen_keys: set[tuple] = set()
        seen_instances: set[str] = set()
        for show in [*patron_ticket_shows, *wordpress_shows]:
            key = show.to_unique_key()
            instances = self._patron_instance_urls(show)
            if key in seen_keys or instances & seen_instances:
                continue
            seen_keys.add(key)
            seen_instances.update(instances)
            combined.append(show)

        Logger.info(
            f"{self._log_prefix}: combined {len(patron_ticket_shows)} PatronTicket "
            f"and {len(wordpress_shows)} WordPress shows into {len(combined)} unique shows",
            self.logger_context,
        )
        return combined

    @staticmethod
    def _patron_instance_urls(show: Show) -> set[str]:
        return {
            ticket.purchase_url.rstrip("/")
            for ticket in show.tickets
            if ticket.purchase_url
            and "/ticket/#/instances/" in ticket.purchase_url.lower()
        }

    async def _scrape_patron_ticket(self) -> list[Show]:
        try:
            return await self._patron_ticket_scraper.scrape_async()
        except Exception as exc:
            self._record_child_failure()
            Logger.error(
                f"{self._log_prefix}: PatronTicket source failed: {exc}",
                self.logger_context,
            )
            return []

    async def _scrape_wordpress(self) -> list[Show]:
        try:
            return await super().scrape_async()
        except Exception as exc:
            self._record_child_failure()
            Logger.error(
                f"{self._log_prefix}: WordPress source failed: {exc}",
                self.logger_context,
            )
            return []

    @staticmethod
    def _record_child_failure() -> None:
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            # A partial union is useful enough to persist, but not trustworthy
            # enough to reconcile shows omitted by the failed child source.
            diagnostics.record_fetch_failed()

    @staticmethod
    def extract_cash_price(description: Optional[str]) -> Optional[float]:
        text = description or ""
        for pattern in _CASH_PRICE_PATTERNS:
            match = pattern.search(text)
            if match:
                return float(match.group(1))
        return None

    @classmethod
    def _apply_cash_prices(cls, shows: list[Show]) -> None:
        for show in shows:
            price = cls.extract_cash_price(show.description)
            if price is None or len(show.tickets) != 1:
                continue

            ticket = show.tickets[0]
            if ticket.price is None and ticket.type == "General Admission":
                ticket.price = price
