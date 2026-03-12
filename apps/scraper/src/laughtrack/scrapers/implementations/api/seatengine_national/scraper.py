"""
SeatEngineNationalScraper: enumerates all comedy venues registered on
SeatEngine and upserts them into the clubs table.

No per-venue scraper changes are needed — after enumeration the existing
SeatEngineScraper (key='seatengine') automatically picks up newly registered
venues on the next scraping run.

Triggered by a single clubs row with scraper='seatengine_national'.
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper


class SeatEngineNationalScraper(BaseScraper):
    """
    Platform-level SeatEngine scraper that enumerates comedy venues
    nationally (no per-venue ID required).

    Triggered by a single clubs row with scraper='seatengine_national'.
    Discovers venues via the SeatEngine venues API, upserts club rows for
    newly-seen venues, and returns an empty show list (enumeration only).
    """

    key = "seatengine_national"

    _BASE_API_URL = "https://services.seatengine.com/api/v1"
    _AUTH_TOKEN = "3c7de746-6bc2-4efb-8e91-16da6155edce"
    _REQUEST_TIMEOUT = 30
    _MAX_PAGES = 50

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        self._headers = BaseHeaders.get_headers(
            base_type="mobile_browser",
            auth_type="seat_engine",
            auth_token=self._AUTH_TOKEN,
            domain="services.seatengine.com",
        )

    # ------------------------------------------------------------------ #
    # BaseScraper pipeline                                                 #
    # ------------------------------------------------------------------ #

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target representing the national venue directory."""
        return ["national"]

    async def get_data(self, target: str) -> None:
        """Not used: scrape_async is fully overridden for enumeration logic."""
        return None  # pragma: no cover

    async def scrape_async(self) -> List[Show]:
        """Override: discover SeatEngine venues, upsert clubs. Returns no shows."""
        try:
            venues = await self._fetch_seatengine_venues()
            if not venues:
                Logger.info(
                    "SeatEngineNational: no venues returned from directory",
                    self.logger_context,
                )
                return []

            Logger.info(
                f"SeatEngineNational: discovered {len(venues)} venues",
                self.logger_context,
            )
            await self._upsert_venues(venues)
            return []
        except Exception as e:
            Logger.error(f"SeatEngineNationalScraper failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _fetch_seatengine_venues(self) -> list:
        """Paginate through SeatEngine's venue directory API."""
        venues: list = []
        page = 1

        while page <= self._MAX_PAGES:
            url = f"{self._BASE_API_URL}/venues?page={page}"
            data = await self.fetch_json(url, headers=self._headers, timeout=self._REQUEST_TIMEOUT)
            if not data:
                break

            page_venues = data.get("data", [])
            if not page_venues:
                break

            venues.extend(page_venues)

            meta = data.get("meta", {})
            last_page = (meta or {}).get("last_page", page)
            if page >= last_page:
                break
            page += 1

        if page > self._MAX_PAGES:
            Logger.warn(
                f"SeatEngineNational: reached MAX_PAGES ({self._MAX_PAGES}) — pagination truncated",
                self.logger_context,
            )

        return venues

    async def _upsert_venues(self, venues: list) -> None:
        """Upsert each discovered venue as a clubs row."""
        loop = asyncio.get_running_loop()
        inserted = 0
        skipped = 0

        for venue in venues:
            venue_id = str(venue.get("id", "")).strip()
            if not venue_id:
                skipped += 1
                continue
            try:
                club = await loop.run_in_executor(
                    None, self._club_handler.upsert_for_seatengine_venue, venue
                )
                if club:
                    inserted += 1
                    Logger.info(
                        f"SeatEngineNational: upserted club '{club.name}' (seatengine_id={venue_id})",
                        self.logger_context,
                    )
                else:
                    skipped += 1
            except Exception as exc:
                Logger.error(
                    f"SeatEngineNational: failed to upsert venue {venue_id}: {exc}",
                    self.logger_context,
                )
                skipped += 1

        Logger.info(
            f"SeatEngineNational: enumeration complete — {inserted} upserted, {skipped} skipped",
            self.logger_context,
        )
