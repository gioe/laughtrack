"""do314 / DoStuff Media venue scraper.

DoStuff Media powers a network of city event sites (do314 St. Louis, do312
Chicago, do617 Boston, doLA, etc.) that all expose the same per-venue JSON
contract::

    GET https://do314.com/venues/<slug>/events.json
    -> {"venue": {...}, "event_groups": [{"date": ..., "events": [...]}], ...}

The scraper is reusable across the network: store the full ``events.json`` URL
for the venue in ``scraping_sources.source_url`` and the host varies per city.

Because many DoStuff venues are mixed-use (this scraper was first onboarded for
Apotheosis Comics and Lounge, a comic shop that also hosts comedy), events are
filtered to do314's own ``category_param == "comedy"`` by default. Override per
source via ``scraping_sources.metadata``:

    {"do314_include_all_categories": true}       # keep every category
    {"do314_categories": ["comedy", "spoken"]}   # custom allowlist
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.do314 import Do314Event
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.do314.data import Do314PageData
from laughtrack.scrapers.implementations.api.do314.extractor import Do314Extractor
from laughtrack.scrapers.implementations.api.do314.transformer import Do314EventTransformer

_DEFAULT_CATEGORIES = frozenset({"comedy"})


class Do314Scraper(BaseScraper):
    """Scraper for do314 / DoStuff Media venue event feeds."""

    key = "do314"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/Chicago"
        self._categories = self._resolve_categories()
        self.transformation_pipeline.register_transformer(Do314EventTransformer(club))

    def _resolve_categories(self) -> Optional[frozenset]:
        """Return the set of category_param values to keep, or None for all."""
        metadata = self.club.source_metadata or {}
        if metadata.get("do314_include_all_categories") is True:
            return None
        raw = metadata.get("do314_categories")
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list) and raw:
            return frozenset(str(c).strip().lower() for c in raw if str(c).strip())
        return _DEFAULT_CATEGORIES

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the venue's events.json URL stored in the source_url."""
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[EventListContainer[Do314Event]]:
        """Fetch the do314 venue events feed and return upcoming events."""
        try:
            response = await self.fetch_json(url)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {url}: {e}", self.logger_context)
            return None

        if not response:
            Logger.warn(
                f"{self._log_prefix}: empty response from do314 API ({url})",
                self.logger_context,
            )
            return None

        event_groups = response.get("event_groups") or []
        events = Do314Extractor.extract_events(event_groups, self.default_timezone)
        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming events listed on do314 ({url})",
                self.logger_context,
            )
            return None

        kept = self._apply_category_filter(events)
        if not kept:
            Logger.info(
                f"{self._log_prefix}: no events matched category filter "
                f"{sorted(self._categories) if self._categories else 'all'} "
                f"({len(events)} fetched)",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(kept)}/{len(events)} do314 event(s)",
            self.logger_context,
        )
        return Do314PageData(event_list=kept)

    def _apply_category_filter(self, events: List[Do314Event]) -> List[Do314Event]:
        if self._categories is None:
            return events
        return [e for e in events if e.category_param in self._categories]
