"""HTML extraction for TPAC's Polk Theater comedy endpoint."""

import json
from dataclasses import replace
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.tpac_james_k_polk import TpacJamesKPolkEvent
from laughtrack.foundation.utilities.html.utils import HtmlUtils

_BASE_URL = "https://www.tpac.org"


class TpacJamesKPolkExtractor:
    """Parse TPAC category JSON payloads and event detail pages."""

    @staticmethod
    def extract_category_events(
        payload: str,
        base_url: str = _BASE_URL,
    ) -> List[TpacJamesKPolkEvent]:
        """Extract event cards from the JSON string returned by category_json."""
        html = TpacJamesKPolkExtractor._coerce_html(payload)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[TpacJamesKPolkEvent] = []
        seen: set[str] = set()

        for card in TpacJamesKPolkExtractor._event_cards(soup):
            event = TpacJamesKPolkExtractor._parse_card(card, base_url)
            if event is None or event.detail_url in seen:
                continue
            seen.add(event.detail_url)
            events.append(event)

        return events

    @staticmethod
    def enrich_event_from_detail_page(
        event: TpacJamesKPolkEvent,
        html: str,
    ) -> TpacJamesKPolkEvent:
        """Return ``event`` enriched with detail-page fields."""
        return TpacJamesKPolkExtractor.enrich_events_from_detail_page(event, html)[0]

    @staticmethod
    def enrich_events_from_detail_page(
        event: TpacJamesKPolkEvent,
        html: str,
    ) -> List[TpacJamesKPolkEvent]:
        """Return enriched events, expanding multi-showing detail pages."""
        if not html:
            return [event]

        soup = BeautifulSoup(html, "html.parser")
        title = TpacJamesKPolkExtractor._text_from(soup, ".event_heading h1.title") or event.title
        date_str = TpacJamesKPolkExtractor._text_from(soup, ".sidebar_event_date span") or event.date_str
        time_values = TpacJamesKPolkExtractor._extract_showing_times(soup)
        if not time_values:
            time_values = [
                TpacJamesKPolkExtractor._text_from(soup, ".sidebar_event_starts span")
                or event.time_str
            ]
        venue = TpacJamesKPolkExtractor._text_from(soup, ".sidebar_event_venue span") or event.venue
        ticket_url = TpacJamesKPolkExtractor._extract_ticket_url(soup, event.detail_url) or event.ticket_url
        description = TpacJamesKPolkExtractor._extract_description(soup) or event.description

        return [
            replace(
                event,
                title=title,
                date_str=date_str,
                time_str=time_str,
                venue=venue,
                ticket_url=ticket_url,
                description=description,
            )
            for time_str in time_values
            if time_str
        ] or [event]

    @staticmethod
    def _coerce_html(payload: str) -> str:
        value = (payload or "").strip()
        if not value:
            return ""
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(decoded, str):
            return decoded.strip()
        if isinstance(decoded, dict):
            for key in ("html", "events", "data", "content"):
                html = decoded.get(key)
                if isinstance(html, str):
                    return html.strip()
        return ""

    @staticmethod
    def _event_cards(soup: BeautifulSoup) -> list[Tag]:
        cards = soup.select(".event_card, .event-card, .eventItem, .entry, article")
        if cards:
            return [card for card in cards if isinstance(card, Tag)]
        return [
            parent
            for parent in (link.find_parent(["div", "article", "li"]) for link in soup.select('a[href*="/events/detail/"]'))
            if isinstance(parent, Tag)
        ]

    @staticmethod
    def _parse_card(card: Tag, base_url: str) -> TpacJamesKPolkEvent | None:
        detail_el = card.select_one('a[href*="/events/detail/"]')
        if detail_el is None:
            return None

        title_el = (
            card.select_one(".event_card_title, .event-card-title, h3, h2")
            or detail_el
        )
        title = TpacJamesKPolkExtractor._clean(title_el.get_text(" ", strip=True))
        detail_url = urljoin(base_url, detail_el.get("href", "").strip())
        ticket_el = card.select_one("a.tickets[href], a.ticket[href], a.button[href]")
        ticket_url = (
            urljoin(base_url, ticket_el.get("href", "").strip())
            if ticket_el is not None
            else ""
        )
        if not title or not detail_url:
            return None

        return TpacJamesKPolkEvent(
            title=title,
            detail_url=detail_url,
            ticket_url=ticket_url,
        )

    @staticmethod
    def _extract_ticket_url(soup: BeautifulSoup, base_url: str) -> str:
        ticket_el = soup.select_one(".buttons a.tickets[href], a.tickets[href]")
        if ticket_el is None:
            return ""
        return urljoin(base_url, ticket_el.get("href", "").strip())

    @staticmethod
    def _extract_showing_times(soup: BeautifulSoup) -> list[str]:
        times = []
        seen: set[str] = set()
        for time_el in soup.select(".showings_wrapper .time"):
            value = TpacJamesKPolkExtractor._clean(time_el.get_text(" ", strip=True))
            if value and value not in seen:
                seen.add(value)
                times.append(value)
        return times

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        wrapper = soup.select_one(".description_wrapper") or soup.select_one(".event_description")
        if wrapper is None:
            return ""
        for el in wrapper.select("script, style, .buttons, .button, .btn"):
            el.decompose()
        return TpacJamesKPolkExtractor._clean(wrapper.get_text(" ", strip=True))

    @staticmethod
    def _text_from(root: BeautifulSoup | Tag, selector: str) -> str:
        el = root.select_one(selector)
        return TpacJamesKPolkExtractor._clean(el.get_text(" ", strip=True)) if el else ""

    @staticmethod
    def _clean(value: str) -> str:
        return HtmlUtils.strip_tags(value or "", normalize_whitespace=True).replace(" ,", ",")
