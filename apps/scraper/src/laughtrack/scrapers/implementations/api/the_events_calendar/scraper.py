"""Generic scraper for venues using The Events Calendar (Tribe) WordPress plugin.

"The Events Calendar" is a widely-used WordPress plugin that exposes a public
REST API at:
  /wp-json/tribe/events/v1/events

This is a generic, reusable scraper: any venue running the plugin can be
onboarded by pointing its scraping_sources.source_url at the events endpoint
above — no per-venue code required.

Mixed-use venues (a performing-arts studio that hosts theater, workshops AND a
comedy series on one calendar) can opt into comedy-only filtering via
``scraping_sources.metadata`` — all OFF by default so pure-comedy sources are
unchanged:

  - ``event_categories`` — Tribe event-category slug(s) to keep. Applied
    server-side via the API's ``&categories=`` query param so the feed only
    returns those categories (e.g. ``"on-the-spot-improv"``).
  - ``include_title_patterns`` — keep only events whose title matches one of
    these regexes (e.g. drop "Auditions:" / "Workshop" rows that share the
    comedy category).
  - ``exclude_title_patterns`` — drop events whose title matches any regex.

Pipeline:
  1. collect_scraping_targets() → returns [scraping_url] (default base behaviour)
  2. get_data(url)              → fetches all API pages, extracts + filters TribeEvents
  3. transformation_pipeline    → TribeEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tribe_events import TribeEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import TribeEventsPageData
from .extractor import TribeEventExtractor
from .transformer import TribeEventTransformer

_PER_PAGE = 50
_MAX_PAGES = 20


class TheEventsCalendarScraper(BaseScraper):
    """Scraper for venues using The Events Calendar (Tribe) REST API."""

    key = "the_events_calendar"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TribeEventTransformer(club))

    def _category_query(self) -> str:
        """Build the ``&categories=`` query fragment from metadata, or ``""``.

        ``scraping_sources.metadata.event_categories`` may be a single category
        slug or a list of slugs. When set, the Tribe API filters server-side so
        only those categories are returned — the lever a mixed-use venue uses to
        keep only its comedy series. Off by default (empty string).
        """
        raw = (self.club.source_metadata or {}).get("event_categories")
        if isinstance(raw, str):
            slugs = [raw.strip()] if raw.strip() else []
        elif isinstance(raw, (list, tuple)):
            slugs = [str(v).strip() for v in raw if str(v).strip()]
        else:
            slugs = []
        return f"&categories={','.join(slugs)}" if slugs else ""

    def _filter_events(self, events: List[TribeEvent]) -> List[TribeEvent]:
        """Apply the opt-in title allow/block filter to extracted events.

        Even within a single Tribe category, a comedy series can carry
        non-show rows (e.g. ``Auditions:`` or ``Workshop`` events). This keeps
        only real shows when configured via ``scraping_sources.metadata``:

        - ``include_title_patterns`` — keep only titles matching ≥1 pattern.
        - ``exclude_title_patterns`` — drop titles matching any pattern.

        Both off by default, so pure-comedy sources are returned untouched.
        Pattern parsing/compilation is the shared
        :meth:`BaseScraper.compile_title_patterns` helper; the
        include-then-exclude loop mirrors ticketweb / sellingticket / showare.
        """
        include = self.compile_title_patterns("include_title_patterns")
        exclude = self.compile_title_patterns("exclude_title_patterns")
        if not include and not exclude:
            return events

        kept: List[TribeEvent] = []
        for ev in events:
            title = ev.title or ""
            if include and not any(p.search(title) for p in include):
                continue
            if exclude and any(p.search(title) for p in exclude):
                continue
            kept.append(ev)

        dropped = len(events) - len(kept)
        if dropped:
            Logger.info(
                f"{self._log_prefix}: title filter dropped {dropped} of "
                f"{len(events)} event(s); {len(kept)} kept",
                self.logger_context,
            )
        return kept

    async def get_data(self, url: str) -> Optional[TribeEventsPageData]:
        """
        Fetch all pages from a Tribe Events REST API.

        Args:
            url: The Tribe Events API base URL (from club.scraping_url)

        Returns:
            TribeEventsPageData containing all TribeEvent objects, or None
        """
        try:
            all_events = []
            page = 1
            category_query = self._category_query()
            while True:
                api_url = f"{url}?per_page={_PER_PAGE}&status=publish&page={page}{category_query}"
                response = await self.fetch_json(api_url)
                if not response:
                    break

                events = TribeEventExtractor.extract_events(response)
                all_events.extend(events)

                total_pages = TribeEventExtractor.get_total_pages(response)
                Logger.debug(
                    f"{self._log_prefix}: page {page}/{total_pages}, "
                    f"{len(events)} events",
                    self.logger_context,
                )
                if page >= total_pages:
                    break
                if page >= _MAX_PAGES:
                    Logger.warn(
                        f"{self._log_prefix}: reached max pages ({_MAX_PAGES}), stopping early",
                        self.logger_context,
                    )
                    break
                page += 1

            if not all_events:
                self._warn_empty_extraction(url, extra={"pages_fetched": page})
                return None

            all_events = self._filter_events(all_events)
            if not all_events:
                Logger.info(
                    f"{self._log_prefix}: no events matched the configured title "
                    f"filters on {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(all_events)} events total",
                self.logger_context,
            )
            return TribeEventsPageData(event_list=all_events)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: error fetching events: {e}", self.logger_context)
            return None
