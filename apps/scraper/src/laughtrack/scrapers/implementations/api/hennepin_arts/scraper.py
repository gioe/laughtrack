"""Hennepin Arts comedy scraper.

Hennepin Arts renders its event grid through Algolia InstantSearch. The public
events page exposes the app id/key and queries index ``events_production`` with
``genre:Comedy``. Algolia hits contain event slugs and venue names, while the
Nuxt detail page embeds exact Contentful performance records with ``startDate``
and ``ticketsUrl``. This scraper uses Algolia for pagination and detail pages
for exact showtime/ticket URLs.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote, urlencode

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import HennepinArtsPageData
from .extractor import extract_events_from_details, extract_hits, slug_from_hit
from .transformer import HennepinArtsEventTransformer

_ALGOLIA_APP_ID = "82420Y68O3"
_ALGOLIA_API_KEY = "fcac13e357903ba15f299fc0c18545f2"
_ALGOLIA_HOST = "https://82420y68o3-dsn.algolia.net"
_INDEX_NAME = "events_production"
_DEFAULT_SOURCE_URL = "https://hennepinarts.org/events?refinementList%5Bgenre%5D%5B0%5D=Comedy"
_DEFAULT_HITS_PER_PAGE = 24
_MAX_PAGES = 20


class HennepinArtsScraper(BaseScraper):
    """Scrape Hennepin Arts comedy events."""

    key = "hennepin_arts"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(HennepinArtsEventTransformer(club))

    async def collect_scraping_targets(self) -> list[ScrapingTarget]:
        return [self.club.scraping_url or _DEFAULT_SOURCE_URL]

    async def _fetch_algolia_page(self, page: int) -> Optional[dict[str, Any]]:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        params = urlencode(
            {
                "facetFilters": '[["genre:Comedy"]]',
                "filters": f"endDateTimestamp >= {now_ts} OR startDateTimestamp >= {now_ts}",
                "hitsPerPage": str(_DEFAULT_HITS_PER_PAGE),
                "page": str(page),
                "query": "",
            }
        )
        body = {"requests": [{"indexName": _INDEX_NAME, "params": params}]}
        headers = {
            "Content-Type": "application/json",
            "X-Algolia-API-Key": _ALGOLIA_API_KEY,
            "X-Algolia-Application-Id": _ALGOLIA_APP_ID,
        }
        url = f"{_ALGOLIA_HOST}/1/indexes/*/queries"
        async with AsyncSession(impersonate="chrome124") as session:
            response = await session.post(url, headers=headers, json=body)
            if response.status_code != 200:
                Logger.warn(
                    f"{self._log_prefix}: Algolia page {page} returned "
                    f"HTTP {response.status_code}",
                    self.logger_context,
                )
                return None
            return response.json()

    async def _fetch_detail(self, slug: str) -> str:
        url = f"https://hennepinarts.org/events/{quote(slug.strip('/'))}"
        async with AsyncSession(impersonate="chrome124") as session:
            html = await HttpClient.fetch_html(
                session=session,
                url=url,
                logger_context=self.logger_context,
                scraper_key=self.key,
            )
        return html or ""

    async def get_data(self, target: ScrapingTarget) -> Optional[HennepinArtsPageData]:
        hits: list[dict[str, Any]] = []
        seen_slugs: set[str] = set()
        nb_pages: Optional[int] = None

        for page in range(_MAX_PAGES):
            if nb_pages is not None and page >= nb_pages:
                break
            payload = await self._fetch_algolia_page(page)
            if not payload:
                break
            page_hits, page_count = extract_hits(payload)
            if nb_pages is None:
                nb_pages = page_count
            if not page_hits:
                break
            for hit in page_hits:
                slug = slug_from_hit(hit)
                if not slug or slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                hits.append(hit)

        detail_items: list[tuple[dict[str, Any], str]] = []
        for hit in hits:
            slug = slug_from_hit(hit)
            if not slug:
                continue
            html = await self._fetch_detail(slug)
            if html:
                detail_items.append((hit, html))

        events = extract_events_from_details(detail_items)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: no Hennepin Arts comedy events extracted from {target}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} Hennepin Arts comedy performance(s)",
            self.logger_context,
        )
        return HennepinArtsPageData(event_list=events)
