"""HoldMyTicket whitelabel-site scraper.

HoldMyTicket (holdmyticket.com, "hmt-front") venues run branded whitelabel
sites (``<venue>.holdmyticket.com``) whose SPA hydrates from a public JSON
API keyed by the whitelabel host::

    GET https://holdmyticket.com/api/public/events/nearby/api_key/anon
        /page/{n}/whitelabel/{host}          (paginated feed, venue-scoped)
    GET https://holdmyticket.com/api/public/events/repeating/id/{id}
        /whitelabel/{host}                   (expands a series into showtimes)

Each feed entry is the head of a repeating series (Fri/Sat runs) with a
``repeating_future_events`` count; the expansion endpoint returns every
showtime in the series — including the head itself and sibling heads that may
also appear in the feed — so showtimes are deduplicated by event id.

The scraper is generic across the platform: point a ``scraping_sources`` row's
``source_url`` at the venue's whitelabel site
(``https://<venue>.holdmyticket.com/``) and both API targets are derived from
its host. Optional ``scraping_sources.metadata``:

    {"holdmyticket_venue_id": "8819"}   # keep only this venue's feed entries
                                        # (for shared/multi-venue whitelabels)

Currently used by: Quezada's Comedy Club & Cantina (Santa Ana Pueblo, NM).
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.holdmyticket import HoldMyTicketEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.holdmyticket.data import (
    HoldMyTicketPageData,
)
from laughtrack.scrapers.implementations.api.holdmyticket.extractor import (
    HoldMyTicketExtractor,
)
from laughtrack.scrapers.implementations.api.holdmyticket.transformer import (
    HoldMyTicketEventTransformer,
)

_API_BASE = "https://holdmyticket.com/api"
# Backstop against a runaway feed — 10 pages x 25 events is far above any
# single venue's upcoming calendar.
_MAX_FEED_PAGES = 10


class HoldMyTicketScraper(BaseScraper):
    """Scraper for HoldMyTicket whitelabel venue feeds."""

    key = "holdmyticket"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/Denver"
        self.transformation_pipeline.register_transformer(
            HoldMyTicketEventTransformer(club)
        )

    def _whitelabel_host(self) -> Optional[str]:
        """Return the whitelabel host from the source URL."""
        parsed = urlparse(self.club.scraping_url or "")
        return parsed.netloc or None

    def _venue_id_filter(self) -> Optional[str]:
        """Return the metadata venue-id allowlist value, if configured."""
        metadata = self.club.source_metadata or {}
        raw = metadata.get("holdmyticket_venue_id")
        if raw is None:
            return None
        value = str(raw).strip()
        return value or None

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the venue's whitelabel site stored in the source_url."""
        if not self._whitelabel_host():
            Logger.warn(
                f"{self._log_prefix}: invalid/empty HoldMyTicket source_url "
                f"({self.club.scraping_url!r})",
                self.logger_context,
            )
            return []
        return [self.club.scraping_url]

    def _feed_url(self, host: str, page: int) -> str:
        return f"{_API_BASE}/public/events/nearby/api_key/anon/page/{page}/whitelabel/{host}"

    def _repeating_url(self, host: str, event_id: int) -> str:
        return f"{_API_BASE}/public/events/repeating/id/{event_id}/whitelabel/{host}"

    async def get_data(self, url: str) -> Optional[EventListContainer[HoldMyTicketEvent]]:
        """Fetch the whitelabel feed, expand repeating series, dedup showtimes."""
        host = self._whitelabel_host()
        if not host:
            return None

        heads = await self._fetch_feed_heads(host)
        if not heads:
            Logger.info(
                f"{self._log_prefix}: no upcoming events in HoldMyTicket feed "
                f"for {host}",
                self.logger_context,
            )
            return None

        # Feed heads are authoritative (they carry the cancel/postponed flags
        # the expansion entries lack), so they land in the map first and
        # setdefault keeps them over expansion duplicates.
        raw_by_id: Dict[int, Dict[str, Any]] = {}
        for head in heads:
            raw_by_id.setdefault(int(head["id"]), head)
        for head in heads:
            await self._expand_repeating(host, head, raw_by_id)

        events = HoldMyTicketExtractor.to_events(
            list(raw_by_id.values()), self.default_timezone
        )
        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming shows after expansion for {host}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} HoldMyTicket show(s) "
            f"from {len(heads)} feed event(s) for {host}",
            self.logger_context,
        )
        return HoldMyTicketPageData(event_list=events)

    async def _fetch_feed_heads(self, host: str) -> List[Dict[str, Any]]:
        """Fetch feed pages until an empty page, applying the venue filter."""
        venue_filter = self._venue_id_filter()
        heads: List[Dict[str, Any]] = []
        for page in range(_MAX_FEED_PAGES):
            feed_url = self._feed_url(host, page)
            try:
                payload = await self.fetch_json(feed_url)
            except Exception as e:
                Logger.error(
                    f"{self._log_prefix}: feed fetch failed for {feed_url}: {e}",
                    self.logger_context,
                )
                break
            page_events = HoldMyTicketExtractor.extract_raw_events(payload)
            raw_count = len((payload or {}).get("events") or []) if isinstance(payload, dict) else 0
            if venue_filter is not None:
                page_events = [
                    e for e in page_events
                    if str(e.get("venue_id") or "").strip() == venue_filter
                ]
            heads.extend(page_events)
            if raw_count == 0:
                break
        else:
            Logger.warn(
                f"{self._log_prefix}: feed pagination hit the {_MAX_FEED_PAGES}-page "
                f"cap for {host}; later events may be missing",
                self.logger_context,
            )
        return heads

    async def _expand_repeating(
        self,
        host: str,
        head: Dict[str, Any],
        raw_by_id: Dict[int, Dict[str, Any]],
    ) -> None:
        """Merge a head's repeating-series showtimes into ``raw_by_id``."""
        try:
            repeating_count = int(head.get("repeating_future_events") or 0)
        except (TypeError, ValueError):
            repeating_count = 0
        if repeating_count <= 0:
            return

        repeating_url = self._repeating_url(host, int(head["id"]))
        try:
            payload = await self.fetch_json(repeating_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: repeating fetch failed for {repeating_url}: {e}",
                self.logger_context,
            )
            return
        for raw in HoldMyTicketExtractor.extract_raw_events(payload):
            raw_by_id.setdefault(int(raw["id"]), raw)
