"""Generic scraper for SellingTicket HTML list pages."""

import re
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import SellingTicketPageData
from .extractor import SellingTicketExtractor
from .transformer import SellingTicketTransformer


class GenericSellingTicketScraper(BaseScraper):
    """Scrape SellingTicket list pages configured by scraping_sources.source_url.

    SellingTicket is often used by multi-purpose theatres. Configure
    ``metadata.include_title_patterns`` to keep only relevant rows.
    """

    key = "sellingticket"

    def __init__(self, club: Club, **kwargs):
        source_url = URLUtils.normalize_url(club.scraping_url or "")
        if not source_url or "sellingticket.com" not in source_url:
            raise ValueError(
                "GenericSellingTicketScraper requires a sellingticket.com "
                f"scraping_sources.source_url for club_id={club.id} ('{club.name}'); "
                f"got {club.scraping_url!r}"
            )

        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SellingTicketTransformer(club))

    async def get_data(self, url: str) -> Optional[SellingTicketPageData]:
        normalized_url = URLUtils.normalize_url(url)
        try:
            html = await self.fetch_html(normalized_url)
            events = SellingTicketExtractor.extract_events(html or "", normalized_url)
            events = self._filter_events(events)
            if not events:
                Logger.info(
                    f"{self._log_prefix}: no SellingTicket events matched configured filters",
                    self.logger_context,
                )
                return None
            return SellingTicketPageData(event_list=events)
        except Exception as e:
            Logger.error(f"{self._log_prefix}: get_data failed for {normalized_url}: {e}", self.logger_context)
            return None

    def _filter_events(self, events):
        include_patterns = self._compiled_patterns("include_title_patterns")
        exclude_patterns = self._compiled_patterns("exclude_title_patterns")

        filtered = []
        for event in events:
            title = event.title or ""
            if include_patterns and not any(pattern.search(title) for pattern in include_patterns):
                continue
            if exclude_patterns and any(pattern.search(title) for pattern in exclude_patterns):
                continue
            filtered.append(event)
        return filtered

    def _compiled_patterns(self, metadata_key: str) -> list[re.Pattern]:
        raw = (self.club.source_metadata or {}).get(metadata_key)
        if not raw:
            return []
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, list):
            values = [str(value) for value in raw if str(value).strip()]
        else:
            return []
        return [re.compile(value, re.IGNORECASE) for value in values]
