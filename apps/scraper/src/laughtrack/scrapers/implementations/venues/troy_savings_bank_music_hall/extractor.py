"""HTML extraction for Troy Savings Bank Music Hall's official events pages."""

from dataclasses import replace
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.troy_savings_bank_music_hall import (
    TroySavingsBankMusicHallEvent,
)
from laughtrack.foundation.utilities.html.utils import HtmlUtils

_BASE_URL = "https://www.troymusichall.org"
_LIST_YEAR = 2026


class TroySavingsBankMusicHallExtractor:
    """Parse Troy Savings Bank Music Hall list and detail pages."""

    @staticmethod
    def extract_listing_events(
        html: str,
        base_url: str = _BASE_URL,
        *,
        year: int = _LIST_YEAR,
    ) -> list[TroySavingsBankMusicHallEvent]:
        """Extract event cards from the rendered comedy listing page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: list[TroySavingsBankMusicHallEvent] = []
        seen: set[tuple[str, str, str]] = set()

        for card in soup.select(".show-item"):
            title_el = card.select_one(".show-title a[href]")
            month_el = card.select_one(".show-date-short .month")
            day_el = card.select_one(".show-date-short .day")
            time_el = card.select_one(".show-date-short .time")
            if not (title_el and month_el and day_el and time_el):
                continue

            title = TroySavingsBankMusicHallExtractor._clean(
                title_el.get("title") or title_el.get_text(" ", strip=True)
            )
            month = TroySavingsBankMusicHallExtractor._clean(
                month_el.get_text(" ", strip=True)
            )
            day = TroySavingsBankMusicHallExtractor._clean(day_el.get_text(" ", strip=True))
            time_str = TroySavingsBankMusicHallExtractor._clean(
                time_el.get_text(" ", strip=True)
            )
            detail_url = urljoin(base_url, title_el.get("href", ""))
            ticket_el = card.select_one(".show-links a.buyticket[href]")
            ticket_url = (
                urljoin(base_url, ticket_el.get("href", "")) if ticket_el else ""
            )
            subtitle_el = card.select_one(".show-subHead")
            subtitle = (
                TroySavingsBankMusicHallExtractor._clean(
                    subtitle_el.get_text(" ", strip=True)
                )
                if subtitle_el
                else ""
            )

            if not (title and month and day and time_str and detail_url):
                continue

            date_str = f"{month} {int(day)} {year}"
            key = (title, date_str, detail_url)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                TroySavingsBankMusicHallEvent(
                    title=title,
                    date_str=date_str,
                    time_str=time_str,
                    detail_url=detail_url,
                    ticket_url=ticket_url,
                    subtitle=subtitle,
                )
            )

        return events

    @staticmethod
    def enrich_event_from_detail_page(
        event: TroySavingsBankMusicHallEvent,
        html: str,
        base_url: str = _BASE_URL,
    ) -> TroySavingsBankMusicHallEvent:
        """Return ``event`` enriched with the detail page description and ticket URL."""
        if not html:
            return event

        soup = BeautifulSoup(html, "html.parser")
        ticket_url = event.ticket_url
        ticket_el = soup.select_one("#shows-tickets a.buyticket[href]")
        if ticket_el:
            ticket_url = urljoin(base_url, ticket_el.get("href", ""))

        detail_date_str, detail_time_str = (
            TroySavingsBankMusicHallExtractor._extract_start_datetime(soup)
        )
        description = TroySavingsBankMusicHallExtractor._extract_description(soup)
        return replace(
            event,
            date_str=detail_date_str or event.date_str,
            time_str=detail_time_str or event.time_str,
            ticket_url=ticket_url or event.ticket_url,
            description=description or event.description,
        )

    @staticmethod
    def detail_fetch_url(detail_url: str) -> str:
        """Preserve Troy's required trailing slash through URL normalization."""
        return detail_url if "?" in detail_url else f"{detail_url}?"

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        editor = soup.select_one(".editor.show-desc-editor")
        if editor is None:
            meta = soup.select_one('meta[name="Description"][content]')
            return TroySavingsBankMusicHallExtractor._clean(
                meta.get("content", "") if meta else ""
            )
        return TroySavingsBankMusicHallExtractor._clean(editor.get_text(" ", strip=True))

    @staticmethod
    def _extract_start_datetime(soup: BeautifulSoup) -> tuple[str, str]:
        start_el = soup.select_one('[itemprop="startDate"][content]')
        if start_el is None:
            return "", ""

        try:
            start_dt = datetime.fromisoformat(start_el.get("content", ""))
        except ValueError:
            return "", ""

        date_str = f"{start_dt:%b} {start_dt.day} {start_dt.year}"
        time_str = start_dt.strftime("%I:%M%p").lstrip("0")
        return date_str, time_str

    @staticmethod
    def _clean(value: str) -> str:
        return HtmlUtils.strip_tags(value or "", normalize_whitespace=True)
