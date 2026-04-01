"""
Ninkashi API client for fetching upcoming events.

Ninkashi is a ticketing platform used by venues like Cheaper Than Therapy
(tickets.cttcomedy.com). The public API requires no authentication.

API endpoint:
  GET https://api.ninkashi.com/public_access/events/find_by_url_site
      ?url_site=<subdomain>&page=<n>&per_page=<n>

Response: a root-level JSON array of event objects.
"""

from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ninkashi import NinkashiEvent
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _is_future_event(raw: dict, now: datetime) -> bool:
    """Return True if the event's start time is in the future (or unparseable)."""
    try:
        event_dates = raw.get("event_dates_attributes") or []
        if not event_dates:
            return True
        starts_at = event_dates[0].get("starts_at", "")
        if not starts_at:
            return True
        dt = datetime.strptime(starts_at, "%Y-%m-%d %H:%M:%S %z")
        return dt > now
    except Exception:
        return True  # include on parse failure to avoid silent drops


class NinkashiClient(BaseApiClient):
    """Client for the Ninkashi public events API."""

    BASE_URL = "https://api.ninkashi.com/public_access/events/find_by_url_site"
    PER_PAGE = 100
    MAX_PAGES = 50

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        super().__init__(club, proxy_pool=proxy_pool)
        self.logger_context = club.as_context()

    async def fetch_events(self, url_site: str) -> List[NinkashiEvent]:
        """
        Fetch all upcoming events for the given url_site, paginating as needed.

        Stops when a page is smaller than the first page (actual page size), when
        MAX_PAGES is reached, or when an empty/non-list page is returned. Only
        future events are included in the result.

        Returns an empty list on network failure or unexpected response format.
        """
        events: List[NinkashiEvent] = []
        page = 1
        page_size: Optional[int] = None  # actual page size learned from first response
        now = datetime.now(timezone.utc)

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

            for raw in response:
                if not isinstance(raw, dict):
                    continue
                if not _is_future_event(raw, now):
                    continue
                try:
                    events.append(NinkashiEvent.from_dict(raw, url_site))
                except Exception as e:
                    Logger.warn(
                        f"NinkashiClient: skipping malformed event — {e}",
                        self.logger_context,
                    )

            if len(response) < page_size:
                break
            page += 1

        return events
