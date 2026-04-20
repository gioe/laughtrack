"""
Generic SquadUP platform scraper.

Serves all venues that use SquadUP for ticketing. Per-venue configuration
(user_id) is read from the Club model.

Venues served:
- Dynasty Typewriter (user_id=7408591)
- Sunset Strip Comedy Club (user_id=9086799)
"""

from typing import Any, Dict, List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import SquadUpPageData
from .extractor import SquadUpExtractor
from .transformer import SquadUpEventTransformer

_SQUADUP_EVENTS_URL = "https://www.squadup.com/api/v3/events"
_PAGE_SIZE = 100
_MAX_PAGES = 20


class SquadUpScraper(BaseScraper):
    """
    Generic scraper for venues using SquadUP for ticketing.

    Reads squadup_user_id from the Club model. Uses curl_cffi with Chrome
    impersonation to bypass Cloudflare protection — no application-level
    HTTP headers are sent.
    """

    key = "squadup"

    def __init__(self, club: Club, **kwargs):
        if not club.squadup_user_id:
            raise ValueError(f"Club {club.name} does not have a squadup_user_id configured")
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SquadUpEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Return a single logical target — the SquadUP API is called directly in get_data."""
        return [self.club.squadup_user_id]

    async def _fetch_events_page(self, user_id: str, page: int) -> Optional[Dict[str, Any]]:
        """
        Fetch one page of events from the SquadUP API.

        Uses a bare AsyncSession with Chrome impersonation (no extra headers —
        ``headers=None`` is forwarded to ``HttpClient.fetch_json``) to bypass
        Cloudflare's TLS fingerprint check.

        Routes through ``HttpClient.fetch_json`` so a Cloudflare 403, empty
        body, or known bot-block interstitial transparently retries via the
        shared Playwright headless-browser fallback (A2 / TASK-1650) — the
        primary recovery path when the TLS fingerprint bypass fails.
        """
        params = (
            f"user_ids={user_id}"
            f"&page_size={_PAGE_SIZE}"
            f"&topics_exclude=true"
            f"&additional_attr=sold_out"
            f"&include=custom_fields"
            f"&page={page}"
        )
        url = f"{_SQUADUP_EVENTS_URL}?{params}"
        try:
            async with AsyncSession(impersonate="chrome124") as session:
                return await HttpClient.fetch_json(
                    session=session,
                    url=url,
                    headers=None,
                    logger_context=self.logger_context,
                )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching page {page}: {e}",
                self.logger_context,
            )
            return None

    async def get_data(self, target: str) -> Optional[SquadUpPageData]:
        """
        Fetch all events from the SquadUP API for the given user_id (paginated).

        Args:
            target: The SquadUP user_id (from collect_scraping_targets).

        Returns:
            SquadUpPageData containing all events, or None if none found.
        """
        user_id = target
        all_events: List[SquadUpEvent] = []
        seen_ids: set = set()
        total_pages: Optional[int] = None

        for page in range(1, _MAX_PAGES + 1):
            if total_pages is not None and page > total_pages:
                break

            data = await self._fetch_events_page(user_id, page)
            if not data:
                break

            # Discover total page count from first response
            if total_pages is None:
                try:
                    total_pages = int(
                        data.get("meta", {}).get("paging", {}).get("total_pages", 1)
                    )
                except (TypeError, ValueError):
                    total_pages = 1

            raw_events: List[Dict[str, Any]] = data.get("events") or []
            if not raw_events:
                break

            events = SquadUpExtractor.extract_events(raw_events)

            for event in events:
                if event.event_id not in seen_ids:
                    seen_ids.add(event.event_id)
                    all_events.append(event)

        if not all_events:
            Logger.info(
                f"{self._log_prefix}: no events found (user_id={user_id})",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(all_events)} events total",
            self.logger_context,
        )
        return SquadUpPageData(event_list=all_events)
