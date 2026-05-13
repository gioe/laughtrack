"""HTML extraction for Soboba Casino Resort's public calendar."""

from dataclasses import replace
import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.soboba_casino_resort import SobobaCasinoResortEvent
from laughtrack.foundation.utilities.html.utils import HtmlUtils

_BASE_URL = "https://soboba.com"
_COMEDY_SIGNAL_RE = re.compile(
    r"\b(comed(?:y|ian|ic)|stand[- ]?up|laughs?|cholo\s*fit)\b",
    re.IGNORECASE,
)


class SobobaCasinoResortExtractor:
    """Parse Soboba calendar listing and detail pages."""

    @staticmethod
    def extract_listing_events(html: str, base_url: str = _BASE_URL) -> List[SobobaCasinoResortEvent]:
        """Extract all rendered event cards from a Soboba calendar listing page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[SobobaCasinoResortEvent] = []
        seen: set[tuple[str, str, str]] = set()

        for card in soup.select(".calendar-list-item.vevent"):
            title_el = card.select_one("h4")
            date_el = card.select_one("abbr.dtstart")
            time_el = card.select_one(".times abbr[title]")
            room_el = card.select_one(".cat-name")
            detail_el = card.select_one("a.button[href]") or card.select_one("a.thumb[href]")
            if not (title_el and date_el and time_el and detail_el):
                continue

            title = SobobaCasinoResortExtractor._clean(title_el.get_text(" ", strip=True))
            date_str = SobobaCasinoResortExtractor._clean(date_el.get_text(" ", strip=True))
            time_str = SobobaCasinoResortExtractor._clean(time_el.get("title", ""))
            room = (
                SobobaCasinoResortExtractor._clean(room_el.get_text(" ", strip=True))
                if room_el
                else ""
            )
            detail_url = urljoin(base_url, detail_el.get("href", ""))
            if not (title and date_str and time_str and detail_url):
                continue

            key = (title, date_str, detail_url)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                SobobaCasinoResortEvent(
                    title=title,
                    date_str=date_str,
                    time_str=time_str.split("-", 1)[0].strip(),
                    room=room,
                    detail_url=detail_url,
                )
            )

        return events

    @staticmethod
    def enrich_event_from_detail_page(
        event: SobobaCasinoResortEvent,
        html: str,
    ) -> SobobaCasinoResortEvent:
        """Return ``event`` enriched with ticket URL and detail description."""
        if not html:
            return event

        soup = BeautifulSoup(html, "html.parser")
        ticket_url = event.ticket_url
        ticket_link = soup.select_one('a.button[href*="yapsody.com"]')
        if ticket_link is not None:
            ticket_url = urljoin(event.detail_url, ticket_link.get("href", ""))

        description = SobobaCasinoResortExtractor._extract_description(soup)
        return replace(
            event,
            ticket_url=ticket_url,
            description=description or event.description,
        )

    @staticmethod
    def is_comedy_event(event: SobobaCasinoResortEvent) -> bool:
        """Return True when title/description contains comedy-specific signals."""
        text = " ".join(part for part in [event.title, event.description or ""] if part)
        return bool(_COMEDY_SIGNAL_RE.search(text))

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        paragraphs: list[str] = []
        for paragraph in soup.find_all("p"):
            if paragraph.find("a", href=True):
                continue
            text = SobobaCasinoResortExtractor._clean(paragraph.get_text(" ", strip=True))
            if not text:
                continue
            if "Soboba Casino Resort Event Center |" in text:
                continue
            paragraphs.append(text)
        return "\n\n".join(paragraphs)

    @staticmethod
    def _clean(value: str) -> str:
        return HtmlUtils.strip_tags(value or "", normalize_whitespace=True)
