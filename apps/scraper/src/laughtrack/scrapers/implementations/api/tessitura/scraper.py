"""Generic Tessitura comedy scraper (WordPress REST integration).

Many Tessitura venue operators (e.g. CAPA — the Columbus Association for the
Performing Arts, across the Ohio/Palace/Southern/Lincoln theatres and the
Davidson at the Riffe Center) run a WordPress plugin that mirrors their
Tessitura productions into ``tessi_production`` / ``tessi_performance`` custom
post types, exposed over the standard WP REST API together with a ``genre``
taxonomy. The Tessitura box office itself (``tickets.{org}.com``) is bot- and
queue-protected, so this REST feed is the scrapable seam.

Per-venue configuration is the operator's site root, read from the club's
``scraping_url`` (e.g. ``https://www.capa.com``); the scraper derives the
``/wp-json/wp/v2`` base from it. Optional ``scraping_sources.metadata``
overrides: ``post_type`` (default ``tessi_production``), ``genre_taxonomy``
(default ``genre``), and ``comedy_genre_names`` (comma-separated, default
``comedy``).

Pipeline:
    1. collect_scraping_targets(): return the WP REST base URL for the operator.
    2. get_data(base): discover the comedy genre term(s) from the genre
       taxonomy, page through the comedy productions, and wrap them as
       TessituraPageData (one TessituraEvent per production).
    3. transformation_pipeline: TessituraEvent.to_show() -> Show objects.
"""

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import TessituraPageData
from .extractor import discover_comedy_genre_ids, extract_events
from .transformer import TessituraEventTransformer

_DEFAULT_POST_TYPE = "tessi_production"
_DEFAULT_GENRE_TAXONOMY = "genre"
_DEFAULT_COMEDY_NAMES = "comedy"
_PER_PAGE = 100
_MAX_PAGES = 20  # safety cap: 20 * 100 = 2000 productions per genre


class TessituraScraper(BaseScraper):
    """Comedy scraper for Tessitura operators on the WordPress REST integration."""

    key = "tessitura"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TessituraEventTransformer(club))

    def _wp_rest_base(self) -> Optional[str]:
        """Derive the ``/wp-json/wp/v2`` base from the club's scraping_url."""
        raw = self.club.scraping_url
        if not raw:
            return None
        normalized = URLUtils.normalize_url(raw)
        if "/wp-json/" in normalized:
            return normalized.rstrip("/")
        parsed = urlparse(normalized)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return f"{origin}/wp-json/wp/v2"

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        base = self._wp_rest_base()
        if not base:
            Logger.warn(
                f"{self._log_prefix}: Club has no scraping_url configured",
                self.logger_context,
            )
            return []
        return [base]

    async def get_data(self, target: ScrapingTarget) -> Optional[TessituraPageData]:
        base = str(target).rstrip("/")

        # Use-time config reads so a source can retune without code changes.
        post_type = self.club.metadata_value("post_type") or _DEFAULT_POST_TYPE
        genre_taxonomy = self.club.metadata_value("genre_taxonomy") or _DEFAULT_GENRE_TAXONOMY
        comedy_names_raw = self.club.metadata_value("comedy_genre_names") or _DEFAULT_COMEDY_NAMES
        comedy_names = tuple(n.strip() for n in comedy_names_raw.split(",") if n.strip())

        genre_terms = await self.fetch_json(f"{base}/{genre_taxonomy}?per_page={_PER_PAGE}")
        if not isinstance(genre_terms, list):
            Logger.warn(
                f"{self._log_prefix}: {genre_taxonomy} taxonomy returned no terms at {base}",
                self.logger_context,
            )
            return None

        comedy_ids = discover_comedy_genre_ids(genre_terms, target_names=comedy_names)
        if not comedy_ids:
            Logger.warn(
                f"{self._log_prefix}: No comedy genre term found among "
                f"{[t.get('name') for t in genre_terms]}",
                self.logger_context,
            )
            return None

        productions: List[dict] = []
        for genre_id in comedy_ids:
            productions.extend(
                await self._fetch_productions(base, post_type, genre_taxonomy, genre_id)
            )

        events = extract_events(productions)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: No comedy productions extracted from {base}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: Extracted {len(events)} comedy production(s) from {base}",
            self.logger_context,
        )
        return TessituraPageData(event_list=events)

    async def _fetch_productions(
        self, base: str, post_type: str, genre_taxonomy: str, genre_id: int
    ) -> List[dict]:
        """Page through ``{post_type}?{genre_taxonomy}={genre_id}`` until exhausted.

        The WP REST filter query parameter for a custom taxonomy is the
        taxonomy's own slug (its ``rest_base``), so it tracks any override.
        """
        collected: List[dict] = []
        for page in range(1, _MAX_PAGES + 1):
            url = (
                f"{base}/{post_type}"
                f"?{genre_taxonomy}={genre_id}&per_page={_PER_PAGE}&page={page}"
            )
            try:
                page_items = await self.fetch_json(url)
            except Exception as e:
                # Defensive terminator for genuine fetch failures (e.g. the WP
                # 400 "invalid page number" surfacing as a raised RequestsError
                # when the Playwright fallback is disabled or fails).
                Logger.info(
                    f"{self._log_prefix}: pagination stopped at page {page} ({e})",
                    self.logger_context,
                )
                break
            # Normal terminator: once `page` exceeds the page count WP returns a
            # 400, which fetch_json's Playwright fallback recovers as the JSON
            # error *object* ({"code": "rest_post_invalid_page_number", ...}) —
            # a dict, not a list — so this guard ends the loop without raising.
            if not isinstance(page_items, list) or not page_items:
                break
            collected.extend(page_items)
            if len(page_items) < _PER_PAGE:
                break
        return collected
