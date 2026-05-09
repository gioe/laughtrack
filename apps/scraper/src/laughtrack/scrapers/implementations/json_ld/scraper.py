"""
Simplified JSON-LD scraper implementation using standardized project patterns.

This implementation leverages the project's architectural abstractions:
- BaseScraper pipeline for standard workflow
- Built-in fetch methods with error handling and retries
- URL discovery manager for pagination support
- Standardized error handling and logging
- Proper session management and cleanup

Clean single-responsibility architecture:
- JsonLdExtractor: HTML → JSON-LD dictionaries
- JSONLdTransformer: JSON-LD dictionaries → Show objects
- JsonLdScraper: Orchestrates extraction and transformation
"""

from typing import Any, Optional, TYPE_CHECKING
from urllib.parse import urljoin

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from .transformer import JsonLdTransformer

if TYPE_CHECKING:
    # Only imported for type hints to avoid heavy imports at module import time
    from .data import JsonLdPageData
    from .extractor import EventExtractor  # noqa: F401


class JsonLdScraper(BaseScraper):
    """
    Simplified JSON-LD scraper using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (discover_urls → extract_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Uses URL discovery manager for pagination support
    4. Follows established error handling and logging patterns
    5. Separates concerns: extraction vs transformation
    """

    key = "json_ld"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def scrape_async(self) -> list[Show]:
        """Scrape either a single JSON-LD page or metadata-configured detail pages."""
        detail_fetch = self._detail_fetch_config()
        if not detail_fetch:
            return await super().scrape_async()

        try:
            from .extractor import EventExtractor

            calendar_url = URLUtils.normalize_url(self.club.scraping_url)
            object_type = str(detail_fetch.get("listing_type") or detail_fetch.get("object_type") or "Event")
            url_path = str(detail_fetch.get("url_path") or detail_fetch.get("url_field") or "sameAs")

            Logger.info(
                f"{self._log_prefix}: Fetching JSON-LD index page for detail URLs: {calendar_url}",
                self.logger_context,
            )
            calendar_html = await self.fetch_html(calendar_url)
            if not calendar_html:
                Logger.warn(
                    f"{self._log_prefix}: Empty response from JSON-LD index page: {calendar_url}",
                    self.logger_context,
                )
                return []

            detail_urls = EventExtractor.extract_typed_field_values(
                calendar_html,
                object_type=object_type,
                field_path=url_path,
            )
            if not detail_urls:
                Logger.warn(
                    f"{self._log_prefix}: No JSON-LD detail URLs found via {object_type}.{url_path} on {calendar_url}",
                    self.logger_context,
                )
                return []

            targets = sorted({urljoin(calendar_url, url) for url in detail_urls})
            Logger.info(
                f"{self._log_prefix}: Found {len(targets)} JSON-LD detail pages to process",
                self.logger_context,
            )

            raw_data_results = await self._fetch_all_raw_data(targets)
            all_shows = self._transform_all_raw_data(raw_data_results)

            Logger.info(
                f"{self._log_prefix}: Scraped {len(all_shows)} total shows from {len(targets)} detail pages",
                self.logger_context,
            )
            return all_shows

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Scraping failed: {e}", self.logger_context)
            raise
        finally:
            await self._cleanup_resources()

    async def get_data(self, url: str) -> Optional["JsonLdPageData"]:
        """
        Extract JSON-LD data from a webpage using standardized fetch methods.

        Returns raw JSON-LD dictionaries, not transformed objects.

        Honors the optional ``location_name_filter`` metadata key on
        scraping_sources: when set, only events whose ``location.name``
        contains the configured substring are kept (case-sensitive
        match, preserving the prior BrewHaHaRiverExtractor semantics —
        configure the metadata value with the exact venue casing).
        This supports multi-venue calendar pages (e.g.
        comedycraftbeer.com/calendar listing every Comedy Craft Beer
        venue on one page) without a bespoke per-venue scraper class.
        """
        try:
            # Local imports to prevent circular imports during module discovery
            from .data import JsonLdPageData
            from .extractor import EventExtractor
            # Use BaseScraper's standardized fetch_html with built-in error handling
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)

            detail_fetch = self._detail_fetch_config()
            same_as_override = (
                normalized_url
                if detail_fetch and detail_fetch.get("set_same_as_to_detail_url")
                else None
            )

            # Parse HTML and extract JSON-LD (events only)
            event_list = EventExtractor.extract_events(
                html_content,
                same_as_override=same_as_override,
            )

            if not event_list:
                if html_content:
                    Logger.warn(
                        f"{self._log_prefix}: Page loaded but contained no JSON-LD events: {normalized_url}",
                        self.logger_context,
                    )
                return None

            location_filter = self.club.metadata_value("location_name_filter")
            if location_filter:
                before = len(event_list)
                event_list = [
                    e for e in event_list
                    if e.location and location_filter in e.location.name
                ]
                Logger.info(
                    f"{self._log_prefix}: location_name_filter '{location_filter}' "
                    f"kept {len(event_list)}/{before} events",
                    self.logger_context,
                )
                if not event_list:
                    return None

            return JsonLdPageData(event_list)

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None

    def _detail_fetch_config(self) -> Optional[dict[str, Any]]:
        raw = (self.club.source_metadata or {}).get("detail_fetch")
        if not isinstance(raw, dict):
            return None
        if raw.get("enabled") is False:
            return None
        return raw
