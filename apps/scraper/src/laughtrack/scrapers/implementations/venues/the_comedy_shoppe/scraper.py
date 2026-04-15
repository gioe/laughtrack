"""ShowSlinger scraper for The Comedy Shoppe (club 327).

Fetches events from the ShowSlinger promo_widget_v3/combo_widget endpoint.
The widget is Cloudflare-protected but curl-cffi's TLS fingerprint
impersonation bypasses it when the correct secure_code is included
in the URL query string.

The scraping_url stored in the DB should be the full widget URL including
the secure_code and origin_url parameters, e.g.:
  https://app.showslinger.com/promo_widget_v3/combo_widget?id=238&secure_code=ec8183215e&origin_url=https://jjcomedy.com/calendar/
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ShowSlingerPageData
from .extractor import ShowSlingerExtractor
from .transformer import ShowSlingerEventTransformer


class ShowSlingerScraper(BaseScraper):
    """Scraper for venues using the ShowSlinger ticketing platform.

    The scraping_url should point to the promo_widget_v3/combo_widget endpoint
    with the venue's id and secure_code query parameters.
    """

    key = "show_slinger"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ShowSlingerEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[ShowSlingerPageData]:
        try:
            html_content = await self.fetch_html(url)
            if not html_content:
                return None

            event_list = ShowSlingerExtractor.extract_events(html_content)
            return ShowSlingerPageData(event_list=event_list)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting data from {url}: {e}",
                self.logger_context,
            )
            return None
