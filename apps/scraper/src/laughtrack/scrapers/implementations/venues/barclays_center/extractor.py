"""HTML extraction for Barclays Center's official comedy category."""

from dataclasses import replace
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.barclays_center import BarclaysCenterEvent
from laughtrack.foundation.utilities.html.utils import HtmlUtils

_BASE_URL = "https://www.barclayscenter.com"


class BarclaysCenterExtractor:
    """Parse Barclays Center category listing and detail pages."""

    @staticmethod
    def extract_listing_events(html: str, base_url: str = _BASE_URL) -> List[BarclaysCenterEvent]:
        """Extract event cards from the official comedy category listing."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[BarclaysCenterEvent] = []
        seen: set[str] = set()

        for card in soup.select("#list .entry"):
            event = BarclaysCenterExtractor._parse_listing_card(card, base_url)
            if event is None or event.detail_url in seen:
                continue
            seen.add(event.detail_url)
            events.append(event)

        return events

    @staticmethod
    def enrich_event_from_detail_page(
        event: BarclaysCenterEvent,
        html: str,
    ) -> BarclaysCenterEvent:
        """Return ``event`` enriched with detail-page date, time, ticket URL, and copy."""
        if not html:
            return event

        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one(".event-details") or soup
        title = BarclaysCenterExtractor._extract_title(root) or event.title
        date_str = BarclaysCenterExtractor._extract_date(root) or event.date_str
        time_str = BarclaysCenterExtractor._extract_time(root) or event.time_str
        ticket_url = BarclaysCenterExtractor._extract_ticket_url(root, event.detail_url) or event.ticket_url
        description = BarclaysCenterExtractor._extract_description(root) or event.description

        return replace(
            event,
            title=title,
            date_str=date_str,
            time_str=time_str,
            ticket_url=ticket_url,
            description=description,
        )

    @staticmethod
    def _parse_listing_card(card: Tag, base_url: str) -> BarclaysCenterEvent | None:
        title_el = card.select_one("a.title-container h3") or card.select_one("h3")
        detail_el = card.select_one('a.title-container[href]') or card.select_one('a.more[href]')
        ticket_el = card.select_one('a.tickets[href*="ticketmaster.com/event/"]')
        if not (title_el and detail_el):
            return None

        title = BarclaysCenterExtractor._clean(title_el.get_text(" ", strip=True))
        detail_url = urljoin(base_url, detail_el.get("href", "").strip())
        ticket_url = (
            urljoin(base_url, ticket_el.get("href", "").strip())
            if ticket_el is not None
            else ""
        )
        if not title or not detail_url:
            return None

        return BarclaysCenterEvent(
            title=title,
            date_str="",
            time_str="",
            detail_url=detail_url,
            ticket_url=ticket_url,
        )

    @staticmethod
    def _extract_title(root: Tag) -> str:
        title_el = root.select_one("h1.summary") or root.select_one("h1")
        return BarclaysCenterExtractor._clean(title_el.get_text(" ", strip=True)) if title_el else ""

    @staticmethod
    def _extract_date(root: Tag) -> str:
        date_li = root.select_one("li.date")
        if date_li is None:
            return ""

        month = BarclaysCenterExtractor._text_from(date_li, ".m-date__month")
        day = BarclaysCenterExtractor._text_from(date_li, ".m-date__day")
        year = BarclaysCenterExtractor._text_from(date_li, ".m-date__year").lstrip(", ")
        if not (month and day and year):
            return ""
        return BarclaysCenterExtractor._clean(f"{month} {day}, {year}")

    @staticmethod
    def _extract_time(root: Tag) -> str:
        date_li = root.select_one("li.date")
        time_el = date_li.select_one(".time") if date_li is not None else None
        return BarclaysCenterExtractor._clean(time_el.get_text(" ", strip=True)) if time_el else ""

    @staticmethod
    def _extract_ticket_url(root: Tag, base_url: str) -> str:
        for link in root.select('a.tickets[href*="ticketmaster.com/event/"]'):
            href = link.get("href", "").strip()
            if href:
                return urljoin(base_url, href)
        return ""

    @staticmethod
    def _extract_description(root: Tag) -> str:
        info = root.select_one(".event-info")
        if info is None:
            return ""
        heading = info.select_one("h2, h3")
        if heading is not None:
            heading.decompose()
        for button in info.select(".button, .btn, script, style"):
            button.decompose()
        return BarclaysCenterExtractor._clean(info.get_text(" ", strip=True))

    @staticmethod
    def _text_from(root: Tag, selector: str) -> str:
        el = root.select_one(selector)
        return BarclaysCenterExtractor._clean(el.get_text(" ", strip=True)) if el else ""

    @staticmethod
    def _clean(value: str) -> str:
        return HtmlUtils.strip_tags(value or "", normalize_whitespace=True)
