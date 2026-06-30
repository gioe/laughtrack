"""Extract SeeTickets/Eventim whitelabel event cards from rendered HTML."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.seetickets_whitelabel import SeeTicketsWhitelabelEvent

_BUY_LABEL_RE = re.compile(r"^Buy tickets for (?P<name>.+) on (?P<date>[A-Za-z]+ \d{1,2} \d{4})$")
_EVENT_ID_RE = re.compile(r"/event/[^/?#]+/(?P<id>\d+)")


class SeeTicketsWhitelabelExtractor:
    @staticmethod
    def extract_events(html: str, base_url: str) -> list[SeeTicketsWhitelabelEvent]:
        soup = BeautifulSoup(html or "", "html.parser")
        events: list[SeeTicketsWhitelabelEvent] = []
        seen_ids: set[str] = set()

        for anchor in soup.select('a[href*="/event/"][aria-label^="Buy tickets for"]'):
            label = (anchor.get("aria-label") or "").strip()
            match = _BUY_LABEL_RE.match(label)
            if not match:
                continue
            href = (anchor.get("href") or "").strip()
            id_match = _EVENT_ID_RE.search(href)
            if not id_match:
                continue
            event_id = id_match.group("id")
            if event_id in seen_ids:
                continue

            card = anchor.find_parent(class_="search-event")
            location = ""
            image_url = ""
            if card is not None:
                location_node = card.select_one(".event-location")
                if location_node is not None:
                    location = location_node.get_text(" ", strip=True)
                image_node = card.select_one("img[src]")
                if image_node is not None:
                    image_url = urljoin(base_url, image_node.get("src") or "")

            events.append(
                SeeTicketsWhitelabelEvent(
                    event_id=event_id,
                    name=match.group("name").strip(),
                    start_date=match.group("date").strip(),
                    ticket_url=urljoin(base_url, href),
                    location=location,
                    image_url=image_url,
                )
            )
            seen_ids.add(event_id)
        return events
