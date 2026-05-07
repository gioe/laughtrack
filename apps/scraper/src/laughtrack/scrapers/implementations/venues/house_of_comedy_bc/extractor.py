"""Extraction for House of Comedy BC Webflow event cards."""

from datetime import datetime
from typing import List

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.house_of_comedy_bc import HouseOfComedyBcEvent

_TIXR_EVENT_FRAGMENT = "tixr.com/groups/comicstripbc/events/"


class HouseOfComedyBcExtractor:
    """Parse the Webflow day-card links on bc.houseofcomedy.net."""

    @staticmethod
    def extract_events(html: str, *, source_url: str) -> List[HouseOfComedyBcEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: list[HouseOfComedyBcEvent] = []
        seen_urls: set[str] = set()
        for card in soup.select(f'a.day-card[href*="{_TIXR_EVENT_FRAGMENT}"]'):
            if not isinstance(card, Tag):
                continue
            event = HouseOfComedyBcExtractor._parse_card(card, source_url=source_url)
            if event is None or event.ticket_url in seen_urls:
                continue
            seen_urls.add(event.ticket_url)
            events.append(event)
        return events

    @staticmethod
    def _parse_card(card: Tag, *, source_url: str) -> HouseOfComedyBcEvent | None:
        ticket_url = str(card.get("href") or "").strip()
        if not ticket_url:
            return None

        title = HouseOfComedyBcExtractor._text(card.select_one(".event-name.show"))
        room = HouseOfComedyBcExtractor._text(card.select_one(".event-name.spaced"))
        date_parts = [HouseOfComedyBcExtractor._text(node) for node in card.select(".date .b-venue")]
        date_parts = [part for part in date_parts if part]
        if len(date_parts) < 2:
            return None

        date = HouseOfComedyBcExtractor._date(date_parts[0])
        time = HouseOfComedyBcExtractor._time(date_parts[1])
        if not title or not date or not time:
            return None

        return HouseOfComedyBcEvent(
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
