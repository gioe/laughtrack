"""AEG/Goldenvoice Carbonhouse venue-page scraper.

Many AEG Presents / Goldenvoice venues (The Warfield, The Regency Ballroom,
Social Hall SF, …) run the stock Carbonhouse venue-site template
(``generatorAgent rdf:resource="http://carbonhouse.com/"``) and ticket every
show via AXS (``axs.com/events/<id>/...?skin=<venue>``). The generic ``axs``
scraper expects an AXS-skinned homepage with ``rsCaption`` slider cards and the
``pabst_axs`` scraper expects ``div.eventItem`` cards; this Carbonhouse template
uses ``div.entry`` cards on the venue's own ``/events`` page instead — carrying
the show name, a real date AND show time, the venue detail URL, and an AXS ticket
link. The ``axs.com`` detail pages are DataDome-protected, so only the venue page
is fetched.

These are mixed-use concert venues that host comedy only occasionally, so the
scraper is a mixed-use venue source: it opts into the shared comedy filter
(``scraping_sources.metadata.comedy_filter``) which keeps a title when it carries
a comedy keyword, matches a per-source ``comedy_title_allowlist`` substring, or
names a known comedian above the popularity floor — dropping the concert
programming. Without the filter the scraper imports every event (mirrors the
generic ``axs`` import-all behaviour).

Per-venue configuration (``scraping_sources``):
    - ``source_url`` (required) — the venue ``/events`` page, e.g.
      ``https://www.thewarfieldtheatre.com/events``
    - ``metadata.default_show_time`` (optional, ``HH:MM``, default 19:00) — only
      used for cards that carry no parseable show time
    - ``metadata.comedy_filter`` (optional) — enable comedy-only isolation
    - ``metadata.comedy_title_allowlist`` (optional) — substrings forcing keep of
      comedian-name acts the keyword filter misses (e.g. "Kevin Langue")
    - ``metadata.min_comedian_popularity`` (optional) — known-comedian floor

Pipeline:
    1. collect_scraping_targets(): return the venue ``/events`` URL.
    2. get_data(url): fetch the page, parse the event cards, apply the comedy
       filter, wrap as AEGAXSPageData.
    3. transformation_pipeline: AEGAXSEvent.to_show() -> Show objects.
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)
from laughtrack.shared.types import ScrapingTarget

from .data import AEGAXSPageData
from .extractor import extract_events
from .transformer import AEGAXSEventTransformer


class AEGAXSVenueScraper(BaseScraper):
    """Venue-page scraper for AEG/Goldenvoice Carbonhouse rooms (AXS-ticketed)."""

    key = "aeg_axs"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(AEGAXSEventTransformer(club))
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        page_url = self.club.scraping_url
        if not page_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no scraping_url configured",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(page_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[AEGAXSPageData]:
        try:
            html = await self.fetch_html(target)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch AEG venue page {target}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: AEG venue page returned empty HTML: {target}",
                self.logger_context,
            )
            return None

        events = extract_events(html)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: No event cards parsed from AEG venue page {target}",
                self.logger_context,
            )
            return None

        if self._comedy_filter:
            events = await self._filter_comedy(events)
            if not events:
                Logger.warn(
                    f"{self._log_prefix}: comedy filter dropped all events from {target}",
                    self.logger_context,
                )
                return None

        Logger.info(
            f"{self._log_prefix}: Parsed {len(events)} event(s) from AEG venue page {target}",
            self.logger_context,
        )
        return AEGAXSPageData(event_list=events)

    async def _filter_comedy(self, events: List) -> List:
        """Keep only comedy events via the shared keyword/allowlist/comedian filter.

        The venue page is concert-dominated; ``select_comedy_titles`` keeps a
        title when it carries a comedy keyword, matches a per-source allowlist
        substring, or names a known comedian above the popularity floor.
        """
        titles = [e.title for e in events if e.title]
        loop = asyncio.get_running_loop()
        kept_titles = await loop.run_in_executor(
            None,
            lambda: select_comedy_titles(
                titles,
                lineup_handler=self._lineup_handler,
                comedian_handler=self._comedian_handler,
                min_popularity=resolve_min_popularity(self.club.source_metadata),
                allowlist=resolve_allowlist(self.club.source_metadata),
            ),
        )
        kept = [e for e in events if e.title in kept_titles]
        Logger.info(
            f"{self._log_prefix}: comedy filter kept {len(kept)}/{len(events)} event(s)",
            self.logger_context,
        )
        return kept
