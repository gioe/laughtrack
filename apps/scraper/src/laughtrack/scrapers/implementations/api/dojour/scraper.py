"""Dojour platform scraper.

Dojour (https://dojour.us) is a hosted event/ticketing platform that venues
embed on their own sites via an AngularJS calendar iframe at
``https://dojour.us/embed/u/<username>``. The embed is hydrated by a public
JSON feed::

    GET https://dojour.us/api/event_instances/user_feed/
        ?username=<username>&date_min=<now>&distinct_event=true
        &exclude_plans=true&page_size=<n>

The scraper is reusable across the platform: store the venue's Dojour embed /
profile URL (or bare username) in ``scraping_sources.source_url`` and the
``username`` is parsed from it. Each feed row is an event whose
``upcoming_showing_set`` lists every upcoming showtime; the extractor expands
those into one Show per showing.

No category filter is applied: Dojour exposes no reliable per-event comedy tag,
and this scraper is onboarded for dedicated comedy rooms (e.g. Sisyphus Brewing
& Comedy) whose Dojour calendar is the comedy room's calendar.
"""

from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode, urlsplit

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.dojour import DojourEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.dojour.data import DojourPageData
from laughtrack.scrapers.implementations.api.dojour.extractor import DojourExtractor
from laughtrack.scrapers.implementations.api.dojour.transformer import DojourEventTransformer

_FEED_URL = "https://dojour.us/api/event_instances/user_feed/"
_PAGE_SIZE = 50
_MAX_PAGES = 20  # safety cap; venues list far fewer pages in practice


class DojourScraper(BaseScraper):
    """Scraper for venue calendars hosted on the Dojour platform."""

    key = "dojour"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/Chicago"
        self.transformation_pipeline.register_transformer(DojourEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Scrape the venue's Dojour source stored in source_url."""
        return [self.club.scraping_url]

    @staticmethod
    def _parse_username(source: str) -> Optional[str]:
        """Extract the Dojour username from an embed/profile URL or bare slug.

        Handles ``https://dojour.us/embed/u/<username>?...``,
        ``https://dojour.us/u/<username>``, and a bare ``<username>``.
        """
        if not source:
            return None
        source = source.strip()
        if "/" not in source and ":" not in source:
            return source  # bare username
        path = urlsplit(source).path.strip("/")
        parts = [p for p in path.split("/") if p]
        if "u" in parts:
            idx = parts.index("u")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return parts[-1] if parts else None

    def _build_feed_url(self, username: str) -> str:
        date_min = datetime.now().strftime("%Y-%m-%d 00:00")
        params = {
            "username": username,
            "date_min": date_min,
            "distinct_event": "true",
            "exclude_plans": "true",
            "page_size": _PAGE_SIZE,
        }
        return f"{_FEED_URL}?{urlencode(params)}"

    async def get_data(self, url: str) -> Optional[EventListContainer[DojourEvent]]:
        """Fetch the Dojour user_feed (following pagination) and extract showings."""
        username = self._parse_username(url)
        if not username:
            Logger.error(
                f"{self._log_prefix}: could not parse Dojour username from '{url}'",
                self.logger_context,
            )
            return None

        results = []
        next_url: Optional[str] = self._build_feed_url(username)
        pages = 0
        while next_url and pages < _MAX_PAGES:
            try:
                response = await self.fetch_json(next_url)
            except Exception as e:
                Logger.error(
                    f"{self._log_prefix}: get_data failed for {next_url}: {e}",
                    self.logger_context,
                )
                break
            if not response:
                break
            page_results = response.get("results") or []
            results.extend(page_results)
            next_url = response.get("next")
            pages += 1

        if not results:
            Logger.info(
                f"{self._log_prefix}: no events listed on Dojour for '{username}'",
                self.logger_context,
            )
            return None

        events = DojourExtractor.extract_events(results, self.default_timezone)
        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming Dojour showings for '{username}' "
                f"({len(results)} event(s) fetched)",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} Dojour showing(s) " f"from {len(results)} event(s)",
            self.logger_context,
        )
        return DojourPageData(event_list=events)
