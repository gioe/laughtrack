"""Generic scraper for SeeTickets/Eventim whitelabel storefronts."""

from __future__ import annotations

import asyncio
import re
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.seetickets_whitelabel import SeeTicketsWhitelabelEvent
from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.shared.types import ScrapingTarget

from .data import SeeTicketsWhitelabelPageData
from .extractor import SeeTicketsWhitelabelExtractor
from .transformer import SeeTicketsWhitelabelTransformer

# A JSON-LD startDate carrying an actual clock time (vs. a bare "2026-06-29"
# date). Only timed values improve on the card's date-only midnight, so the
# enrichment ignores date-only startDates.
_TIMED_START_RE = re.compile(r"T\d{2}:\d{2}")


class SeeTicketsWhitelabelScraper(BaseScraper):
    key = "seetickets_whitelabel"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SeeTicketsWhitelabelTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        if not self._profile_id() or not self._whitelabel_key():
            Logger.warn(
                f"{self._log_prefix}: missing metadata.profile_id or metadata.whitelabel_key",
                self.logger_context,
            )
            return []
        source_url = self._source_url()
        return [source_url] if source_url else []

    async def get_data(self, url: ScrapingTarget) -> Optional[SeeTicketsWhitelabelPageData]:
        profile_id = self._profile_id()
        whitelabel_key = self._whitelabel_key()
        if not profile_id or not whitelabel_key:
            return None

        browser = PlaywrightBrowser()
        try:
            pages = await browser.fetch_seetickets_whitelabel_pages(
                profile_id=profile_id,
                whitelabel_key=whitelabel_key,
                affiliate_key=self._affiliate_key(),
                base_url=self._base_url(str(url)),
                max_months=self._int_metadata("max_months", 12),
                page_size=self._int_metadata("page_size", 15),
            )
        finally:
            await browser.close()

        events = []
        seen_ids = set()
        base_url = self._base_url(str(url))
        for html in pages:
            for event in SeeTicketsWhitelabelExtractor.extract_events(html, base_url=base_url):
                if event.event_id in seen_ids:
                    continue
                events.append(event)
                seen_ids.add(event.event_id)

        if not events:
            self._warn_empty_extraction(str(url), subject="SeeTickets whitelabel events")
            return None

        await self._attach_detail_page_times(events)

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} SeeTickets whitelabel event(s)",
            self.logger_context,
        )
        return SeeTicketsWhitelabelPageData(event_list=events)

    async def _attach_detail_page_times(self, events: Iterable[SeeTicketsWhitelabelEvent]) -> None:
        """Enrich each event with the real showtime from its detail-page JSON-LD.

        The search-results card carries only a date, so start_date alone lands
        every show at local midnight. Each event's detail page (ticket_url)
        embeds a schema.org Event JSON-LD with a timed startDate; fetch those,
        parse the time, and write it onto ``event.start_datetime``. Distinct
        URLs are fetched at most once and bounded by a semaphore. Any per-event
        failure leaves start_datetime empty so to_show degrades to the date-only
        midnight value rather than dropping the show or sinking the run.
        """
        events = list(events)
        urls = list(dict.fromkeys(e.ticket_url for e in events if e.ticket_url))
        if not urls:
            return

        limit = self._int_metadata("detail_concurrency", 8)
        semaphore = asyncio.Semaphore(limit)

        async def _fetch(url: str) -> tuple[str, Optional[str]]:
            async with semaphore:
                return url, await self._fetch_detail_start_datetime(url)

        results = await asyncio.gather(*(_fetch(url) for url in urls))
        start_by_url = dict(results)
        for event in events:
            iso = start_by_url.get(event.ticket_url)
            if iso:
                event.start_datetime = iso

    async def _fetch_detail_start_datetime(self, url: str) -> Optional[str]:
        """Fetch one detail page and return its timed JSON-LD startDate, or None.

        Never raises: a failed/blocked fetch or a date-only startDate degrades
        to None (caller keeps the card's midnight value). skip_js_fallback=True
        (convention #296) keeps a bot-blocked detail page from spinning a
        per-URL Playwright browser — the time is a cheap enrichment, not
        load-bearing show data.
        """
        try:
            await self.rate_limiter.await_if_needed(url)
            html = await self.fetch_html(url, skip_js_fallback=True)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: detail-page time fetch failed for {url}: {e}",
                self.logger_context,
            )
            return None
        if not html:
            return None
        try:
            return self._parse_detail_start_datetime(html)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: detail-page time parse failed for {url}: {e}",
                self.logger_context,
            )
            return None

    @staticmethod
    def _parse_detail_start_datetime(html: str) -> Optional[str]:
        """Lowest timed JSON-LD startDate on the page, or None if all are date-only.

        A whitelabel detail page is one event, but may carry several Event
        blocks (e.g. doors vs. show); take the earliest timed value as the
        showtime. Date-only startDates are ignored — they would not improve on
        the card's midnight value.
        """
        values = EventExtractor.extract_event_field_values(html, "startDate")
        timed = sorted(v for v in values if _TIMED_START_RE.search(v))
        return timed[0] if timed else None

    def _metadata_value(self, key: str) -> str:
        value = (self.club.source_metadata or {}).get(key)
        return str(value or "").strip()

    def _profile_id(self) -> str:
        return self._metadata_value("profile_id")

    def _whitelabel_key(self) -> str:
        return self._metadata_value("whitelabel_key") or self._metadata_value("white_label_key")

    def _affiliate_key(self) -> str:
        return self._metadata_value("affiliate_key") or self._metadata_value("afflky") or self._whitelabel_key()

    def _source_url(self) -> str:
        return (self.club.scraping_url or "").strip()

    def _int_metadata(self, key: str, default: int) -> int:
        raw = (self.club.source_metadata or {}).get(key)
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return default

    def _base_url(self, source_url: str) -> str:
        parsed = urlparse(source_url or self._source_url())
        if not parsed.scheme or not parsed.netloc:
            return "https://wl.eventim.us"
        return f"{parsed.scheme}://{parsed.netloc}"
