"""
Side Splitters Comedy Club scraper.

Side Splitters' new Tampa calendar is hosted on Punchup at
sidesplitterscomedytampa.punchup.live. Show data is embedded in the Next.js
RSC/TanStack hydration payload, and ticket links resolve through Tixologi.
"""

import asyncio
import dataclasses
import json
import re
from typing import List, Optional
from urllib.parse import urlencode

from laughtrack.core.clients.punchup.extractor import PunchupExtractor, PunchupShow
from laughtrack.core.clients.tixologi import TixologiClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

from .data import SideSplittersPageData, SideSplittersShow
from .transformer import SideSplittersEventTransformer

_PUNCHUP_API_BASE_URL = "https://punchup.live"
_PUNCHUP_PAGE_SIZE = 20
_PUNCHUP_MAX_PAGES = 25
_TIXOLOGI_MAX_CONCURRENT_FETCHES = 10
_VENUE_SHOWS_QUERY_RE = re.compile(r'"queryKey"\s*:\s*\[\s*"venueShows"\s*,\s*"([^"]+)"\s*\]')


class SideSplittersScraper(BaseScraper):
    """Scraper for Side Splitters Comedy Club's Punchup calendar."""

    key = "side_splitters"

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.tixologi_client = TixologiClient(club)
        self.transformation_pipeline.register_transformer(SideSplittersEventTransformer(club))

    async def get_data(self, url: str) -> Optional[SideSplittersPageData]:
        """Fetch the Punchup page and extract shows from its hydration data."""
        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html_bare(normalized_url)
            if not html_content:
                Logger.warn(
                    f"{self._log_prefix}: received empty HTML from {url}",
                    self.logger_context,
                )
                return None

            punchup_shows = await self._extract_all_punchup_shows(html_content)
            if not punchup_shows:
                Logger.warn(
                    f"{self._log_prefix}: no shows found in Punchup hydration data at {url} -- "
                    "site may have changed structure or have no upcoming events",
                    self.logger_context,
                )
                return None

            shows = [
                SideSplittersShow(**{f.name: getattr(show, f.name) for f in dataclasses.fields(show)})
                for show in punchup_shows
            ]
            shows = await self._enrich_tixologi_tickets(shows)

            Logger.info(
                f"{self._log_prefix}: extracted {len(shows)} shows from {url}",
                self.logger_context,
            )
            return SideSplittersPageData(event_list=shows)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching data from {url}: {e}",
                self.logger_context,
            )
            return None

    async def _extract_all_punchup_shows(self, html_content: str) -> List[PunchupShow]:
        """Extract all Side Splitters shows, following Punchup's limit/offset API."""
        embedded_shows = PunchupExtractor.extract_shows(html_content)
        venue_page_id = self._extract_venue_page_id(html_content)
        if not venue_page_id:
            return embedded_shows

        paginated_shows = await self._fetch_paginated_punchup_shows(venue_page_id)
        return paginated_shows or embedded_shows

    async def _fetch_paginated_punchup_shows(self, venue_page_id: str) -> List[PunchupShow]:
        """Fetch every Punchup /api/shows page for the venue."""
        shows: List[PunchupShow] = []
        for page_index in range(_PUNCHUP_MAX_PAGES):
            offset = page_index * _PUNCHUP_PAGE_SIZE
            params = urlencode(
                {
                    "venuePageId": venue_page_id,
                    "limit": _PUNCHUP_PAGE_SIZE,
                    "offset": offset,
                }
            )
            url = f"{_PUNCHUP_API_BASE_URL}/api/shows?{params}"
            payload = await self.fetch_json(
                url,
                headers={"accept": "application/json"},
            )
            if not isinstance(payload, list):
                Logger.warn(
                    f"{self._log_prefix}: Punchup API returned {type(payload).__name__} "
                    f"for offset {offset}; falling back to embedded page data",
                    self.logger_context,
                )
                return []

            for item in payload:
                if not isinstance(item, dict):
                    continue
                show = PunchupExtractor._build_punchup_show(item)
                if show:
                    shows.append(show)

            if len(payload) < _PUNCHUP_PAGE_SIZE:
                break

        return shows

    @staticmethod
    def _extract_venue_page_id(html_content: str) -> Optional[str]:
        """Find the Punchup venue page id from the hydrated venueShows query key."""
        if not html_content:
            return None

        for script in HtmlScraper.find_script_elements(html_content):
            content = script.get_text() if script else None
            if not content:
                continue

            venue_page_id = SideSplittersScraper._extract_venue_page_id_from_text(content)
            if venue_page_id:
                return venue_page_id

            for match in re.finditer(r'\[1,"((?:[^"\\]|\\.)*)"\]', content):
                try:
                    decoded = json.loads('"' + match.group(1) + '"')
                except (json.JSONDecodeError, Exception):
                    continue
                venue_page_id = SideSplittersScraper._extract_venue_page_id_from_text(decoded)
                if venue_page_id:
                    return venue_page_id

        return None

    @staticmethod
    def _extract_venue_page_id_from_text(text: str) -> Optional[str]:
        match = _VENUE_SHOWS_QUERY_RE.search(text)
        return match.group(1) if match else None

    async def _enrich_tixologi_tickets(self, shows: List[SideSplittersShow]) -> List[SideSplittersShow]:
        """Attach Tixologi ticket-type payloads before transformation."""
        semaphore = asyncio.Semaphore(_TIXOLOGI_MAX_CONCURRENT_FETCHES)

        async def enrich(show: SideSplittersShow) -> SideSplittersShow:
            if not show.tixologi_event_id:
                return show
            try:
                async with semaphore:
                    ticket_types = await self.tixologi_client.fetch_event_ticket_types(show.tixologi_event_id)
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: tixologi enrichment failed for event " f"{show.tixologi_event_id}: {e}",
                    self.logger_context,
                )
                return show
            if not ticket_types:
                return show
            return show.with_tixologi_ticket_types(ticket_types)

        return await asyncio.gather(*(enrich(show) for show in shows))
