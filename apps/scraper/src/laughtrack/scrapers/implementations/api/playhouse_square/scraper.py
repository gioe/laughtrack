"""Dedicated Playhouse Square (Cleveland) comedy scraper.

Playhouse Square runs a custom carbonhouse "showtime" CMS (RequireJS, not
WordPress) — it is a Tessitura OPERATOR but is NOT on the WordPress
tessi_production REST integration the generic ``tessitura`` scraper targets, so
it cannot be onboarded there (see SCRAPERS.md). The scrapable seam is the
load-more AJAX feed behind the ``/events`` "Load More Events" button:

    GET {origin}/events/events_ajax/{offset}?per_page=N
        &category=0&venue=0&team=0&came_from_page=event-list-page

The response is a JSON-encoded **string of HTML** (the same ``m-eventItem`` cards
the list page server-renders). curl_cffi's default Chrome impersonation is
required — plain requests get a 406 from the WAF. ``fetch_json`` returns the
decoded HTML string, which the extractor parses.

Because the feed is multi-venue and multi-genre with no comedy tag, each
scraping source is scoped to ONE PHS theatre via ``metadata.venue_titles`` and
comedy is isolated by a known-comedian heuristic (see comedy_filter.py). The
result: a per-venue ``playhouse_square`` source emits only that theatre's comedy
shows, with ticket links pointing at the PHS box office (drives venue traffic).

Per-source ``scraping_sources.metadata``:
  - ``venue_titles`` — list of feed ``venue_title`` strings this source covers
    (e.g. ``["Connor Palace"]``). REQUIRED; without it the source emits nothing.
  - ``per_page`` — feed page size (default 500; one fetch returns the full feed).
  - ``min_comedian_popularity`` — comedy-filter popularity floor (default 0.30).
  - ``default_show_time`` — ``HH:MM`` for the (time-less) list dates (default 19:00).

Pipeline:
    1. collect_scraping_targets(): build the events_ajax feed URL.
    2. get_data(url): fetch + decode the feed, parse all cards, filter to this
       source's venue(s) and to comedy, wrap as PlayhouseSquarePageData.
    3. transformation_pipeline: PlayhouseSquareEvent.to_show() -> Show objects.
"""

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .comedy_filter import DEFAULT_MIN_COMEDIAN_POPULARITY, select_comedy_titles
from .data import PlayhouseSquarePageData
from .extractor import extract_events
from .transformer import PlayhouseSquareEventTransformer

_DEFAULT_ORIGIN = "https://www.playhousesquare.org"
_DEFAULT_PER_PAGE = 500


class PlayhouseSquareScraper(BaseScraper):
    """Per-venue comedy scraper for the Playhouse Square event feed."""

    key = "playhouse_square"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(PlayhouseSquareEventTransformer(club))
        self._lineup_handler = LineupHandler()
        self._comedian_handler = ComedianHandler()

    def _metadata(self) -> Dict[str, Any]:
        return getattr(self.club, "source_metadata", None) or {}

    def _origin(self) -> str:
        """Resolve the feed origin from the club's scraping_url, defaulting to
        the canonical PHS host."""
        raw = self.club.scraping_url
        if not raw:
            return _DEFAULT_ORIGIN
        parts = urlsplit(raw if "//" in raw else f"https://{raw}")
        if not parts.netloc:
            return _DEFAULT_ORIGIN
        return urlunsplit((parts.scheme or "https", parts.netloc, "", "", ""))

    def _venue_titles(self) -> List[str]:
        raw = self._metadata().get("venue_titles")
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        return [str(v).strip() for v in raw if str(v).strip()]

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        meta = self._metadata()
        try:
            per_page = int(meta.get("per_page", _DEFAULT_PER_PAGE))
        except (TypeError, ValueError):
            per_page = _DEFAULT_PER_PAGE
        origin = self._origin()
        feed = (
            f"{origin}/events/events_ajax/0?category=0&venue=0&team=0"
            f"&per_page={per_page}&came_from_page=event-list-page"
        )
        return [feed]

    async def get_data(self, target: ScrapingTarget) -> Optional[PlayhouseSquarePageData]:
        url = str(target)
        venue_titles = self._venue_titles()
        if not venue_titles:
            Logger.warn(
                f"{self._log_prefix}: no metadata.venue_titles configured — "
                f"refusing to emit the whole multi-venue feed",
                self.logger_context,
            )
            return None

        try:
            decoded = await self.fetch_json(url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch PHS feed {url}: {e}",
                self.logger_context,
            )
            return None

        # The feed payload is a JSON-encoded HTML string.
        if not decoded or not isinstance(decoded, str):
            Logger.warn(
                f"{self._log_prefix}: PHS feed returned empty/non-string payload: {url}",
                self.logger_context,
            )
            return None

        all_events = extract_events(decoded, base_url=self._origin())
        if not all_events:
            Logger.warn(
                f"{self._log_prefix}: No event cards parsed from PHS feed {url}",
                self.logger_context,
            )
            return None

        # Scope to this source's venue(s).
        wanted = {v.lower() for v in venue_titles}
        venue_events = [e for e in all_events if e.venue_title.lower() in wanted]
        if not venue_events:
            Logger.info(
                f"{self._log_prefix}: parsed {len(all_events)} PHS event(s); "
                f"none at venue(s) {venue_titles}",
                self.logger_context,
            )
            return None

        # Isolate comedy via the known-comedian heuristic (DB-backed — run the
        # sync handler queries off the event loop, like the national scrapers).
        try:
            min_pop = float(self._metadata().get("min_comedian_popularity", DEFAULT_MIN_COMEDIAN_POPULARITY))
        except (TypeError, ValueError):
            min_pop = DEFAULT_MIN_COMEDIAN_POPULARITY

        loop = asyncio.get_running_loop()
        comedy_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                [e.title for e in venue_events],
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                min_popularity=min_pop,
                allowlist=self._metadata().get("comedy_title_allowlist"),
            ),
        )

        comedy_events = [e for e in venue_events if e.title in comedy_titles]
        Logger.info(
            f"{self._log_prefix}: PHS feed -> {len(all_events)} event(s), "
            f"{len(venue_events)} at {venue_titles}, {len(comedy_events)} comedy",
            self.logger_context,
        )
        if not comedy_events:
            return None
        return PlayhouseSquarePageData(event_list=comedy_events)
