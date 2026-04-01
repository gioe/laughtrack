"""
Ninkashi API client for fetching upcoming events.

Ninkashi is a ticketing platform used by venues like Cheaper Than Therapy
(tickets.cttcomedy.com). The public API requires no authentication.

API endpoint:
  GET https://api.ninkashi.com/public_access/events/find_by_url_site
      ?url_site=<subdomain>&page=<n>&per_page=<n>

Response: a root-level JSON array of event objects.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ninkashi import NinkashiEvent
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _parse_event_starts_at(raw: dict) -> Optional[datetime]:
    """Return the event's start datetime (UTC-aware), or None if unparseable."""
    try:
        event_dates = raw.get("event_dates_attributes") or []
        if not event_dates:
            return None
        starts_at = event_dates[0].get("starts_at", "")
        if not starts_at:
            return None
        return datetime.strptime(starts_at, "%Y-%m-%d %H:%M:%S %z")
    except Exception:
        return None


def _is_future_event(raw: dict, now: datetime) -> bool:
    """Return True if the event's start time is in the future (or unparseable)."""
    dt = _parse_event_starts_at(raw)
    return dt is None or dt > now  # include on parse failure to avoid silent drops


def _is_beyond_horizon(raw: dict, horizon: datetime) -> bool:
    """Return True if the event's start time is beyond the given horizon."""
    dt = _parse_event_starts_at(raw)
    return dt is not None and dt > horizon


class NinkashiClient(BaseApiClient):
    """Client for the Ninkashi public events API."""

    BASE_URL = "https://api.ninkashi.com/public_access/events/find_by_url_site"
    PER_PAGE = 100
    MAX_PAGES = 50
    DATE_HORIZON_DAYS = 730  # skip events and stop pagination once we see events this far out

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        super().__init__(club, proxy_pool=proxy_pool)
        self.logger_context = club.as_context()

    async def fetch_events(self, url_site: str) -> List[NinkashiEvent]:
        """
        Fetch all upcoming events for the given url_site, paginating as needed.

        Stops when a page is smaller than the first page (actual page size), when
        MAX_PAGES is reached, when an empty/non-list page is returned, or when an
        event beyond DATE_HORIZON_DAYS is encountered (early-stop heuristic for
        venues like CTT that pre-book years of recurring open-mic slots). Events
        beyond the horizon are skipped to avoid DB bloat. Only future events within
        the horizon are included in the result.

        Returns an empty list on network failure or unexpected response format.
        """
        events: List[NinkashiEvent] = []
        page = 1
        page_size: Optional[int] = None  # actual page size learned from first response
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=self.DATE_HORIZON_DAYS)

        while True:
            if page > self.MAX_PAGES:
                Logger.warn(
                    f"NinkashiClient: reached MAX_PAGES={self.MAX_PAGES} for {url_site} — stopping pagination",
                    self.logger_context,
                )
                break

            qs = urlencode({"url_site": url_site, "page": page, "per_page": self.PER_PAGE})
            url = f"{self.BASE_URL}?{qs}"
            response = await self.fetch_json_list(url)
            if response is None:
                Logger.warn(
                    f"NinkashiClient: no list response on page {page} for {url_site} — stopping pagination",
                    self.logger_context,
                )
                break

            if not response:
                break

            if page_size is None:
                page_size = len(response)

            beyond_horizon_on_page = False
            for raw in response:
                if not isinstance(raw, dict):
                    continue
                if not _is_future_event(raw, now):
                    continue
                if _is_beyond_horizon(raw, horizon):
                    beyond_horizon_on_page = True
                    continue  # skip event; also signals early stop below
                try:
                    events.append(NinkashiEvent.from_dict(raw, url_site))
                except Exception as e:
                    Logger.warn(
                        f"NinkashiClient: skipping malformed event — {e}",
                        self.logger_context,
                    )

            if beyond_horizon_on_page:
                Logger.info(
                    f"NinkashiClient: stopping pagination — events beyond {self.DATE_HORIZON_DAYS}-day horizon found for {url_site}",
                    self.logger_context,
                )
                break

            if len(response) < page_size:
                break
            page += 1

        return events
