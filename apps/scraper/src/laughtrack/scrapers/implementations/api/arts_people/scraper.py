"""Generic Arts-People (Neon One) comedy scraper.

Venues selling through Arts-People publish a public ticketing list page at
``https://app.arts-people.com/index.php?ticketing={shortName}`` (one row per
current production), and a per-show page at ``index.php?show={id}`` whose
``TBLperformances`` table lists each bookable performance date. Both pages are
static HTML (curl_cffi chrome impersonation suffices), so no JS rendering or API
key is required.

Pipeline (multi_step / html):
    1. collect_scraping_targets(): fetch the list page, parse the production rows,
       apply the opt-in title allow/block filter, and return one ``?show={id}``
       detail URL per kept production.
    2. get_data(detail_url): fetch the show page and extract one
       ``ArtsPeopleEvent`` per dated performance.
    3. transformation_pipeline: ArtsPeopleEvent.to_show() -> Show objects.

Per-venue configuration comes from ``scraping_sources``:
  - ``source_url`` — the venue's Arts-People ticketing list page (required).
  - ``metadata.include_title_patterns`` / ``metadata.exclude_title_patterns`` —
    optional case-insensitive regex allow/block lists applied to production
    titles. Both OFF by default, so a pure-comedy Arts-People org is unchanged.
    Dinner theatres that mix musicals/plays with a comedy series set
    ``include_title_patterns`` to a comedy allowlist (e.g. ``["comedy","improv",
    "stand[ -]?up","comedian","open mic"]``) so only the comedy productions are
    scraped.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import ArtsPeoplePageData
from .extractor import extract_performances, extract_show_links
from .transformer import ArtsPeopleEventTransformer


class ArtsPeopleScraper(BaseScraper):
    """Two-phase HTML scraper for venues hosted on an Arts-People (Neon One) org."""

    key = "arts_people"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ArtsPeopleEventTransformer(club))

    def _keep_title(self, title: str, include, exclude) -> bool:
        """Apply the opt-in include/exclude title filter (mirrors ticketweb /
        the_events_calendar). A title is kept when it matches at least one
        include pattern (when any are configured) AND no exclude pattern."""
        if include and not any(p.search(title) for p in include):
            return False
        if exclude and any(p.search(title) for p in exclude):
            return False
        return True

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        list_url = self.club.scraping_url
        if not list_url:
            Logger.warn(
                f"{self._log_prefix}: no source_url configured for Arts-People list page",
                self.logger_context,
            )
            return []
        list_url = URLUtils.normalize_url(list_url)

        try:
            html = await self.fetch_html(list_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch Arts-People list page {list_url}: {e}",
                self.logger_context,
            )
            return []

        if not html:
            self._warn_empty_extraction(list_url, subject="show links", html=html)
            return []

        pairs = extract_show_links(html, base_url=list_url)
        if not pairs:
            self._warn_empty_extraction(list_url, subject="show links", html=html)
            return []

        include = self.compile_title_patterns("include_title_patterns")
        exclude = self.compile_title_patterns("exclude_title_patterns")

        targets: List[ScrapingTarget] = []
        for title, detail_url in pairs:
            if self._keep_title(title, include, exclude):
                targets.append(detail_url)

        dropped = len(pairs) - len(targets)
        if dropped:
            Logger.info(
                f"{self._log_prefix}: title filter dropped {dropped} of {len(pairs)} "
                f"production(s); {len(targets)} kept",
                self.logger_context,
            )
        return targets

    async def get_data(self, target: ScrapingTarget) -> Optional[ArtsPeoplePageData]:
        url = str(target)
        try:
            html = await self.fetch_html(url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch Arts-People show page {url}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            self._warn_empty_extraction(url, subject="performances", html=html)
            return None

        events = extract_performances(html, show_page_url=url)
        if not events:
            self._warn_empty_extraction(url, subject="performances", html=html)
            return None

        Logger.info(
            f"{self._log_prefix}: Parsed {len(events)} performance(s) from {url}",
            self.logger_context,
        )
        return ArtsPeoplePageData(event_list=events)
