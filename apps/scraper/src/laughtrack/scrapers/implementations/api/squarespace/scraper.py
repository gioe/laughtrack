"""
Generic Squarespace venue scraper.

Venues whose show calendar is powered by Squarespace publish event data via:
  GET {domain}/api/open/GetItemsByMonth?month=MM-YYYY&collectionId={id}

The response is a JSON array at the root level (not a dict). The scraping_url
stored in the clubs DB must be the full GetItemsByMonth endpoint including the
collectionId query parameter, e.g.:
  https://thedentheatre.com/api/open/GetItemsByMonth?collectionId=64bc3c406b6d3d1edd3c84db

The scraper fetches the current month and the next two months to capture all
upcoming shows.

Currently used by: The Den Theatre Chicago (IL), The Elysian Theater (CA), Nashville Improv (TN), Villain Theater (FL).
A new Squarespace venue can be onboarded with only a DB row — no Python changes.
"""

import asyncio
import re
from datetime import date
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from laughtrack.core.entities.event.squarespace import SquarespaceEvent

from .data import SquarespacePageData
from .extractor import SquarespaceExtractor
from .transformer import SquarespaceEventTransformer


# Per-host RPS override applied to each Squarespace venue's own domain.
# The TASK-2560 nightly survey (run 26762966336) found The Den Theatre stalling
# at 1.05 s/show (98s wall clock across 93 shows) on the per-event detail fetch
# in _enrich_with_ticket_urls.
#
# 2 RPS = 1 req/500ms — conservative bump above the 1 RPS floor. The inner
# detail-fetch semaphore is already 5, so 2 RPS drops the rate-limit floor
# for The Den from ~93s to ~47s without changing the concurrency model.
# Matches the JsonLdScraper and FoxTucsonTheatre overrides for consistency
# (TASK-2570 ships all three together).
_SQUARESPACE_HOST_RPS = 2.0


