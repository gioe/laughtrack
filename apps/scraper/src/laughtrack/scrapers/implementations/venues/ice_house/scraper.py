"""
Tockify scraper implementation.

Venues publishing their calendar via the Tockify embedded calendar widget
(tockify.com) store the full API URL in club.scraping_url, e.g.:

  https://tockify.com/api/ngevent?calname=theicehouse&max=200

The scraper appends a startms timestamp so only upcoming events are returned.
Each event includes a title, start timestamp (milliseconds), and a ShowClix
ticket URL in the customButtonLink field. The scraper normalizes embed URLs
(embed.showclix.com) to public URLs (www.showclix.com).

No authentication or special headers are required for the Tockify API.

Currently used by: Ice House Comedy Club (Pasadena, CA).
A second Tockify venue can be onboarded with only a DB row — no Python changes.
"""

import time
from typing import List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ice_house import IceHouseEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import IceHousePageData
from .extractor import IceHouseExtractor
from .transformer import IceHouseEventTransformer

# Safety cap so a Tockify API that always returns hasNext=true cannot stall the
# scrape forever. Each page is max=200; 20 pages = 4000 upcoming events, well
# above any realistic venue calendar.
_TOCKIFY_MAX_PAGES = 20


class IceHouseScraper(BaseScraper):
    """
    Generic Tockify scraper — reads club.scraping_url for the API base URL.

    Fetches upcoming events from the Tockify calendar API.
    The startms parameter is set to the current time so only upcoming events
    are returned.
    """

    key = "tockify"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(IceHouseEventTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the Tockify API URL with the current timestamp as startms."""
        now_ms = int(time.time() * 1000)
        return [f"{self.club.scraping_url}&startms={now_ms}"]

    async def get_data(self, url: str) -> Optional[IceHousePageData]:
        """
        Fetch events from the Tockify API and return extracted IceHouseEvents.

        The Tockify ngevent endpoint caps each response at max=200 events and
        signals more pages via metaData.hasNext. This method loops while
        hasNext is true, re-fetching with startms advanced one millisecond
        past the highest start_ms seen, so venues with >200 upcoming events
        are paginated rather than silently truncated.

        Args:
            url: The Tockify API URL (from collect_scraping_targets)

        Returns:
            IceHousePageData containing events, or None if no events found
        """
        all_events: List[IceHouseEvent] = []
        current_url = url
        last_response: Optional[dict] = None
        page_count = 0

        try:
            while page_count < _TOCKIFY_MAX_PAGES:
                page_count += 1
                await self.rate_limiter.await_if_needed(current_url)

                response = await self.fetch_json(current_url)
                last_response = response
                if not response:
                    if page_count == 1:
                        self._warn_empty_extraction(current_url, subject="data", payload=response)
                        return None
                    break

                events = IceHouseExtractor.extract_events(response, api_url=current_url)
                all_events.extend(events)

                meta = response.get("metaData") or {}
                if not meta.get("hasNext"):
                    break

                if not events:
                    Logger.warn(
                        f"{self._log_prefix}: metaData.hasNext=true but no events parsed "
                        f"from page {page_count} of {current_url}; stopping pagination",
                        self.logger_context,
                    )
                    break

                next_startms = max(e.start_ms for e in events) + 1
                current_url = self._advance_startms(url, next_startms)
            else:
                Logger.warn(
                    f"{self._log_prefix}: hit Tockify page cap ({_TOCKIFY_MAX_PAGES}) for "
                    f"{url}; metaData.hasNext may still be true — possible truncation",
                    self.logger_context,
                )

            if not all_events:
                self._warn_empty_extraction(url, payload=last_response)
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(all_events)} events across "
                f"{page_count} page(s) from {url}",
                self.logger_context,
            )
            return IceHousePageData(event_list=all_events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None

    @staticmethod
    def _advance_startms(url: str, new_startms: int) -> str:
        """Return url with the startms query parameter replaced by new_startms."""
        parsed = urlparse(url)
        params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "startms"]
        params.append(("startms", str(new_startms)))
        return urlunparse(parsed._replace(query=urlencode(params)))
