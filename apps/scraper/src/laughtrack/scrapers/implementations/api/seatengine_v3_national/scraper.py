"""
SeatEngineV3NationalScraper: discovers comedy venues registered on the
SeatEngine v3 platform (UUID-based GraphQL API) and upserts them into
the clubs table.

No per-venue scraper changes are needed — after discovery the existing
SeatEngineV3Scraper (key='seatengine_v3') automatically picks up newly
registered venues on the next scraping run.

Triggered by a single clubs row with scraper='seatengine_v3_national'.

Discovery approach — BLOCKED (2026-03-23)
-----------------------------------------
The v3 GraphQL API at services.seatengine.com/api/v3/public does NOT expose
a ``venuesList`` query.  Introspection confirmed the full query list is:

    cart, checkout, currentUser, event, eventsList, getPaymentIntent,
    healthcheck, purchase, purchaseTransaction, seatmap, venue, venueCustomer

The closest candidates for venue lookup are:
- ``venue(venueUuid: UUID4!)``       — single-venue lookup, UUID required
- ``venueCustomer(venueId: UUID4)``  — customer-facing details, UUID required

Neither supports listing all venues without a known UUID.  The ``eventsList``
query also requires a non-null ``venueUuid``.

Until a national discovery strategy is implemented (e.g. web scraping a
SeatEngine venue directory, or harvesting UUIDs from the v1 platform), this
scraper will always log a GraphQL error and return 0 venues.

See follow-up task for alternative discovery approaches.
"""

import asyncio
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

_V3_API_URL = "https://services.seatengine.com/api/v3/public"

# GraphQL query to list all venues registered in the SeatEngine v3 platform.
# Field selection follows the pattern of the eventsList query; optional fields
# (city, state, zipCode) are requested speculatively — missing fields are
# handled gracefully in the upsert handler.
_VENUES_LIST_QUERY = """
query GetVenuesList {
    venuesList {
        venues {
            uuid
            name
            address
            website
            zipCode
            city
            state
        }
    }
}
"""

_MAX_CONCURRENT_UPSERTS = 10


class SeatEngineV3NationalScraper(BaseScraper):
    """
    Platform-level scraper that discovers SeatEngine v3 venues nationally.

    Triggered by a single clubs row with scraper='seatengine_v3_national'.
    Discovers venues via the v3 GraphQL ``venuesList`` query, upserts club
    rows for newly-seen venues, and returns an empty show list (discovery
    only).

    Newly discovered clubs get:
      - scraper = 'seatengine_v3'
      - seatengine_id = <venue UUID>
      - scraping_url = https://v-<uuid>.seatengine.net
    """

    key = "seatengine_v3_national"

    _REQUEST_TIMEOUT = 30

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._club_handler = ClubHandler()

    # ------------------------------------------------------------------ #
    # BaseScraper pipeline                                                 #
    # ------------------------------------------------------------------ #

    async def collect_scraping_targets(self) -> List[str]:
        """Single logical target representing the national venue directory."""
        return ["national"]

    async def get_data(self, target: str) -> None:
        """Not used: scrape_async is fully overridden for discovery logic."""
        return None  # pragma: no cover

    async def scrape_async(self) -> List[Show]:
        """Override: discover SeatEngine v3 venues, upsert clubs. Returns no shows."""
        try:
            venues = await self._fetch_v3_venues()
            if not venues:
                Logger.info(
                    "SeatEngineV3National: no venues returned from venuesList query",
                    self.logger_context,
                )
                return []

            Logger.info(
                f"SeatEngineV3National: discovered {len(venues)} venues",
                self.logger_context,
            )
            await self._upsert_venues(venues)
            return []
        except Exception as e:
            Logger.error(f"SeatEngineV3NationalScraper failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _fetch_v3_venues(self) -> List[Dict[str, Any]]:
        """
        POST the ``venuesList`` GraphQL query to the v3 endpoint.

        Returns:
            List of venue dicts from the API, or [] on failure.
        """
        payload: Dict[str, Any] = {"query": _VENUES_LIST_QUERY}
        headers = {"Content-Type": "application/json"}
        try:
            response = await self.post_json(
                _V3_API_URL,
                data=payload,
                headers=headers,
                timeout=self._REQUEST_TIMEOUT,
            )
        except Exception as exc:
            Logger.warn(
                f"SeatEngineV3National: venuesList request failed: {exc}",
                self.logger_context,
            )
            return []

        if not response:
            Logger.warn(
                "SeatEngineV3National: empty response from venuesList query",
                self.logger_context,
            )
            return []

        if "errors" in response:
            Logger.warn(
                f"SeatEngineV3National: GraphQL errors from venuesList: {response['errors']}",
                self.logger_context,
            )
            return []

        venues = (
            response.get("data", {})
            .get("venuesList", {})
            .get("venues", [])
        )
        return venues if isinstance(venues, list) else []

    async def _upsert_venues(self, venues: List[Dict[str, Any]]) -> None:
        """Upsert each discovered venue as a clubs row (with scraper='seatengine_v3')."""
        loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_UPSERTS)
        inserted = 0
        skipped = 0

        async def _upsert_one(venue: dict) -> Optional[Club]:
            async with semaphore:
                return await loop.run_in_executor(
                    None, self._club_handler.upsert_for_seatengine_v3_venue, venue
                )

        tasks = [_upsert_one(v) for v in venues]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for venue, result in zip(venues, results):
            venue_uuid = (venue.get("uuid") or "").strip()
            if isinstance(result, Exception):
                Logger.error(
                    f"SeatEngineV3National: failed to upsert venue {venue_uuid}: {result}",
                    self.logger_context,
                )
                skipped += 1
            elif result is None:
                skipped += 1
            else:
                inserted += 1
                Logger.info(
                    f"SeatEngineV3National: upserted club '{result.name}' (uuid={venue_uuid})",
                    self.logger_context,
                )

        Logger.info(
            f"SeatEngineV3National: discovery complete — {inserted} upserted, {skipped} skipped",
            self.logger_context,
        )
