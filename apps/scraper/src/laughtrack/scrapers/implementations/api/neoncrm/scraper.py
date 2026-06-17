"""Generic NeonCRM (Neon One) comedy scraper.

Venues running on NeonCRM publish a static public event list at
``https://{org}.app.neoncrm.com/eventList.jsp`` (canonical
``/np/clients/{org}/eventList.jsp``), optionally filtered by
``?categoryId={N}``. Each row is server-rendered HTML (curl_cffi chrome
impersonation suffices), so the list page alone yields name + date + detail URL.

Per-venue configuration comes from ``scraping_sources.metadata``:
  - ``neon_org`` — the NeonCRM org slug (e.g. ``oionline``)
  - ``category_ids`` — list of category ids to fetch (e.g. ``[27]`` for
    "Theater Productions", which carries improv / stand-up / plays)

When metadata is present the scraper builds one eventList URL per category;
otherwise it falls back to the club's ``scraping_url`` verbatim. This keeps the
scraper reusable across NeonCRM venues.

Pipeline:
    1. collect_scraping_targets(): build the eventList.jsp URL(s).
    2. get_data(url): fetch the list page, parse the event rows, wrap as
       NeonCRMPageData.
    3. transformation_pipeline: NeonCRMEvent.to_show() -> Show objects.
"""

from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import NeonCRMPageData
from .extractor import extract_events
from .transformer import NeonCRMEventTransformer


class NeonCRMScraper(BaseScraper):
    """Event-list scraper for venues hosted on a NeonCRM (Neon One) org."""

    key = "neoncrm"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(NeonCRMEventTransformer(club))

    def _metadata(self) -> Dict[str, Any]:
        return getattr(self.club, "source_metadata", None) or {}

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        meta = self._metadata()
        org = meta.get("neon_org")
        category_ids = meta.get("category_ids")

        if org and isinstance(category_ids, list) and category_ids:
            base = f"https://{org}.app.neoncrm.com/eventList.jsp"
            return [f"{base}?categoryId={cid}" for cid in category_ids]

        # Fallback: a fully-formed eventList URL configured on the source.
        home_url = self.club.scraping_url
        if not home_url:
            Logger.warn(
                f"{self._log_prefix}: no neon_org/category_ids metadata and no scraping_url",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(home_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[NeonCRMPageData]:
        url = str(target)
        try:
            html = await self.fetch_html(url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch NeonCRM eventList {url}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: NeonCRM eventList returned empty HTML: {url}",
                self.logger_context,
            )
            return None

        events = extract_events(html, base_url=url)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: No event rows parsed from NeonCRM eventList {url}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: Parsed {len(events)} event(s) from NeonCRM eventList {url}",
            self.logger_context,
        )
        return NeonCRMPageData(event_list=events)
