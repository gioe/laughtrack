"""Shared detail-page price attachment for scrapers whose listing source
carries no price field.

Several platforms (ThunderTix calendar API, Tockify ngevent payload, OpenDate
listing pages) list events without prices, but each event's detail/ticket page
embeds a schema.org Event JSON-LD block with offers. This mixin fetches those
pages, parses the lowest per-tier offer price via the shared JSON-LD helper,
and writes it onto each event. Consolidated from identical copies in the
thundertix, ice_house (tockify), and sports_drink scrapers (TASK-2848).
"""

import asyncio
from typing import Any, Callable, Dict, Iterable, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


class DetailPagePriceMixin:
    """Fetch-and-memoize detail-page JSON-LD prices for a scraper's events.

    Fetches are memoized per distinct URL for the life of the run: recurring
    shows share a detail page (and the same event recurs across paginated or
    weekly windows), so each page is fetched at most once — and a get_data
    retry refetches only failures, never successes.

    Host class requirements (all provided by BaseScraper): ``fetch_html``,
    ``rate_limiter``, ``_log_prefix``, ``logger_context``. Items passed to
    ``_attach_detail_page_prices`` must expose a mutable
    ``price: Optional[float]`` attribute. Must precede BaseScraper in the
    bases list so its cooperative ``__init__`` runs.
    """

    # Log label for the fetched page; override where the page is better
    # described another way (e.g. ice_house's ShowClix/Leap "ticket-page").
    _detail_price_log_subject: str = "detail-page"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._detail_price_tasks: Dict[str, "asyncio.Task[Optional[float]]"] = {}

    async def _attach_detail_page_prices(
        self,
        items: Iterable[Any],
        url_for: Callable[[Any], Optional[str]],
    ) -> None:
        """Populate each item's ``price`` from its detail page's JSON-LD offers.

        ``url_for`` maps an item to its detail-page URL; returning None skips
        the item, leaving its price untouched (price-unknown). Distinct URLs
        are fetched concurrently and memoized per run.
        """
        items = list(items)
        urls = list(dict.fromkeys(
            url for url in (url_for(item) for item in items) if url
        ))
        prices = await asyncio.gather(*(self._detail_page_price(url) for url in urls))
        price_by_url = dict(zip(urls, prices))
        for item in items:
            url = url_for(item)
            if url:
                item.price = price_by_url.get(url)

    def _detail_page_price(self, url: str) -> "asyncio.Task[Optional[float]]":
        task = self._detail_price_tasks.get(url)
        if task is None:
            task = asyncio.ensure_future(self._fetch_detail_page_price(url))
            self._detail_price_tasks[url] = task
        return task

    async def _fetch_detail_page_price(self, url: str) -> Optional[float]:
        """Fetch one detail page and parse its lowest JSON-LD offer price.

        Never raises: a missing price degrades the ticket to price-unknown
        (None) rather than dropping the listing. Failed fetches are evicted
        from the memo so a retry can try the page again; a fetched page with
        no parseable offers stays cached — refetching would not help.
        """
        subject = self._detail_price_log_subject
        try:
            await self.rate_limiter.await_if_needed(url)
            html = await self.fetch_html(url)
        except Exception as e:
            self._detail_price_tasks.pop(url, None)
            Logger.warn(
                f"{self._log_prefix}: {subject} price fetch failed for {url}: {e}",
                self.logger_context,
            )
            return None
        if not html:
            self._detail_price_tasks.pop(url, None)
            return None
        try:
            return self._parse_detail_page_price(html)
        except Exception as e:
            # Parse failures stay cached — the page was fetched fine, so a
            # refetch would not help.
            Logger.warn(
                f"{self._log_prefix}: {subject} price parse failed for {url}: {e}",
                self.logger_context,
            )
            return None

    def _parse_detail_page_price(self, html: str) -> Optional[float]:
        """Hook for the page→price parse; default is the shared JSON-LD helper."""
        return EventExtractor.extract_min_offer_price(html)
