"""
Tockify scraper implementation.

Venues publishing their calendar via the Tockify embedded calendar widget
(tockify.com) store the full API URL in club.scraping_url, e.g.:

  https://tockify.com/api/ngevent?calname=theicehouse&max=200

The scraper appends a startms timestamp so only upcoming events are returned.
Each event includes a title, start timestamp (milliseconds), and a ShowClix
ticket URL in the customButtonLink field. The scraper normalizes embed URLs
(embed.showclix.com) to public URLs (www.showclix.com).

Ticket prices (TASK-2838): the Tockify ngevent payload has no structured price
keys, so each event's ShowClix/Leap ticket page (customButtonLink, which
resolves to events.leapevents.com) is fetched once per distinct URL and the
lowest per-tier price is read from its schema.org JSON-LD Event.offers block
(~90% of live pages carry it; verified 2026-06-12). The cheaper alternative —
regexing dollar amounts out of content.description.text (~78% of events) — was
rejected: the marketing copy also carries non-ticket amounts (item minimums,
package upsells) with no way to tell them apart, and it disappears whenever the
venue trims the blurb, while the JSON-LD offers are structured per-tier base
prices. Pages lacking JSON-LD (the seated-sales variant, ~10% of pages) fall
back to the ShowClix seated API via the embedded var EVENT event_id
(TASK-2848); only when that also misses does the event keep price=None.

No authentication or special headers are required for the Tockify API.

Currently used by: Ice House Comedy Club (Pasadena, CA).
A second Tockify venue can be onboarded with only a DB row — no Python changes.
"""

import re
import time
from typing import List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from laughtrack.core.clients.showclix.client import ShowclixAPIClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ice_house import IceHouseEvent, normalize_showclix_url
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.base.detail_price_mixin import DetailPagePriceMixin
from laughtrack.shared.types import ScrapingTarget

from .data import IceHousePageData
from .extractor import IceHouseExtractor
from .transformer import IceHouseEventTransformer

# Safety cap so a Tockify API that always returns hasNext=true cannot stall the
# scrape forever. Each page is max=200; 20 pages = 4000 upcoming events, well
# above any realistic venue calendar.
_TOCKIFY_MAX_PAGES = 20

# Seated-sales ShowClix pages embed the numeric event id in an inline script:
#   var EVENT = {"event_id":"10341917","event":"..."}
_EVENT_ID_RE = re.compile(r'"event_id"\s*:\s*"(\d+)"')


class IceHouseScraper(DetailPagePriceMixin, BaseScraper):
    """
    Generic Tockify scraper — reads club.scraping_url for the API base URL.

    Fetches upcoming events from the Tockify calendar API.
    The startms parameter is set to the current time so only upcoming events
    are returned. Ticket prices are attached from each event's ShowClix/Leap
    ticket page JSON-LD via DetailPagePriceMixin.
    """

    key = "tockify"

    _detail_price_log_subject = "ticket-page"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.showclix_client = ShowclixAPIClient(club)
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
                    Logger.warn(
                        f"{self._log_prefix}: empty/None response on page {page_count} of "
                        f"{current_url}; returning {len(all_events)} event(s) collected so far "
                        f"(possible partial truncation)",
                        self.logger_context,
                    )
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

            await self._attach_detail_page_prices(all_events, self._ticket_price_url)

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
    def _ticket_price_url(event: IceHouseEvent) -> Optional[str]:
        """Normalized ShowClix/Leap ticket URL for an event's price fetch.

        Events without a ticket button (Tockify detail-url fallback pages
        carry no offers) keep price=None.
        """
        return normalize_showclix_url(event.ticket_url) if event.ticket_url else None

    async def _fallback_detail_page_price(self, url: str, html: str) -> Optional[float]:
        """ShowClix seated-API fallback for ticket pages without JSON-LD offers.

        The seated-sales page variant (~10% of Ice House ticket pages,
        TASK-2838 residue) embeds no JSON-LD Event block; it carries the
        numeric event id inline instead. Resolve it through the ShowClix
        seated API, mirroring comedy_store's slug-to-event_id path
        (TASK-2841).
        """
        match = _EVENT_ID_RE.search(html)
        if not match:
            return None
        event_data = await self.showclix_client.get_event_data(match.group(1))
        if not event_data:
            return None
        try:
            price = float(event_data.get_primary_price())
        except (TypeError, ValueError):
            return None
        # A 0.00 seated price level is a placeholder/comp tier, not proof the
        # show is free — keep price-unknown per the tickets-are-access-records
        # convention (TASK-2827).
        return price if price > 0 else None

    @staticmethod
    def _advance_startms(url: str, new_startms: int) -> str:
        """Return url with the startms query parameter replaced by new_startms."""
        parsed = urlparse(url)
        params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k != "startms"]
        params.append(("startms", str(new_startms)))
        return urlunparse(parsed._replace(query=urlencode(params)))
