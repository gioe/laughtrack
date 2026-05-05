"""Palm Beach Improv at the Kravis Center scraper.

The legacy palmbeachimprov.com domain redirects to the Kravis Center's Improv
page. SeatEngine venue 350 still exists but currently returns no shows; the
active source is Kravis' WordPress AJAX performance calendar:

  /wp-admin/admin-ajax.php?action=performance-list-by-month&date=<month>

That endpoint returns the center-wide performance list, so this scraper verifies
each candidate detail page contains "Palm Beach Improv" before producing shows.
"""

from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import PalmBeachImprovPageData
from .extractor import PalmBeachImprovExtractor
from .transformer import PalmBeachImprovEventTransformer


_AJAX_URL = (
    "https://www.kravis.org/wp-admin/admin-ajax.php"
    "?action=performance-list-by-month&date={date}"
)
_MONTH_SCAN_COUNT = 12


class PalmBeachImprovScraper(BaseScraper):
    """Scraper for Palm Beach Improv at the Kravis Center."""

    key = "palm_beach_improv"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            PalmBeachImprovEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        """Return Kravis calendar AJAX URLs from the current month forward."""
        now = datetime.now()
        targets: List[str] = []
        for offset in range(_MONTH_SCAN_COUNT):
            month_index = (now.month - 1) + offset
            year = now.year + month_index // 12
            month = month_index % 12 + 1
            month_start = datetime(year, month, 1, 4, 0)
            date_param = quote(month_start.strftime("%a, %d %b %Y %H:%M:%S GMT"))
            targets.append(_AJAX_URL.format(date=date_param))
        return targets

    async def get_data(self, url: str) -> Optional[PalmBeachImprovPageData]:
        """Fetch one Kravis calendar month and extract Palm Beach Improv shows."""
        try:
            html = await self._fetch_html_with_js(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty Kravis calendar response for {url}",
                    self.logger_context,
                )
                return None

            performances = PalmBeachImprovExtractor.parse_ajax_response(html)
            if not performances:
                Logger.info(
                    f"{self._log_prefix}: no Kravis performances in {url}",
                    self.logger_context,
                )
                return None

            improv_performances = []
            for performance in performances:
                link = str(performance.get("link") or "").strip()
                if not link:
                    continue

                # The Kravis AJAX feed is center-wide (~50 performances/month
                # × 12 months); without a pre-filter we Playwright-fetch every
                # ballet/opera/recital detail page just to discard it. Skip
                # entries with no comedy keyword and no Improv-room location.
                if not PalmBeachImprovExtractor.looks_like_improv_candidate(
                    performance
                ):
                    continue

                detail_html = await self._fetch_html_with_js(link)
                if PalmBeachImprovExtractor.detail_page_is_improv(detail_html or ""):
                    improv_performances.append(performance)
                else:
                    Logger.info(
                        f"{self._log_prefix}: skipped Improv-candidate non-Improv event {link}",
                        self.logger_context,
                    )

            events = PalmBeachImprovExtractor.events_from_performances(
                improv_performances
            )
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no Palm Beach Improv shows found in {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} Palm Beach Improv shows",
                self.logger_context,
            )
            return PalmBeachImprovPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching Kravis calendar {url}: {e}",
                self.logger_context,
            )
            return None
