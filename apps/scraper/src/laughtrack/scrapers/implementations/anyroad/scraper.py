"""AnyRoad platform scraper.

AnyRoad (app.anyroad.com) is a reusable experiences-booking platform. A venue
embeds a widget keyed by a ``plugin_id``; the widget pulls its calendar from
``/plugins/api/v3/experiences?plugin_id=<id>&page=N``. That endpoint is
Cloudflare-gated to plain HTTP but is cleared by curl_cffi's Chrome
impersonation (the default ``fetch_json`` session), with the shared Playwright
browser as the automatic fallback.

Wiring (``scraping_sources``): set ``scraper_key='anyroad'`` and put the plugin
id in ``external_id`` (preferred) or ``metadata.plugin_id``; ``source_url`` may
hold the human-facing widget URL (``https://app.anyroad.com/i/plugin/<id>``),
from which the plugin id is parsed as a last resort.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.anyroad.data import AnyRoadPageData
from laughtrack.scrapers.implementations.anyroad.extractor import extract_anyroad_events
from laughtrack.scrapers.implementations.anyroad.transformer import AnyRoadTransformer
from laughtrack.scrapers.utils.comedy_filter import is_comedy_filter_enabled
from laughtrack.shared.types import ScrapingTarget

_EXPERIENCES_API = "https://app.anyroad.com/plugins/api/v3/experiences"

# Defensive upper bound on pagination so a misbehaving API (e.g. one that never
# returns an empty page) cannot spin forever. Rozzie's full calendar is 3 pages.
_MAX_PAGES = 50


class AnyRoadScraper(BaseScraper):
    """Scraper for venues hosted on app.anyroad.com (experiences widget)."""

    key = "anyroad"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(AnyRoadTransformer(club))

    def _resolve_plugin_id(self) -> Optional[str]:
        """Resolve the AnyRoad plugin id from scraping-source config.

        Order: ``external_id`` -> ``metadata.plugin_id`` -> last path segment of
        ``source_url`` (handles ``/i/plugin/<id>`` and ``integrations.../<id>``).
        """
        source = self.club.scraping_source
        if source is not None:
            if source.external_id:
                return source.external_id.strip()
            meta_id = source.metadata.get("plugin_id") if source.metadata else None
            if meta_id:
                return str(meta_id).strip()

        url = self.club.scraping_url
        if url:
            path = urlparse(url if "://" in url else f"https://{url}").path
            segments = [seg for seg in path.split("/") if seg]
            if segments:
                # ".../i/plugin/<id>" or ".../i/plugin/<id>/tours" -> take the
                # segment after "plugin"; otherwise the final path segment.
                if "plugin" in segments:
                    idx = segments.index("plugin")
                    if idx + 1 < len(segments):
                        return segments[idx + 1]
                return segments[-1]
        return None

    @staticmethod
    def _experiences_url(plugin_id: str, page: int) -> str:
        return f"{_EXPERIENCES_API}?plugin_id={plugin_id}&page={page}"

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        plugin_id = self._resolve_plugin_id()
        if not plugin_id:
            Logger.warn(
                f"{self._log_prefix}: no AnyRoad plugin id configured "
                f"(set scraping_sources.external_id or metadata.plugin_id)",
                self.logger_context,
            )
            return []
        # Identifier-based target (like Comedy Cellar's date strings): get_data
        # turns the plugin id into the paginated API calls.
        return [plugin_id]

    async def get_data(self, target: ScrapingTarget) -> Optional[AnyRoadPageData]:
        plugin_id = str(target)
        try:
            records = await self._fetch_all_experiences(plugin_id)
            if not records:
                self._warn_empty_extraction(
                    self._experiences_url(plugin_id, 1),
                    subject="experiences",
                    n_items=0,
                )
                return None

            events = extract_anyroad_events(
                records,
                timezone=self.club.timezone,
                comedy_filter=is_comedy_filter_enabled(self.club.source_metadata),
            )
            if not events:
                self._warn_empty_extraction(
                    self._experiences_url(plugin_id, 1),
                    subject="events",
                    n_items=len(records),
                )
                return None
            return AnyRoadPageData(events)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error fetching AnyRoad experiences for "
                f"plugin '{plugin_id}': {e}",
                self.logger_context,
            )
            return None

    async def _fetch_all_experiences(self, plugin_id: str) -> List[dict]:
        """Walk pages until an empty ``experiences.data`` array (no links/meta)."""
        records: List[dict] = []
        for page in range(1, _MAX_PAGES + 1):
            payload = await self.fetch_json(self._experiences_url(plugin_id, page))
            data = self._page_records(payload)
            if not data:
                break
            records.extend(data)
        return records

    @staticmethod
    def _page_records(payload) -> List[dict]:
        if not isinstance(payload, dict):
            return []
        experiences = payload.get("experiences")
        if not isinstance(experiences, dict):
            return []
        data = experiences.get("data")
        return data if isinstance(data, list) else []

    def transform_data(
        self,
        raw_data: AnyRoadPageData,
        source_url_or_identifier: ScrapingTarget,
    ) -> List[Show]:
        return super().transform_data(raw_data, source_url_or_identifier)
