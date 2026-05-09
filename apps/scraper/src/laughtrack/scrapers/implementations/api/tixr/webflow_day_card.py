"""Parameterized parser for venue-owned Webflow day-cards with Tixr ticket links.

Multiple venues (House of Comedy BC, The Comic Strip Edmonton, ...) publish a
Webflow homepage where each show is rendered as ``a.day-card`` whose ``href``
points at a Tixr group URL. Selectors and date/time formats are identical
across these venues; the only per-venue input is the Tixr group fragment used
to filter foreign cards.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.webflow_day_card import WebflowDayCardEvent
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


@dataclass(frozen=True)
class WebflowDayCardConfig:
    """Per-venue configuration for the Webflow + Tixr day-card pattern."""

    tixr_group_fragment: str


@dataclass
class WebflowDayCardPageData(EventListContainer[WebflowDayCardEvent]):
    """Webflow day-cards extracted from a venue homepage."""

    event_list: List[WebflowDayCardEvent]


class WebflowDayCardTransformer(DataTransformer[WebflowDayCardEvent]):
    """Identity transformer — events expose ``to_show`` directly."""

    pass


class WebflowDayCardExtractor:
    """Parse ``a.day-card`` Webflow links filtered by Tixr group fragment."""

    @staticmethod
    def extract_events(
        html: str,
        *,
        source_url: str,
        config: WebflowDayCardConfig,
    ) -> List[WebflowDayCardEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: list[WebflowDayCardEvent] = []
        seen_urls: set[str] = set()
        for card in soup.select(f'a.day-card[href*="{config.tixr_group_fragment}"]'):
            if not isinstance(card, Tag):
                continue
            event = WebflowDayCardExtractor._parse_card(card, source_url=source_url)
            if event is None or event.ticket_url in seen_urls:
                continue
            seen_urls.add(event.ticket_url)
            events.append(event)
        return events

    @staticmethod
    def _parse_card(card: Tag, *, source_url: str) -> WebflowDayCardEvent | None:
        ticket_url = str(card.get("href") or "").strip()
        if not ticket_url:
            return None

        title = WebflowDayCardExtractor._text(card.select_one(".event-name.show"))
        room = WebflowDayCardExtractor._text(card.select_one(".event-name.spaced"))
        date_parts = [
            WebflowDayCardExtractor._text(node) for node in card.select(".date .b-venue")
        ]
        date_parts = [part for part in date_parts if part]
        if len(date_parts) < 2:
            return None

        date = WebflowDayCardExtractor._date(date_parts[0])
        time = WebflowDayCardExtractor._time(date_parts[1])
        if not title or not date or not time:
            return None

        return WebflowDayCardEvent(
            title=title,
            date=date,
            time=time,
            ticket_url=ticket_url,
            source_url=source_url,
            room=room,
        )

    @staticmethod
    def _text(node: Tag | None) -> str:
        if node is None:
            return ""
        return " ".join(node.get_text(" ", strip=True).split())

    @staticmethod
    def _date(value: str) -> str:
        try:
            return datetime.strptime(value.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return ""

    @staticmethod
    def _time(value: str) -> str:
        try:
            return datetime.strptime(value.strip().upper(), "%I:%M %p").strftime("%-I:%M %p")
        except ValueError:
            return ""
