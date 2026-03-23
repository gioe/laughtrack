"""
SeatEngineV3NationalScraper: discovers comedy venues registered on the
SeatEngine v3 platform (UUID-based GraphQL API) and upserts them into
the clubs table.

No per-venue scraper changes are needed — after discovery the existing
SeatEngineV3Scraper (key='seatengine_v3') automatically picks up newly
registered venues on the next scraping run.

Triggered by a single clubs row with scraper='seatengine_v3_national'.

Discovery approach — Wayback Machine CDX + GraphQL venue query
--------------------------------------------------------------
The v3 GraphQL API at services.seatengine.com/api/v3/public does NOT expose
a ``venuesList`` query (confirmed via introspection 2026-03-23).  The full
query list is:

    cart, checkout, currentUser, event, eventsList, getPaymentIntent,
    healthcheck, purchase, purchaseTransaction, seatmap, venue, venueCustomer

All venue-specific queries require a known UUID.

Strategy implemented here:
1. Query the Wayback Machine CDX API (web.archive.org) for all URLs under
   the ``seatengine.net`` domain.  Each SeatEngine v3 venue is served from a
   ``v-{uuid}.seatengine.net`` subdomain, so the CDX results yield a set of
   known UUIDs.
2. For each discovered UUID, call the v3 GraphQL ``venue`` query to retrieve
   the full venue record (name, website, address, city, state, zipcode via the
   ``settings`` subfield).
3. Return the collected venue dicts for the existing upsert pipeline.

Limitations:
- Only venues crawled and archived by the Wayback Machine are discoverable.
  New venues appear in the CDX index after their first Wayback Machine crawl,
  which may lag by days to weeks.  Running this scraper periodically (e.g.
  weekly) ensures newly indexed venues are picked up.
- The CDX API wildcard query (matchType=domain) covers the entire seatengine.net
  domain tree; results are filtered to the ``v-{uuid}`` pattern.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

_V3_API_URL = "https://services.seatengine.com/api/v3/public"
_CDX_API_URL = "https://web.archive.org/cdx/search/cdx"

# Matches https?://v-{uuid}.seatengine.net  (group 1 = UUID)
# End anchor (?:[/?#]|$) prevents spurious matches on seatengine.net.evil.com.
_V3_SUBDOMAIN_RE = re.compile(
    r"https?://v-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.seatengine\.net(?:[/?#]|$)",
    re.IGNORECASE,
)

# v3 GraphQL query — fetches all fields needed by the upsert handler.
# The ``settings`` object contains address, city, state, and zipcode.
_VENUE_QUERY = """
query GetVenue($venueUuid: UUID4!) {
    venue(venueUuid: $venueUuid) {
        uuid
        name
        website
        settings {
            address
            city
            state
            zipcode
        }
    }
}
"""

_MAX_CONCURRENT_UPSERTS = 10
_MAX_CONCURRENT_VENUE_FETCHES = 5
# Maximum number of CDX result rows to retrieve per request.
# The seatengine.net domain has O(10) known v3 subdomains as of 2026-03;
# 1000 is a generous ceiling that avoids truncation.
_CDX_LIMIT = 1000


class SeatEngineV3NationalScraper(BaseScraper):
    """
    Platform-level scraper that discovers SeatEngine v3 venues nationally.

    Triggered by a single clubs row with scraper='seatengine_v3_national'.
    Discovers venues via Wayback Machine CDX + v3 GraphQL ``venue`` query,
    upserts club rows for newly-seen venues, and returns an empty show list
    (discovery only).

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
                    "SeatEngineV3National: no venues returned from discovery",
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
        Discover SeatEngine v3 venues via Wayback Machine CDX + GraphQL.

        Step 1: Query the CDX API for all archived seatengine.net URLs and
        extract unique ``v-{uuid}`` subdomains.
        Step 2: For each UUID, call the v3 GraphQL ``venue`` query to retrieve
        the full venue record.

        Returns:
            List of venue dicts ready for upsert, or [] on total failure.
        """
        uuids = await self._discover_uuids_from_cdx()
        if not uuids:
            Logger.warn(
                "SeatEngineV3National: CDX discovery returned no v3 venue UUIDs",
                self.logger_context,
            )
            return []

        Logger.info(
            f"SeatEngineV3National: CDX found {len(uuids)} unique v3 venue UUID(s)",
            self.logger_context,
        )

        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_VENUE_FETCHES)

        async def _fetch_one(uuid: str) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await self._fetch_venue_by_uuid(uuid)

        tasks = [_fetch_one(u) for u in uuids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        venues = []
        for uuid, result in zip(uuids, results):
            if isinstance(result, Exception):
                Logger.warn(
                    f"SeatEngineV3National: venue fetch failed for {uuid}: {result}",
                    self.logger_context,
                )
            elif result:
                venues.append(result)

        return venues

    async def _discover_uuids_from_cdx(self) -> List[str]:
        """
        Query the Wayback Machine CDX API for seatengine.net URLs and extract
        unique v3 venue UUIDs from ``v-{uuid}.seatengine.net`` subdomains.

        Returns:
            Deduplicated list of UUIDs, or [] on failure.
        """
        cdx_url = (
            f"{_CDX_API_URL}"
            f"?url=seatengine.net"
            f"&matchType=domain"
            f"&output=json"
            f"&fl=original"
            f"&collapse=urlkey"
            f"&limit={_CDX_LIMIT}"
        )
        try:
            response = await self.fetch_json(cdx_url, timeout=self._REQUEST_TIMEOUT)
        except Exception as exc:
            Logger.warn(
                f"SeatEngineV3National: CDX API request failed: {exc}",
                self.logger_context,
            )
            return []

        if not response or not isinstance(response, list):
            return []

        uuids: set = set()
        for row in response[1:]:  # row[0] is the header
            if row:
                url_str = row[0] if isinstance(row, list) else ""
                match = _V3_SUBDOMAIN_RE.match(url_str)
                if match:
                    uuids.add(match.group(1).lower())

        return list(uuids)

    async def _fetch_venue_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single v3 venue record via the GraphQL ``venue`` query.

        Args:
            uuid: The venue's UUID4 string.

        Returns:
            Venue dict with keys: uuid, name, website, address, city, state,
            zipCode — or None on API error / missing data.
        """
        payload: Dict[str, Any] = {
            "query": _VENUE_QUERY,
            "variables": {"venueUuid": uuid},
        }
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
                f"SeatEngineV3National: venue GraphQL request failed for {uuid}: {exc}",
                self.logger_context,
            )
            return None

        if not response:
            return None

        if "errors" in response:
            Logger.warn(
                f"SeatEngineV3National: GraphQL errors for venue {uuid}: {response['errors']}",
                self.logger_context,
            )
            return None

        venue = (response.get("data") or {}).get("venue")
        if not venue or not venue.get("uuid") or not venue.get("name"):
            return None

        settings = venue.get("settings") or {}
        return {
            "uuid": venue["uuid"],
            "name": venue["name"],
            "website": venue.get("website") or "",
            "address": settings.get("address") or "",
            "city": settings.get("city") or "",
            "state": settings.get("state") or "",
            "zipCode": settings.get("zipcode") or "",
        }

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
