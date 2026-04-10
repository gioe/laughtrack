"""
Generic SeatEngine white-label website scraper.

Some SeatEngine venues serve shows through a white-label frontend
(e.g., bananascomedyclub.com) while the SeatEngine v1 API returns 0 events.
This scraper bypasses the API entirely and scrapes the venue's own website:

1. Fetches the /events listing page to discover event detail URLs
2. Fetches each event detail page for its JSON-LD Event markup
3. Reuses the standard JsonLd extraction and transformation pipeline

To onboard a new club: set scraper='seatengine_web' and scraping_url to
the venue's website root (e.g., 'https://www.bananascomedyclub.com').
No Python changes needed.
"""

import re
from typing import List

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.shared.types import ScrapingTarget


class SeatEngineWebScraper(JsonLdScraper):
    """Scrapes SeatEngine white-label sites via their /events listing page."""

    key = "seatengine_web"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Fetch the /events page and extract individual event page URLs."""
        events_url = f"{self.club.scraping_url.rstrip('/')}/events"
        html = await self.fetch_html(events_url)
        if not html:
            Logger.warn(
                f"{self._log_prefix}: could not fetch events listing at {events_url}",
                self.logger_context,
            )
            return []

        event_ids = sorted(set(re.findall(r'/events/(\d+)', html)))
        if not event_ids:
            Logger.warn(
                f"{self._log_prefix}: no event links found on {events_url}",
                self.logger_context,
            )
            return []

        base = self.club.scraping_url.rstrip("/")
        targets = [f"{base}/events/{eid}" for eid in event_ids]
        Logger.info(
            f"{self._log_prefix}: discovered {len(targets)} event pages to scrape",
            self.logger_context,
        )
        return targets
