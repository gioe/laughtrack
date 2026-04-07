"""Flappers Comedy Club scraper.

The Flappers calendar is server-rendered PHP at:
  https://www.flapperscomedy.com/site/calendar_test_2025.php?month=N&year=YYYY

Each page contains <form> elements with <button class="event-btn">
holding show titles, times, rooms, and event IDs.

Pipeline:
  1. collect_scraping_targets() -> monthly calendar URLs (current + next 2 months)
  2. get_data(url)              -> fetch calendar HTML -> extract FlappersEvent objects
                                   -> fetch each show detail page for tickets + lineup
  3. transformation_pipeline    -> FlappersEvent.to_show() -> Show objects
"""

import asyncio
import random
from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import FlappersPageData
from .extractor import FlappersEventExtractor
from .transformer import FlappersEventTransformer

_SCRAPE_WINDOW_MONTHS = 3
_DETAIL_CONCURRENCY = 2
_DETAIL_BASE_URL = "https://www.flapperscomedy.com/site/shows.php?event_id="
_DETAIL_DELAY_MIN = 0.3
_DETAIL_DELAY_MAX = 0.8
_CF_MAX_RETRIES = 3
_CF_BASE_DELAY = 3.0
_CF_MAX_DELAY = 30.0
_CF_CHALLENGE_MIN_LEN = 50_000


class FlappersComedyClubScraper(BaseScraper):
    """Scraper for Flappers Comedy Club via server-rendered PHP calendar."""

    key = "flappers"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            FlappersEventTransformer(club)
        )

    async def collect_scraping_targets(self) -> List[str]:
        today = date.today()
        base = self.club.scraping_url.rstrip("/")
        targets = []
        for i in range(_SCRAPE_WINDOW_MONTHS):
            d = today + relativedelta(months=i)
            targets.append(f"{base}?month={d.month}&year={d.year}")

        Logger.info(
            f"{self._log_prefix}: generated {len(targets)} monthly calendar URLs",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[FlappersPageData]:
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response from {url}",
                    self.logger_context,
                )
                return None

            tz = self.club.timezone or "America/Los_Angeles"
            events = FlappersEventExtractor.extract_shows(html, url=url, timezone=tz)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no shows found in {url}",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} show(s) from {url}",
                self.logger_context,
            )

            # Enrich events with detail page data (tickets, lineup, description)
            await self._enrich_events(events)

            return FlappersPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error scraping {url}: {e}",
                self.logger_context,
            )
            return None

    async def _enrich_events(self, events: list) -> None:
        """Fetch show detail pages with Cloudflare-aware retry and inter-request delays."""
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        cf_blocks = 0

        async def fetch_detail(event):
            nonlocal cf_blocks
            async with sem:
                # Random delay between requests to avoid triggering Cloudflare
                await asyncio.sleep(
                    random.uniform(_DETAIL_DELAY_MIN, _DETAIL_DELAY_MAX)
                )
                detail_url = f"{_DETAIL_BASE_URL}{event.event_id}"
                html = await self._fetch_with_cf_retry(detail_url)
                if html is None:
                    cf_blocks += 1
                    return
                details = FlappersEventExtractor.extract_show_details(html)
                if not details:
                    return
                if details.ticket_tiers:
                    event.ticket_tiers = details.ticket_tiers
                if details.lineup_names:
                    event.lineup_names = details.lineup_names
                if details.description:
                    event.description = details.description

        await asyncio.gather(*(fetch_detail(ev) for ev in events))

        with_tickets = sum(1 for ev in events if ev.ticket_tiers)
        with_lineup = sum(1 for ev in events if ev.lineup_names)
        with_desc = sum(1 for ev in events if ev.description)
        enriched = sum(
            1 for ev in events
            if ev.ticket_tiers or ev.lineup_names or ev.description
        )
        Logger.info(
            f"{self._log_prefix}: enriched {enriched}/{len(events)} events "
            f"(tickets={with_tickets}, lineup={with_lineup}, desc={with_desc})"
            + (f" ({cf_blocks} Cloudflare blocks)" if cf_blocks else ""),
            self.logger_context,
        )

    @staticmethod
    def _is_cf_challenge(html: str) -> bool:
        """Detect Cloudflare challenge pages served as HTTP 200.

        When rate-limited, Cloudflare returns the site homepage (large HTML
        without detail-page markers) instead of the actual show detail page.
        """
        if len(html) < _CF_CHALLENGE_MIN_LEN:
            return False
        return "ticket_choices" not in html and "also-starring" not in html

    async def _fetch_with_cf_retry(self, url: str) -> Optional[str]:
        """Fetch a URL with Cloudflare challenge detection and exponential backoff."""
        for attempt in range(1, _CF_MAX_RETRIES + 1):
            try:
                html = await self.fetch_html(url)
                if not html:
                    return None
                if not self._is_cf_challenge(html):
                    return html
                # Cloudflare challenge detected — retry with backoff
                if attempt < _CF_MAX_RETRIES:
                    delay = min(
                        _CF_BASE_DELAY * (2 ** (attempt - 1)),
                        _CF_MAX_DELAY,
                    )
                    delay *= 0.5 + random.random() * 0.5
                    Logger.info(
                        f"{self._log_prefix}: Cloudflare challenge for {url}, "
                        f"retry {attempt}/{_CF_MAX_RETRIES} in {delay:.1f}s",
                        self.logger_context,
                    )
                    await asyncio.sleep(delay)
                    continue
                Logger.warn(
                    f"{self._log_prefix}: Cloudflare challenge for {url} "
                    f"after {_CF_MAX_RETRIES} attempts",
                    self.logger_context,
                )
                return None
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: failed to fetch detail {url}: {e}",
                    self.logger_context,
                )
                return None
        return None
