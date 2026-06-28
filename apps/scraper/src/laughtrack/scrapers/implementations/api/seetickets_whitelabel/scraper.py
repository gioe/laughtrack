"""Generic scraper for SeeTickets/Eventim whitelabel storefronts."""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import SeeTicketsWhitelabelPageData
from .extractor import SeeTicketsWhitelabelExtractor
from .transformer import SeeTicketsWhitelabelTransformer


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

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} SeeTickets whitelabel event(s)",
            self.logger_context,
        )
        return SeeTicketsWhitelabelPageData(event_list=events)

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
