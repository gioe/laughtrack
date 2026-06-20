"""Generic scraper for Odoo website_event pages with schema.org microdata."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Pattern
from urllib.parse import urljoin, urlparse, urlunparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper

_DEFAULT_DETAIL_FETCH: dict[str, Any] = {
    "url_path_prefix": "/event/",
    "exclude_url_path_suffixes": [],
    "set_same_as_to_detail_url": True,
    "pagination": {
        "enabled": True,
        "max_pages": 10,
    },
}
_DEFAULT_EXCLUDE_TITLE_PATTERNS = [
    r"\bclass(?:es)?\b",
    r"\bworkshop(?:s)?\b",
    r"\bcamp(?:s)?\b",
]


class OdooEventsScraper(JsonLdScraper):
    """Scrape Odoo website_event listings and microdata detail pages."""

    key = "odoo_events"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._detail_url_by_fetch_url: dict[str, str] = {}

    async def scrape_async(self) -> list[Show]:
        shows = await super().scrape_async()
        shows = [show for show in shows if self._is_future_show(show)]
        exclude_title_re = self._exclude_title_re()
        if exclude_title_re:
            shows = [show for show in shows if not exclude_title_re.search(show.name or "")]
        return sorted(shows, key=lambda show: (show.date, show.name))

    async def get_data(self, url: str):
        data = await super().get_data(url)
        if data is None:
            return None

        detail_url = self._detail_url_by_fetch_url.get(url, url)
        for event in data.event_list:
            self._normalize_event(event, detail_url)
        return data

    def _detail_fetch_config(self) -> dict[str, Any]:
        configured = super()._detail_fetch_config() or {}
        merged = {
            **_DEFAULT_DETAIL_FETCH,
            **configured,
        }
        pagination = {
            **_DEFAULT_DETAIL_FETCH["pagination"],
            **(configured.get("pagination") if isinstance(configured.get("pagination"), dict) else {}),
        }
        merged["pagination"] = pagination
        return merged

    def _extract_anchor_detail_urls(
        self,
        html: str,
        base_url: str,
        detail_fetch: dict[str, Any],
    ) -> set[str]:
        urls = super()._extract_anchor_detail_urls(html, base_url, detail_fetch)
        return {url for url in urls if url.rstrip("/").endswith("/register")}

    def _extract_pagination_urls(self, html: str, base_url: str, calendar_url: str) -> list[str]:
        urls = super()._extract_pagination_urls(html, base_url, calendar_url)
        base = urlparse(calendar_url)
        listing_path = base.path.rstrip("/")
        seen = set(urls)
        soup = BeautifulSoup(html or "", "html.parser")

        for anchor in soup.find_all("a", href=True):
            parsed = urlparse(urljoin(base_url, anchor["href"]))
            if parsed.netloc != base.netloc:
                continue
            if not parsed.path.rstrip("/").startswith(f"{listing_path}/page/"):
                continue
            normalized = urlunparse((
                parsed.scheme or "https",
                parsed.netloc,
                parsed.path,
                "",
                parsed.query,
                "",
            ))
            if normalized in seen:
                continue
            seen.add(normalized)
            urls.append(normalized)
        return urls

    async def _fetch_all_raw_data(self, urls: list[str]):
        self._detail_url_by_fetch_url = {url: url for url in urls}
        return await super()._fetch_all_raw_data(urls)

    def _normalize_event(self, event: JsonLdEvent, detail_url: str) -> None:
        event.same_as = detail_url
        event.url = urljoin(detail_url, event.url)
        for offer in event.offers:
            if offer.url:
                offer.url = urljoin(detail_url, offer.url)
            else:
                offer.url = detail_url

        if event.start_date.tzinfo is None:
            event.start_date = (
                event.start_date
                .replace(tzinfo=timezone.utc)
                .astimezone(ZoneInfo(self.club.timezone or "America/Chicago"))
            )

    def _is_future_show(self, show: Show) -> bool:
        if show.date.tzinfo:
            return show.date >= datetime.now(show.date.tzinfo)
        return show.date >= datetime.now()

    def _exclude_title_re(self) -> Pattern[str] | None:
        raw = (self.club.source_metadata or {}).get(
            "exclude_title_patterns",
            _DEFAULT_EXCLUDE_TITLE_PATTERNS,
        )
        if raw is False or raw is None:
            return None
        if isinstance(raw, str):
            patterns = [raw]
        elif isinstance(raw, list):
            patterns = [str(item) for item in raw if item]
        else:
            patterns = _DEFAULT_EXCLUDE_TITLE_PATTERNS
        if not patterns:
            return None
        return re.compile("|".join(f"(?:{pattern})" for pattern in patterns), re.IGNORECASE)