class SquarespaceScraper(BaseScraper):
    """
    Generic Squarespace scraper — reads club.scraping_url for the API endpoint.

    Fetches events for the current month and the next two months.
    """

    key = "squarespace"

    # Pagination cap for products mode (?format=json follows pagination.nextPageUrl).
    _PRODUCTS_MAX_PAGES = 10

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SquarespaceEventTransformer(club))

        parsed = urlparse(club.scraping_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        qs = parse_qs(parsed.query)
        self.collection_id = (qs.get("collectionId") or [""])[0]

        # Products-collection mode: some venues sell each show as a dated store
        # product (collection typeName='products') instead of an Events
        # collection, so GetItemsByMonth returns []. Opt in via
        # scraping_sources.metadata.collection_type='products'; scraping_url is
        # then the collection PAGE url (e.g. https://venue.com/tickets) and the
        # scraper reads it via ?format=json. Absent/other → events mode (default).
        self.products_mode = (club.source_metadata or {}).get("collection_type") == "products"
        # The collection page url with any query stripped (?format=json appended later).
        self.products_url = f"{self.base_domain}{parsed.path}".rstrip("/")

        # Opt-in title filter for mixed-use venues. Two scraping_sources.metadata
        # keys, both OFF by default (existing venues are unaffected):
        #   - include_title_patterns — keep ONLY events whose title matches at
        #     least one pattern (the comedy allowlist; for an arts center whose
        #     events collection is mostly films/plays/concerts with an occasional
        #     comedy night, e.g. Cloverdale Performing Arts Center, TASK-3236).
        #   - exclude_title_patterns — drop events whose title matches any
        #     pattern (class sessions/workshops on improv-theatre calendars).
        # Patterns are compiled (str-or-list, case-insensitive, re.error-guarded)
        # via the shared BaseScraper.compile_title_patterns helper. The
        # include-then-exclude loop mirrors ticketweb / sellingticket / showare.
        self.include_title_res = self.compile_title_patterns("include_title_patterns")
        self.exclude_title_res = self.compile_title_patterns("exclude_title_patterns")

        self._register_host_rps(_SQUARESPACE_HOST_RPS)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Return the fetch targets for this venue.

        Products mode: the single collection page rendered as JSON. Events mode:
        GetItemsByMonth URLs for the current month and next two months.
        """
        if self.products_mode:
            return [f"{self.products_url}?format=json"]

        today = date.today()
        targets = []
        for i in range(3):
            month = (today.month + i - 1) % 12 + 1
            year = today.year + (today.month + i - 1) // 12
            month_str = f"{month:02d}-{year}"
            url = (
                f"{self.base_domain}/api/open/GetItemsByMonth"
                f"?month={month_str}&collectionId={self.collection_id}"
            )
            targets.append(url)
        return targets

    async def get_data(self, url: str) -> Optional[SquarespacePageData]:
        """
        Fetch events from the Squarespace GetItemsByMonth API.

        The API returns a JSON array at the root level (not a dict), so
        response is None means a network failure; response == [] means no shows
        scheduled for that month.
        """
        if self.products_mode:
            return await self._get_products_data(url)

        try:
            await self.rate_limiter.await_if_needed(url)

            response = await self.fetch_json_list(url)
            if response is None:
                Logger.info(
                    f"{self._log_prefix}: empty response from {url}",
                    self.logger_context,
                )
                return None
            if not response:
                Logger.info(
                    f"{self._log_prefix}: no shows scheduled for {url}",
                    self.logger_context,
                )
                return None

            events = SquarespaceExtractor.extract_events(
                response,
                self.base_domain,
                include_title_res=self.include_title_res,
                exclude_title_res=self.exclude_title_res,
            )
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no events extracted from {url}",
                    self.logger_context,
                )
                return None

            await self._enrich_with_ticket_urls(events)

            Logger.info(
                f"{self._log_prefix}: extracted {len(events)} events from {url}",
                self.logger_context,
            )
            return SquarespacePageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching events from {url}: {e}",
                self.logger_context,
            )
            return None

    async def _get_products_data(self, url: str) -> Optional[SquarespacePageData]:
        """Fetch a Squarespace products/store collection and extract dated shows.

        The collection page rendered as ``?format=json`` returns a dict with an
        ``items`` array of store products and a ``pagination`` block. Follows
        ``pagination.nextPageUrl`` (capped) to capture every product. No
        per-event detail enrichment: each product's ``fullUrl`` is already its
        ticket/checkout page.
        """
        all_items: List[dict] = []
        current_url: Optional[str] = url
        for _ in range(self._PRODUCTS_MAX_PAGES):
            if not current_url:
                break
            try:
                await self.rate_limiter.await_if_needed(current_url)
                response = await self.fetch_json(current_url)
            except Exception as e:
                Logger.error(
                    f"{self._log_prefix}: error fetching products from {current_url}: {e}",
                    self.logger_context,
                )
                return None
            if not isinstance(response, dict):
                break
            items = response.get("items")
            if isinstance(items, list):
                all_items.extend(items)
            pagination = response.get("pagination") or {}
            next_path = pagination.get("nextPageUrl") if pagination.get("nextPage") else None
            current_url = self._products_next_url(next_path)
        else:
            # for-else: ran the full page budget without breaking. If a next page
            # is still pending, we truncated — warn rather than silently capping.
            if current_url:
                Logger.warn(
                    f"{self._log_prefix}: products pagination hit the "
                    f"{self._PRODUCTS_MAX_PAGES}-page cap with more pages pending; "
                    f"some shows may be missing",
                    self.logger_context,
                )

        if not all_items:
            Logger.info(
                f"{self._log_prefix}: no products found at {url}",
                self.logger_context,
            )
            return None

        events = SquarespaceExtractor.extract_products(
            all_items,
            self.base_domain,
            timezone_name=self.club.timezone or "UTC",
            include_title_res=self.include_title_res,
            exclude_title_res=self.exclude_title_res,
        )
        if not events:
            Logger.info(
                f"{self._log_prefix}: no datable show products extracted from {url}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} show product(s) from {url}",
            self.logger_context,
        )
        return SquarespacePageData(event_list=events)

    def _products_next_url(self, next_path: Optional[str]) -> Optional[str]:
        """Resolve a pagination.nextPageUrl (relative path) to an absolute JSON URL."""
        if not next_path:
            return None
        absolute = next_path if next_path.startswith("http") else self.base_domain + next_path
        if "format=json" not in absolute:
            absolute += ("&" if "?" in absolute else "?") + "format=json"
        return absolute

    async def _enrich_with_ticket_urls(self, events: List[SquarespaceEvent]) -> None:
        """
        Fetch per-event detail pages to populate ticketing_url where available.

        The Squarespace bulk API (GetItemsByMonth) does not include ticketingUrl.
        The individual event detail page at {full_url}?format=json returns a JSON
        object that may contain a top-level or item-nested ticketingUrl field
        (e.g. tickets.thedentheatre.com/event/*).

        Events without a full_url, or where the detail fetch fails, retain the
        show_page_url fallback set in to_show().

        Detail fetches run concurrently (up to 5 at a time) via asyncio.gather()
        with a semaphore to avoid hammering the Squarespace CDN.
        """
        semaphore = asyncio.Semaphore(5)

        async def _fetch_one(event: SquarespaceEvent) -> None:
            if not event.full_url:
                return
            detail_url = self.base_domain.rstrip("/") + event.full_url + "?format=json"
            async with semaphore:
                try:
                    await self.rate_limiter.await_if_needed(detail_url)
                    detail = await self.fetch_json(detail_url)
                    if not isinstance(detail, dict):
                        return
                    ticketing_url = (
                        detail.get("ticketingUrl")
                        or detail.get("item", {}).get("ticketingUrl")
                        or ""
                    )
                    if not ticketing_url:
                        body_html = (
                            detail.get("body")
                            or detail.get("item", {}).get("body")
                            or ""
                        )
                        eb_match = re.search(
                            r"https://www\.eventbrite\.com/e/[^\s\"'<>]+",
                            body_html,
                        )
                        if eb_match:
                            ticketing_url = eb_match.group(0)
                    if ticketing_url:
                        event.ticketing_url = ticketing_url
                except Exception as e:
                    Logger.warn(
                        f"{self._log_prefix}: failed to fetch detail for {detail_url}: {e}",
                        self.logger_context,
                    )

        await asyncio.gather(*(_fetch_one(e) for e in events))
