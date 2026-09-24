"""Generic scraper for SeeTickets/Eventim whitelabel storefronts."""

from __future__ import annotations

import asyncio
import math
from datetime import datetime
import re
from typing import Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from laughtrack.foundation.exceptions.scraping_errors import DataError, ErrorSeverity
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
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


class IncompleteCalendarError(DataError):
    """A bounded calendar failure must not restart the entire fan-out."""

    def __init__(self, message: str):
        super().__init__(message, data_type="event showtime")
        self.severity = ErrorSeverity.HIGH


class SeeTicketsWhitelabelScraper(BaseScraper):
    key = "seetickets_whitelabel"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SeeTicketsWhitelabelTransformer(club))

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        calendar_url = self._metadata_value("calendar_url")
        if calendar_url:
            return [calendar_url]
        if not self._profile_id() or not self._whitelabel_key():
            Logger.warn(
                f"{self._log_prefix}: missing metadata.profile_id or metadata.whitelabel_key",
                self.logger_context,
            )
            return []
        source_url = self._source_url()
        return [source_url] if source_url else []

    async def get_data(self, url: ScrapingTarget) -> Optional[SeeTicketsWhitelabelPageData]:
        calendar_url = self._metadata_value("calendar_url")
        if calendar_url:
            try:
                html = await asyncio.wait_for(self.fetch_html(calendar_url), timeout=45)
                if not html:
                    raise IncompleteCalendarError("Official calendar returned no usable HTML")
                events = SeeTicketsWhitelabelExtractor.extract_calendar_events(
                    html, base_url=self._base_url(calendar_url)
                )
                if not events:
                    raise IncompleteCalendarError("Official calendar contained no verified performances")
                await self._attach_detail_page_times(events)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Do not let the base retry layer multiply a bounded calendar
                # attempt, including provider/network failures and parse errors.
                raise IncompleteCalendarError(f"{self._log_prefix}: official calendar failed: {exc}") from exc
            return SeeTicketsWhitelabelPageData(event_list=events)

        profile_id = self._profile_id()
        whitelabel_key = self._whitelabel_key()
        if not profile_id or not whitelabel_key:
            return None

        browser = PlaywrightBrowser()

        async def listing_pages():
            try:
                return await browser.fetch_seetickets_whitelabel_pages(
                    profile_id=profile_id,
                    whitelabel_key=whitelabel_key,
                    affiliate_key=self._affiliate_key(),
                    base_url=self._base_url(str(url)),
                    max_months=self._int_metadata("max_months", 12),
                    page_size=self._int_metadata("page_size", 15),
                )
            finally:
                # Cancellation must not leave an unbounded browser close after
                # the listing deadline. 40s fetching + <=5s close fits 45s.
                await asyncio.wait_for(browser.close(), timeout=5)

        try:
            pages = await asyncio.wait_for(listing_pages(), timeout=40)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise IncompleteCalendarError(f"{self._log_prefix}: bounded listing failed: {exc}") from exc

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
        """Attach verified times within a hard phase budget; reject partial data.

        Missing showtimes are load-bearing failures, not optional enrichment.
        DataError makes BaseScraper mark the target failed, preventing stale-show
        deletion. Both request timeouts and the phase deadline include rate-limit
        waits/retries; cancelled tasks are drained before returning.
        """
        events = list(events)
        if not events:
            return
        verified = {}
        for event in events:
            if event.start_datetime and _TIMED_START_RE.search(event.start_datetime):
                try:
                    datetime.fromisoformat(event.start_datetime)
                except ValueError:
                    pass
                else:
                    verified[event.ticket_url] = event.start_datetime
        if all(event.ticket_url in verified for event in events):
            return
        urls = list(
            dict.fromkeys(event.ticket_url for event in events if event.ticket_url and event.ticket_url not in verified)
        )
        limit = min(8, self._int_metadata("detail_concurrency", 8))
        request_timeout = self._bounded_seconds("detail_timeout_seconds", 12, 20)
        budget = self._bounded_seconds("detail_budget_seconds", 120, 120)
        semaphore = asyncio.Semaphore(limit)

        async def fetch(url):
            async with semaphore:
                try:
                    value = await asyncio.wait_for(self._fetch_detail_start_datetime(url), request_timeout)
                    return url, value
                except asyncio.TimeoutError:
                    return url, None

        tasks = [asyncio.create_task(fetch(url)) for url in urls]
        done = set()
        try:
            if tasks:
                done, _ = await asyncio.wait(tasks, timeout=budget)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        start_by_url = dict(verified)
        for task in done:
            if not task.cancelled() and task.exception() is None:
                url, value = task.result()
                if value:
                    start_by_url[url] = value
        for event in events:
            event.start_datetime = start_by_url.get(event.ticket_url) or ""
        missing = [event.event_id for event in events if not event.start_datetime]
        if missing:
            raise IncompleteCalendarError(
                f"{self._log_prefix}: missing verified showtime for {len(missing)}/{len(events)} "
                f"events (IDs {', '.join(missing[:10])}); refusing incomplete calendar"
            )

    async def _fetch_detail_start_datetime(self, url: str) -> Optional[str]:
        """Fetch one identity-matched detail time; caller owns failure policy.

        Browser fallback stays disabled for this per-event fan-out. The outer
        request budget covers both HTTP retries and the domain rate limiter.
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
            return self._parse_detail_start_datetime(html, url)
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: detail-page time parse failed for {url}: {e}",
                self.logger_context,
            )
            return None

    @staticmethod
    def _detail_identity(url: str):
        parsed = urlparse(url)
        match = re.search(r"/event/[^/]+/(\d+)(?:/|$)", parsed.path)
        return (parsed.hostname, match.group(1)) if match and parsed.hostname else None

    @staticmethod
    def _parse_detail_start_datetime(html: str, expected_url: str) -> Optional[str]:
        """One valid timed value on the matching Event; never choose earliest.

        Query strings/slugs are not event identity. Conflicting matching Event
        blocks or malformed/date-only values fail closed, while unrelated event
        recommendations cannot replace this performance's time.
        """
        identity = SeeTicketsWhitelabelScraper._detail_identity(expected_url)
        if identity is None:
            return None
        objects = JSONUtils.parse_json_ld_contents(HtmlScraper.get_json_ld_script_contents(html))
        values = set()
        for obj in objects:
            for event in EventExtractor._extract_objects_by_type(obj, "Event"):
                url = event.get("url") or event.get("@id")
                if (
                    not isinstance(url, str)
                    or SeeTicketsWhitelabelScraper._detail_identity(urljoin(expected_url, url)) != identity
                ):
                    continue
                value = event.get("startDate")
                if not isinstance(value, str) or not _TIMED_START_RE.search(value):
                    return None
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    return None
                values.add(value)
        return next(iter(values)) if len(values) == 1 else None

    def _bounded_seconds(self, key: str, default: float, maximum: float) -> float:
        try:
            value = float((self.club.source_metadata or {}).get(key, default))
        except (ValueError, TypeError):
            value = default
        if not math.isfinite(value):
            value = default
        return min(maximum, max(0.1, value))

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
