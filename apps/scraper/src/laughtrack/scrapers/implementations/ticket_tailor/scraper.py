"""Ticket Tailor (tickettailor.com) box-office scraper.

Ticket Tailor accounts are commonly roving producers — one box office selling
shows at many physical venues. This scraper runs in production-company mode:
the orchestrator builds a synthetic proxy Club for the company (see
``_build_synthetic_proxy_for_company`` in services/scraping), and this scraper
groups the listing's events by their per-event venue, upserts one ``clubs`` row
per distinct venue via ``ClubHandler.upsert_discovered_venue``, and emits each
event as a Show whose ``club_id`` points at the per-venue club. The orchestrator
then stamps ``production_company_id`` on every resulting Show.

Anti-bot: tickettailor.com sits behind Cloudflare, which 403s a plain request.
A curl_cffi ``impersonate='chrome120'`` session plus a ``Referer`` header (the
producer's own website) clears it.
"""

import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ticket_tailor import TicketTailorEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.database.write_lock import serialized_db_call
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .extractor import (
    extract_account_slug,
    extract_events,
    listing_url_for_account,
)

_FETCH_TIMEOUT = 30
_DEFAULT_REFERER = "https://www.tickettailor.com/"


class TicketTailorScraper(BaseScraper):
    """Roving-producer scraper for tickettailor.com box offices."""

    key = "ticket_tailor"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()

    def _listing_url(self) -> Optional[str]:
        slug = (self.club.source_metadata or {}).get("account_slug")
        if slug:
            return listing_url_for_account(str(slug))
        url = self.club.scraping_url or ""
        if url:
            return url
        return None

    def _referer(self) -> str:
        """Referer header that clears Cloudflare — the producer's own website."""
        return self.club.website or _DEFAULT_REFERER

    async def _fetch_listing(self, url: str) -> Optional[str]:
        """Fetch listing HTML with curl_cffi impersonation + Referer (Cloudflare)."""
        headers = {"Referer": self._referer()}
        try:
            async with AsyncSession(impersonate="chrome120", timeout=_FETCH_TIMEOUT) as session:
                response = await session.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Ticket Tailor fetch failed for {url}: {e}", self.logger_context)
            return None

    async def get_data(self, target: ScrapingTarget) -> None:
        """Unused: this scraper only runs in production-company mode via
        scrape_async, which routes each event to its own venue club. The
        abstract method is satisfied here but never reached."""
        return None

    async def scrape_async(self) -> List[Show]:
        listing_url = self._listing_url()
        if not listing_url:
            Logger.warn(
                f"{self._log_prefix}: no account_slug metadata or scraping_url configured",
                self.logger_context,
            )
            return []

        html = await self._fetch_listing(listing_url)
        if not html:
            self._warn_empty_extraction(listing_url, html=html)
            return []

        events = extract_events(html)
        if not events:
            self._warn_empty_extraction(listing_url, subject="events", html=html)
            return []

        Logger.info(
            f"{self._log_prefix}: parsed {len(events)} Ticket Tailor event(s)",
            self.logger_context,
        )
        if self._single_venue_mode():
            return self._events_to_current_club(events)
        return await self._route_events_to_venues(events)

    def _single_venue_mode(self) -> bool:
        """Attach every listing event to the configured club.

        Ticket Tailor accounts are usually roving producers, so the default
        route still groups by each card's venue. Some accounts, including West
        River, are a single physical venue whose own box office carries the
        complete calendar. Those sources opt in through metadata so they avoid
        noisy discovered-venue upserts and keep all shows on the configured
        club row.
        """
        return bool((self.club.source_metadata or {}).get("single_venue"))

    def _events_to_current_club(self, events: List[TicketTailorEvent]) -> List[Show]:
        shows: List[Show] = []
        for event in events:
            try:
                show = event.to_show(self.club)
            except Exception as e:
                Logger.error(
                    f"{self._log_prefix}: to_show failed for '{event.title}': {e}",
                    self.logger_context,
                )
                continue
            if show:
                shows.append(show)

        Logger.info(
            f"{self._log_prefix}: built {len(shows)} show(s) for single-venue Ticket Tailor source",
            self.logger_context,
        )
        return shows

    async def _route_events_to_venues(self, events: List[TicketTailorEvent]) -> List[Show]:
        """Group events by venue, upsert one club per venue, build per-venue shows."""
        groups: Dict[Tuple[str, str], List[TicketTailorEvent]] = defaultdict(list)
        for event in events:
            key = (event.venue_name.strip().lower(), event.venue_zip.strip())
            if not key[0]:
                Logger.warn(
                    f"{self._log_prefix}: event '{event.title}' has no venue — skipping",
                    self.logger_context,
                )
                continue
            groups[key].append(event)

        loop = asyncio.get_running_loop()
        shows: List[Show] = []
        for (_name, _zip), group in groups.items():
            sample = group[0]
            venue_club = await self._upsert_venue(loop, sample)
            if venue_club is None:
                Logger.warn(
                    f"{self._log_prefix}: could not resolve venue '{sample.venue_name}' — "
                    f"skipping {len(group)} event(s)",
                    self.logger_context,
                )
                continue
            for event in group:
                try:
                    show = event.to_show(venue_club)
                except Exception as e:
                    Logger.error(
                        f"{self._log_prefix}: to_show failed for '{event.title}' "
                        f"at '{sample.venue_name}': {e}",
                        self.logger_context,
                    )
                    continue
                if show:
                    shows.append(show)

        Logger.info(
            f"{self._log_prefix}: built {len(shows)} show(s) across {len(groups)} venue(s)",
            self.logger_context,
        )
        return shows

    async def _upsert_venue(self, loop, event: TicketTailorEvent) -> Optional[Club]:
        venue = {
            "name": event.venue_name,
            "zip_code": event.venue_zip,
            "timezone": event.timezone,
        }
        try:
            return await loop.run_in_executor(
                None, serialized_db_call, self._club_handler.upsert_discovered_venue, venue
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: upsert_discovered_venue failed for '{event.venue_name}': {e}",
                self.logger_context,
            )
            return None
