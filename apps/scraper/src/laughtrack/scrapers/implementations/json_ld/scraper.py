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
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
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
            calendar_url = URLUtils.normalize_url(self.club.scraping_url)
            object_type = str(detail_fetch.get("listing_type") or detail_fetch.get("object_type") or "Event")
            url_path = str(detail_fetch.get("url_path") or detail_fetch.get("url_field") or "sameAs")

            Logger.info(
                f"{self._log_prefix}: Fetching JSON-LD index page for detail URLs: {calendar_url}",
                self.logger_context,
            )
            calendar_html = await self._fetch_configured_html(calendar_url)
            if not calendar_html:
                Logger.warn(
                    f"{self._log_prefix}: Empty response from JSON-LD index page: {calendar_url}",
                    self.logger_context,
                )
                return []

            detail_urls = await self._collect_detail_urls(
                calendar_url,
                calendar_html,
                detail_fetch,
                object_type=object_type,
                url_path=url_path,
            )
            if not detail_urls:
                Logger.warn(
                    f"{self._log_prefix}: No JSON-LD detail URLs found from {calendar_url}",
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
            html_content = await self._fetch_configured_html(normalized_url)

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

    def _force_js_rendering(self) -> bool:
        return bool((self.club.source_metadata or {}).get("force_js_rendering"))

    async def _fetch_configured_html(self, url: str) -> Optional[str]:
        normalized_url = URLUtils.normalize_url(url)
        if self._force_js_rendering():
            return await self._fetch_html_with_js(normalized_url)
        return await self.fetch_html(normalized_url)

    async def _collect_detail_urls(
        self,
        calendar_url: str,
        calendar_html: str,
        detail_fetch: dict[str, Any],
        *,
        object_type: str,
        url_path: str,
    ) -> set[str]:
        pages: list[tuple[str, str | None]] = [(calendar_url, calendar_html)]
        visited: set[str] = set()
        detail_urls: set[str] = set()
        max_pages = self._pagination_max_pages(detail_fetch)

        while pages and len(visited) < max_pages:
            page_url, provided_html = pages.pop(0)
            if page_url in visited:
                continue
            visited.add(page_url)

            html = provided_html
            if html is None:
                html = await self._fetch_configured_html(page_url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: Empty response from JSON-LD listing page: {page_url}",
                    self.logger_context,
                )
                continue

            detail_urls.update(
                self._extract_json_ld_detail_urls(
                    html,
                    page_url,
                    object_type=object_type,
                    url_path=url_path,
                )
            )
            detail_urls.update(self._extract_anchor_detail_urls(html, page_url, detail_fetch))

            if not self._pagination_enabled(detail_fetch):
                continue

            for next_url in self._extract_pagination_urls(html, page_url, calendar_url):
                if next_url not in visited and all(next_url != queued_url for queued_url, _ in pages):
                    pages.append((next_url, None))

        if pages:
            Logger.warn(
                f"{self._log_prefix}: stopped JSON-LD listing pagination after {max_pages} pages",
                self.logger_context,
            )

        return detail_urls

    def _extract_json_ld_detail_urls(
        self,
        html: str,
        base_url: str,
        *,
        object_type: str,
        url_path: str,
    ) -> set[str]:
        from .extractor import EventExtractor

        return {
            urljoin(base_url, url)
            for url in EventExtractor.extract_typed_field_values(
                html,
                object_type=object_type,
                field_path=url_path,
            )
        }

    def _extract_anchor_detail_urls(
        self,
        html: str,
        base_url: str,
        detail_fetch: dict[str, Any],
    ) -> set[str]:
        path_prefix = detail_fetch.get("url_path_prefix")
        if not isinstance(path_prefix, str) or not path_prefix:
            return set()

        base = urlparse(base_url)
        allowed_hosts = detail_fetch.get("allowed_hosts")
        if isinstance(allowed_hosts, list):
            hosts = {str(host) for host in allowed_hosts if host}
        else:
            hosts = {base.netloc}
        excluded_suffixes = [
            str(suffix)
            for suffix in detail_fetch.get("exclude_url_path_suffixes", [])
            if suffix
        ]

        urls: set[str] = set()
        soup = BeautifulSoup(html or "", "html.parser")
        for anchor in soup.find_all("a", href=True):
            parsed = urlparse(urljoin(base_url, anchor["href"]))
            if parsed.netloc not in hosts:
                continue
            if not parsed.path.startswith(path_prefix):
                continue
            if any(parsed.path.endswith(suffix) for suffix in excluded_suffixes):
                continue

            urls.add(
                urlunparse((
                    parsed.scheme or "https",
                    parsed.netloc,
                    parsed.path,
                    "",
                    "",
                    "",
                ))
            )
        return urls

    def _extract_pagination_urls(self, html: str, base_url: str, calendar_url: str) -> list[str]:
        base = urlparse(calendar_url)
        listing_path = base.path.rstrip("/")
        urls: list[str] = []
        seen: set[str] = set()
        soup = BeautifulSoup(html or "", "html.parser")

        for anchor in soup.find_all("a", href=True):
            if not self._is_pagination_link(anchor):
                continue

            parsed = urlparse(urljoin(base_url, anchor["href"]))
            if parsed.netloc != base.netloc:
                continue
            if parsed.path.rstrip("/") != listing_path:
                continue

            normalized = urlunparse((
                parsed.scheme or "https",
                parsed.netloc,
                parsed.path,
                "",
                parsed.query,
                "",
            ))
            if normalized in seen:
                continue
            seen.add(normalized)
            urls.append(normalized)
        return urls

    def _pagination_enabled(self, detail_fetch: dict[str, Any]) -> bool:
        raw = detail_fetch.get("pagination")
        return isinstance(raw, dict) and raw.get("enabled") is not False

    def _pagination_max_pages(self, detail_fetch: dict[str, Any]) -> int:
        raw = detail_fetch.get("pagination")
        if not isinstance(raw, dict):
            return 1
        try:
            return max(1, int(raw.get("max_pages", 1)))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _is_pagination_link(anchor) -> bool:
        rel = anchor.get("rel") or []
        if isinstance(rel, str):
            rel = [rel]
        rel_values = {str(value).lower() for value in rel}
        if "next" in rel_values:
            return True

        aria_label = str(anchor.get("aria-label", "")).strip().lower()
        if aria_label == "next" or aria_label.startswith("next "):
            return True

        label = " ".join(
            part.strip().lower()
            for part in [
                aria_label,
                anchor.get_text(" ", strip=True),
                " ".join(anchor.get("class", [])),
            ]
            if part
        )
        return "pagination" in label and ("next" in label or "page" in label)
