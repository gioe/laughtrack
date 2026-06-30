"""
Delirious Comedy Club scraper (FriendlySky platform).

Delirious Comedy Club (4100 Paradise Rd, Las Vegas, NV) uses the FriendlySky
ticketing platform at tickets.deliriouscomedyclub.com.

The API endpoint returns all upcoming games in a single call:

  GET /rest/events/$EKR?_branch=findByDomainNameOrHashId&_s=1

Required headers:
  - hashsiteid: e9b   (site identifier)
  - source: ONLINE
  - accept: application/json

No session cookie or auth token is needed — the headers alone are sufficient.

The response contains a ``data.games`` array with ~200+ shows. Each game has
a name field with comma-separated comedian names, date/time info, and a hashId
used to construct the ticket URL.

Pipeline:
  1. collect_scraping_targets() → single API URL
  2. get_data(url)              → fetch JSON, extract games, return DeliriousPageData
  3. transformation_pipeline    → FriendlySkyEvent.to_show() → Show objects
"""

import asyncio
import os
from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.friendlysky import FriendlySkyEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import DeliriousPageData
from .extractor import DeliriousExtractor
from .transformer import DeliriousEventTransformer

_API_PATH = "/rest/events/$EKR?_branch=findByDomainNameOrHashId&_s=1"

_FRIENDLYSKY_HEADERS = {
    "hashsiteid": "e9b",
    "source": "ONLINE",
    "accept": "application/json",
}

# Per-event price chain. The games API carries no price, but two unauthenticated
# JSON calls per event recover it (only _FRIENDLYSKY_HEADERS, no cookies/auth):
#   1. /rest/pkgs?_branch=findByGameIdAndUrlName&hashGameId={hashId}&urlName=tickets
#      → data.hashId = package hash
#   2. /rest/onlinePageDispatcher/firstPage?hashPkgId={pkgHash}
#      → data.targetPkgItems[*].item.price (min face = starting price)
# These are internal SPA endpoints (no public contract) — degrade to price-less
# per event on any failure so one bad event never sinks the run.
_PKGS_PATH = (
    "/rest/pkgs?_branch=findByGameIdAndUrlName"
    "&hashGameId={hash_id}&urlName=tickets&_s=1"
)
_FIRSTPAGE_PATH = "/rest/onlinePageDispatcher/firstPage?hashPkgId={pkg_hash}"
_DEFAULT_PRICE_FETCH_CONCURRENCY = 5


class DeliriousComedyClubScraper(BaseScraper):
    """Scraper for Delirious Comedy Club via FriendlySky API."""

    key = "delirious"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            DeliriousEventTransformer(club)
        )

    def _get_base_url(self) -> str:
        """Derive the base URL from the club's scraping_url."""
        if self.club.scraping_url:
            parsed = urlparse(self.club.scraping_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return "https://tickets.deliriouscomedyclub.com"

    async def collect_scraping_targets(self) -> List[str]:
        """Return the single FriendlySky API URL."""
        base = self._get_base_url()
        url = f"{base}{_API_PATH}"
        Logger.info(
            f"{self._log_prefix}: using API URL {url}",
            self.logger_context,
        )
        return [url]

    async def get_data(self, url: str) -> Optional[DeliriousPageData]:
        """Fetch all games from the FriendlySky events API.

        Args:
            url: FriendlySky events API URL.

        Returns:
            DeliriousPageData with extracted events, or None if no games found.
        """
        try:
            response = await self.fetch_json(url, headers=_FRIENDLYSKY_HEADERS)
            if response is None:
                self._warn_empty_extraction(f"FriendlySky API {url}", subject="data", payload=response)
                return None

            base_url = self._get_base_url()
            events = DeliriousExtractor.extract_events(response, base_url)

            if not events:
                self._warn_empty_extraction(f"FriendlySky API {url}", payload=response)
                return None

            await self._enrich_prices(events, base_url)

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} game(s) from API",
                self.logger_context,
            )
            return DeliriousPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: get_data failed for {url}: {e}",
                self.logger_context,
            )
            return None

    async def _enrich_prices(
        self, events: List[FriendlySkyEvent], base_url: str
    ) -> None:
        """Set ``event.price`` to the min face price via the 2-call package chain.

        For each event: GET /rest/pkgs (→ package hash) then GET firstPage
        (→ min targetPkgItems face price), reusing ``self.fetch_json`` with the
        FriendlySky headers. Concurrency is bounded by a semaphore so the
        ~2-per-event extra fetches stay within budget, and every per-event
        failure is swallowed so the event keeps its price-less ticket rather
        than sinking the run.
        """
        try:
            concurrency = int(
                os.environ.get(
                    "DELIRIOUS_PRICE_CONCURRENCY", _DEFAULT_PRICE_FETCH_CONCURRENCY
                )
            )
        except (TypeError, ValueError):
            concurrency = _DEFAULT_PRICE_FETCH_CONCURRENCY
        concurrency = max(1, concurrency)
        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(event: FriendlySkyEvent) -> None:
            if not event.hash_id:
                return
            async with sem:
                try:
                    pkgs_url = base_url + _PKGS_PATH.format(hash_id=event.hash_id)
                    pkgs_response = await self.fetch_json(
                        pkgs_url, headers=_FRIENDLYSKY_HEADERS
                    )
                    pkg_hash = DeliriousExtractor.extract_package_hash(pkgs_response)
                    if not pkg_hash:
                        return

                    firstpage_url = base_url + _FIRSTPAGE_PATH.format(pkg_hash=pkg_hash)
                    firstpage_response = await self.fetch_json(
                        firstpage_url, headers=_FRIENDLYSKY_HEADERS
                    )
                    price = DeliriousExtractor.extract_min_price(firstpage_response)
                except Exception as e:
                    Logger.debug(
                        f"{self._log_prefix}: price fetch failed for game "
                        f"{event.hash_id}: {e}",
                        self.logger_context,
                    )
                    return
            if price is not None:
                event.price = price

        await asyncio.gather(*(_fetch_one(event) for event in events))
