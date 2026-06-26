"""Ludus (ludus.com) box-office scraper.

Pipeline:
    1. collect_scraping_targets(): fetch the venue's Ludus embed, keep the
       ``show_item`` cards tagged with the configured comedy category id, layer
       the shared comedy keyword/comedian filter to drop venue mis-tags (e.g. a
       tribute band mis-tagged as comedy), and return one detail URL per kept
       show.
    2. get_data(url): fetch one show's detail page and fan its upcoming
       showtimes out into dated shows.

Anti-bot: Ludus sits behind a Cloudflare managed challenge that 403s a plain
request; a curl_cffi ``impersonate='chrome120'`` session clears it.

Configuration (``scraping_sources.metadata``):
    - ``ludus_subdomain`` (required) — the venue's Ludus subdomain
    - ``comedy_category_id`` (optional) — the venue-specific comedy category id.
      When set, only embed cards tagged with it are kept (mixed-use venue). When
      omitted, ALL cards are kept (dedicated comedy venue that leaves
      ``data-event-categories`` empty, e.g. ComedySportz) — pair with the
      title-pattern allowlist below to drop classes/workshops.
    - ``include_title_patterns`` / ``exclude_title_patterns`` (optional) — keep
      only / drop cards whose title matches a regex (case-insensitive). Off by
      default; the include-then-exclude loop mirrors ticketweb / sellingticket.
    - ``comedy_filter`` (optional) — enable the keyword/comedian mis-tag filter
"""

import asyncio
import re
from typing import Dict, List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.event.ludus import LudusEvent
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.utils.comedy_filter import (
    is_comedy_filter_enabled,
    resolve_allowlist,
    resolve_min_popularity,
    select_comedy_titles,
)
from laughtrack.shared.types import ScrapingTarget

from .data import LudusPageData
from .extractor import (
    detail_url_for_show,
    embed_url_for_subdomain,
    extract_show_cards,
    extract_showtimes,
)
from .transformer import LudusTransformer

_FETCH_TIMEOUT = 30


class LudusScraper(BaseScraper):
    """Two-step embed -> detail scraper for ludus.com venues."""

    key = "ludus"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LudusTransformer(club))
        self._comedy_filter = is_comedy_filter_enabled(self.club.source_metadata)
        self._lineup_handler = LineupHandler() if self._comedy_filter else None
        self._comedian_handler = ComedianHandler() if self._comedy_filter else None
        # Populated by collect_scraping_targets so get_data can label each
        # detail page's shows without re-fetching the embed.
        self._titles_by_show_id: Dict[str, str] = {}

    def _subdomain(self) -> Optional[str]:
        return (self.club.source_metadata or {}).get("ludus_subdomain")

    def _category_id(self) -> Optional[str]:
        cat = (self.club.source_metadata or {}).get("comedy_category_id")
        return str(cat) if cat is not None else None

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch HTML with curl_cffi impersonation (clears Cloudflare)."""
        try:
            async with AsyncSession(impersonate="chrome120", timeout=_FETCH_TIMEOUT) as session:
                response = await session.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            Logger.error(f"{self._log_prefix}: Ludus fetch failed for {url}: {e}", self.logger_context)
            return None

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        subdomain = self._subdomain()
        if not subdomain:
            Logger.warn(
                f"{self._log_prefix}: missing ludus_subdomain metadata",
                self.logger_context,
            )
            return []
        # comedy_category_id is optional: present -> mixed-use category filter;
        # absent -> dedicated comedy venue, keep all cards and scope via the
        # title-pattern allowlist / comedy filter below.
        category_id = self._category_id()

        embed_url = embed_url_for_subdomain(subdomain)
        html = await self._fetch(embed_url)
        if not html:
            self._warn_empty_extraction(embed_url, subject="comedy cards", html=html)
            return []

        cards = extract_show_cards(html, category_id)
        if not cards:
            self._warn_empty_extraction(embed_url, subject="comedy cards", html=html)
            return []

        cards = self._filter_titles(cards)
        if not cards:
            return []

        if self._comedy_filter:
            cards = await self._filter_comedy(cards)
            if not cards:
                return []

        self._titles_by_show_id = {show_id: title for show_id, title in cards}
        Logger.info(
            f"{self._log_prefix}: {len(cards)} comedy show(s) after filtering",
            self.logger_context,
        )
        return [detail_url_for_show(subdomain, show_id) for show_id, _title in cards]

    def _filter_titles(self, cards: List[tuple]) -> List[tuple]:
        """Apply the opt-in include/exclude title-pattern filter to embed cards.

        A dedicated comedy venue (no category tags) still lists non-public rows
        — classes, workshops, camps — on the same embed. ``include_title_patterns``
        keeps only cards whose title matches at least one regex (the comedy-series
        allowlist, e.g. ``["ComedySportz"]``); ``exclude_title_patterns`` drops
        cards whose title matches any regex. Both off by default, so categorized
        mixed-use venues (Park Theatre) are unchanged. Pattern compilation is the
        shared :meth:`BaseScraper.compile_title_patterns`; the include-then-exclude
        loop mirrors ticketweb / sellingticket.
        """
        include = self.compile_title_patterns("include_title_patterns")
        exclude = self.compile_title_patterns("exclude_title_patterns")
        if not include and not exclude:
            return cards

        kept: List[tuple] = []
        for show_id, title in cards:
            if include and not any(p.search(title) for p in include):
                continue
            if exclude and any(p.search(title) for p in exclude):
                continue
            kept.append((show_id, title))

        dropped = len(cards) - len(kept)
        if dropped:
            Logger.info(
                f"{self._log_prefix}: title filter dropped {dropped} of "
                f"{len(cards)} card(s); {len(kept)} kept",
                self.logger_context,
            )
        return kept

    async def _filter_comedy(self, cards: List[tuple]) -> List[tuple]:
        """Drop category mis-tags by layering the shared comedy filter on titles.

        The category id is a coarse venue tag (e.g. a tribute band can be
        mis-tagged comedy); ``select_comedy_titles`` keeps only titles with a
        comedy keyword OR a known comedian name.
        """
        titles = [title for _show_id, title in cards if title]
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
        kept = [(show_id, title) for show_id, title in cards if title in kept_titles]
        Logger.info(
            f"{self._log_prefix}: comedy filter kept {len(kept)}/{len(cards)} card(s)",
            self.logger_context,
        )
        return kept

    async def get_data(self, target: ScrapingTarget) -> Optional[LudusPageData]:
        html = await self._fetch(target)
        if not html:
            self._warn_empty_extraction(target, html=html)
            return None

        showtimes = extract_showtimes(html)
        if not showtimes:
            self._warn_empty_extraction(target, subject="showtimes", html=html)
            return None

        title = self._title_for_target(target)
        events = [
            LudusEvent(title=title, start=start, show_url=target)
            for start in showtimes
        ]
        return LudusPageData(event_list=events)

    def _title_for_target(self, target: str) -> str:
        match = re.search(r"show_id=(\d+)", target)
        show_id = match.group(1) if match else ""
        return self._titles_by_show_id.get(show_id, "") or self.club.name
