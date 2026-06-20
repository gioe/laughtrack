"""Tempo Tickets (tempotickets.com) scraper.

Pipeline:
    1. collect_scraping_targets(): fetch the listing.php?c=<category_id> page,
       extract the per-event /event/{code} detail URLs.
    2. get_data(url): fetch one event page, parse its EventDateID select into one
       TempoTicketsEvent per upcoming date.

The listing page and event pages are plain server-rendered PHP HTML (browser UA,
no JSON-LD / API / auth / anti-bot), so plain fetch_html works (curl_cffi with
automatic Playwright fallback). The listing URL is built from the active
scraping source's `category_id` metadata so the scraper is reusable for any
Tempo venue; it falls back to the club's scraping_url when no category is set.
"""

import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import TempoTicketsPageData
from .extractor import (
    extract_event_dates,
    extract_event_links,
    listing_url_for_category,
)
from laughtrack.core.entities.event.tempo_tickets import TempoTicketsEvent
from .transformer import TempoTicketsTransformer


class TempoTicketsScraper(BaseScraper):
    """Two-step listing -> event-page scraper for tempotickets.com venues."""

    key = "tempo_tickets"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TempoTicketsTransformer(club))

    def _show_tags(self) -> List[str]:
        """Venue-specific Show tags from source metadata (default ['event']).

        Keeps the shared scraper generic: ComedySportz sets ['event','improv'],
        a future stand-up Tempo venue can set its own without code changes.
        """
        tags = (self.club.source_metadata or {}).get("tags")
        if isinstance(tags, list) and tags:
            return [str(t) for t in tags]
        return ["event"]

    def _listing_url(self) -> Optional[str]:
        category_id = (self.club.source_metadata or {}).get("category_id")
        if category_id:
            return listing_url_for_category(str(category_id))
        return self.club.scraping_url or None

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """Fetch the listing page and return the event detail URLs."""
        listing_url = self._listing_url()
        if not listing_url:
            Logger.warn(
                f"{self._log_prefix}: no category_id metadata or scraping_url configured",
                self.logger_context,
            )
            return []

        html = await self.fetch_html(listing_url)
        if not html:
            self._warn_empty_extraction(listing_url, subject="event links", html=html)
            return []

        links = extract_event_links(html)
        if not links:
            self._warn_empty_extraction(listing_url, subject="event links", html=html)
            return []

        Logger.info(
            f"{self._log_prefix}: discovered {len(links)} Tempo event(s)",
            self.logger_context,
        )
        return [url for _code, _title, url in links]

    async def get_data(self, target: ScrapingTarget) -> Optional[TempoTicketsPageData]:
        """Fetch one event page and fan its upcoming dates out into shows."""
        html = await self.fetch_html(target)
        if not html:
            self._warn_empty_extraction(target, html=html)
            return None

        title = self._extract_title(html, fallback=self.club.name)
        tags = self._show_tags()
        dates = extract_event_dates(html)
        if not dates:
            self._warn_empty_extraction(target, subject="upcoming dates", html=html)
            return None

        events = [
            TempoTicketsEvent(
                title=title,
                start=start,
                event_url=target,
                date_id=date_id,
                tags=tags,
            )
            for date_id, start in dates
        ]
        return TempoTicketsPageData(event_list=events)

    # Tempo event titles are hardcoded with the current year ('2026 ComedySportz
    # Friday 7:30 Match'); strip a leading 4-digit year so a rolled-over
    # next-year date doesn't carry a stale year in the Show name.
    _LEADING_YEAR_RE = re.compile(r"^\s*\d{4}\s+")

    @classmethod
    def _extract_title(cls, html: str, *, fallback: str) -> str:
        """Best-effort event title from the event page <h1>/<title>."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find("h1")
        raw = ""
        if heading and heading.get_text(strip=True):
            raw = heading.get_text(strip=True)
        elif soup.title and soup.title.get_text(strip=True):
            raw = soup.title.get_text(strip=True)

        cleaned = cls._LEADING_YEAR_RE.sub("", raw).strip()
        return cleaned or fallback
