"""Generic AXS-skinned venue homepage scraper.

Many AXS/AEG venues run a stock venue website whose homepage renders an
upcoming-events slider (royalSlider ``rsCaption`` cards) with each show's name,
date, the venue's own detail URL, and an AXS ticket link
(``axs.com/events/<id>/...?skin=<venue>``). The ``axs.com`` detail pages are
DataDome-protected, but the venue homepage is plain server-rendered HTML, so it
is the scrapable seam — handled here without ever touching ``axs.com``.

Per-venue configuration is the venue homepage URL, read from the club's
``scraping_url`` (e.g. ``https://agoracleveland.com``). The homepage carries no
show time, so each Show uses ``scraping_sources.metadata.default_show_time``
(``HH:MM``, default 19:00) localized to the club timezone.

Pipeline:
    1. collect_scraping_targets(): return the venue homepage URL.
    2. get_data(url): fetch the homepage, parse the event cards, wrap as
       AXSPageData.
    3. transformation_pipeline: AXSEvent.to_show() -> Show objects.
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import AXSPageData
from .extractor import extract_events
from .transformer import AXSEventTransformer


class AXSVenueScraper(BaseScraper):
    """Homepage scraper for AXS-skinned venue websites."""

    key = "axs"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(AXSEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        home_url = self.club.scraping_url
        if not home_url:
            Logger.warn(
                f"{self._log_prefix}: Club has no scraping_url configured",
                self.logger_context,
            )
            return []
        return [URLUtils.normalize_url(home_url)]

    async def get_data(self, target: ScrapingTarget) -> Optional[AXSPageData]:
        try:
            html = await self.fetch_html(target)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Failed to fetch AXS venue homepage {target}: {e}",
                self.logger_context,
            )
            return None

        if not html:
            Logger.warn(
                f"{self._log_prefix}: AXS venue homepage returned empty HTML: {target}",
                self.logger_context,
            )
            return None

        events = extract_events(html)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: No event cards parsed from AXS venue homepage {target}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: Parsed {len(events)} event(s) from AXS venue homepage {target}",
            self.logger_context,
        )
        return AXSPageData(event_list=events)
