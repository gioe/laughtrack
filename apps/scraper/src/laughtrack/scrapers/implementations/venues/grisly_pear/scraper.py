"""Scraper for the Grisly Pear calendar listing."""

from typing import Optional
import asyncio
from collections import defaultdict

from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import GrislyPearPageData
from .extractor import GrislyPearExtractor
from .transformer import GrislyPearTransformer


class GrislyPearScraper(BaseScraper):
    """Extract dated event anchors from grislypearstandup.com/calendar."""

    key = "grisly_pear"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._register_host_rps(2.0)
        self.transformation_pipeline.register_transformer(GrislyPearTransformer(club))

    async def collect_scraping_targets(self) -> list[ScrapingTarget]:
        return [self.club.scraping_url]

    async def get_data(self, url: str) -> Optional[GrislyPearPageData]:
        html = await self.fetch_html(url)
        if not html:
            self._warn_empty_extraction(url, subject="calendar", html=html)
            return None

        events = GrislyPearExtractor.extract_events(
            html,
            base_url=url,
            club_name=self.club.name,
        )
        if not events:
            self._warn_empty_extraction(url, html=html)
            return None
        # Bound parallel detail reads; the existing host limiter also enforces RPS.
        limit = asyncio.Semaphore(4)

        async def enrich(event):
            async with limit:
                try:
                    detail_html = await self.fetch_html(event.url)
                    if not detail_html:
                        raise ValueError("empty event detail")
                    return GrislyPearExtractor.enrich_detail(event, detail_html, self.club)
                except Exception as exc:
                    self._record_incomplete(f"detail rejected for {event.url}: {exc}")
                    return None

        results = await asyncio.gather(*(enrich(event) for event in events))
        groups = defaultdict(list)
        for candidate, result in zip(events, results):
            groups[(candidate.date, candidate.time)].append(result)
        verified = []
        for key, aliases in groups.items():
            if any(event is None for event in aliases):
                continue
            # Two links for one venue/time cannot silently overwrite conflicting
            # performer or price evidence. Benign legacy/current aliases merge.
            signatures = {(tuple(sorted(name.casefold() for name in event.performers)), event.price)
                          for event in aliases}
            if len(signatures) != 1:
                self._record_incomplete(f"conflicting event aliases at {key}")
                continue
            verified.append(aliases[0])
        return GrislyPearPageData(event_list=verified)

    def _record_incomplete(self, message: str) -> None:
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_fetch_failed()
            diagnostics.record_scrape_error(message)
        Logger.warn(f"{self._log_prefix}: {message}; blocking stale reconciliation", self.logger_context)
