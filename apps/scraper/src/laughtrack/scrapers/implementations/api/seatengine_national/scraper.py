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
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.scrapers.base.base_scraper import BaseScraper


class SeatEngineNationalScraper(BaseScraper):
    """
    Platform-level SeatEngine scraper that enumerates comedy venues
    nationally (no per-venue ID required).

    Triggered by a single clubs row with scraper='seatengine_national'.
    Discovers venues via the SeatEngine venues API, upserts club rows for
    newly-seen venues, and returns an empty show list (enumeration only).

    The directory listing endpoint (/api/v1/venues?page=N) returns HTTP 500
    (Server Error) — a SeatEngine API defect.  This scraper works around it
    by scanning per-venue IDs 1…_venue_scan_max_id concurrently.
    """

    key = "seatengine_national"

    _BASE_API_URL = "https://services.seatengine.com/api/v1"
    _REQUEST_TIMEOUT = 30
    _MAX_CONCURRENT_REQUESTS = 20

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()
        auth_token = ConfigManager.get_config("api", "seatengine_auth_token")
        self._venue_scan_max_id: int = ConfigManager.get_config(
            "api", "seatengine_venue_scan_max_id", 700
        )
        self._headers = BaseHeaders.get_headers(
            base_type="mobile_browser",
            auth_type="seat_engine",
            auth_token=auth_token,
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
                    f"{self._log_prefix}: no venues returned from directory",
                    self.logger_context,
                )
                return []

            Logger.info(
                f"{self._log_prefix}: discovered {len(venues)} venues",
                self.logger_context,
            )
            await self._upsert_venues(venues)
            return []
        except Exception as e:
            Logger.error(f"{self._log_prefix}: failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _fetch_seatengine_venues(self) -> list:
        """
        Enumerate SeatEngine venues via concurrent per-venue API calls.

        The directory listing endpoint (/api/v1/venues?page=N) always returns
        HTTP 500 (Server Error) — a SeatEngine API defect.  As a workaround,
        scan venue IDs 1…_venue_scan_max_id in parallel and collect any record
        that has a non-empty ``name`` field.  Unknown IDs return
        ``{"data": null}`` (HTTP 200) and are silently skipped.
        """
        semaphore = asyncio.Semaphore(self._MAX_CONCURRENT_REQUESTS)

        async def _fetch_one(venue_id: int) -> Optional[dict]:
            async with semaphore:
                url = f"{self._BASE_API_URL}/venues/{venue_id}"
                try:
                    data = await self.fetch_json(
                        url, headers=self._headers, timeout=self._REQUEST_TIMEOUT
                    )
                    if not data:
                        return None
                    venue = data.get("data")
                    if not venue or not venue.get("name"):
                        return None
                    return venue
                except Exception as exc:
                    Logger.warn(
                        f"{self._log_prefix}: error fetching venue {venue_id}: {exc}",
                        self.logger_context,
                    )
                    return None

        tasks = [_fetch_one(vid) for vid in range(1, self._venue_scan_max_id + 1)]
        results = await asyncio.gather(*tasks)
        return [v for v in results if v is not None]

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
                        f"{self._log_prefix}: upserted club '{club.name}' (seatengine_id={venue_id})",
                        self.logger_context,
                    )
                else:
                    skipped += 1
            except Exception as exc:
                Logger.error(
                    f"{self._log_prefix}: failed to upsert venue {venue_id}: {exc}",
                    self.logger_context,
                )
                skipped += 1

        Logger.info(
            f"{self._log_prefix}: enumeration complete — {inserted} upserted, {skipped} skipped",
            self.logger_context,
        )
