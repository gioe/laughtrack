"""Extract SeeTickets/Eventim whitelabel event cards from rendered HTML."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

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

    @staticmethod
    def extract_calendar_events(html: str, base_url: str) -> list[SeeTicketsWhitelabelEvent]:
        """Read the official SeeTickets WordPress calendar with explicit years.

        The calendar includes events omitted from the homepage grid. Its
        doortime-showtime paragraph is the show time; the following paragraph
        is doors. Never infer a year or substitute doors for a missing showtime.
        An incomplete calendar is not safe input for stale-show reconciliation.
        """
        soup = BeautifulSoup(html or "", "html.parser")
        tables = soup.select("table.seetickets-calendar")
        cards = soup.select(".seetickets-calendar-event-container")
        if not tables or not cards:
            raise ValueError("SeeTickets calendar has no verified event cards")
        events: dict[str, SeeTicketsWhitelabelEvent] = {}
        parsed_cards = 0
        for table in tables:
            heading = table.find_previous_sibling()
            if heading is None or "seetickets-calendar-year-month-container" not in heading.get("class", []):
                raise ValueError("SeeTickets calendar month heading is missing")
            month = datetime.strptime(heading.get_text(" ", strip=True), "%B %Y")
            for card in table.select(".seetickets-calendar-event-container"):
                cell = card.find_parent("td")
                day = cell.select_one(".date-number") if cell else None
                title = card.select_one(".seetickets-calendar-event-title a[href]")
                time = card.select_one(".seetickets-calendar-event-date p.doortime-showtime")
                if day is None or title is None or time is None:
                    raise ValueError("SeeTickets calendar event identity/date/showtime is missing")
                name = title.get_text(" ", strip=True)
                ticket_url = urljoin(base_url, title["href"])
                ident = _EVENT_ID_RE.search(urlparse(ticket_url).path)
                if not name or not ident or urlparse(ticket_url).hostname not in {"wl.seetickets.us", "wl.eventim.us"}:
                    raise ValueError("SeeTickets calendar ticket identity is invalid")
                clock = datetime.strptime(time.get_text("", strip=True).replace(" ", "").upper(), "%I:%M%p")
                start = month.replace(day=int(day.get_text(strip=True)), hour=clock.hour, minute=clock.minute)
                event_id = ident.group("id")
                event = SeeTicketsWhitelabelEvent(
                    event_id=event_id,
                    name=name,
                    start_date=start.strftime("%B %d %Y"),
                    ticket_url=ticket_url,
                    start_datetime=start.isoformat(),
                )
                prior = events.get(event_id)
                if prior and (prior.name, prior.start_datetime) != (event.name, event.start_datetime):
                    raise ValueError(f"SeeTickets calendar event {event_id} has conflicting performances")
                events[event_id] = event
                parsed_cards += 1
        if parsed_cards != len(cards):
            raise ValueError("SeeTickets calendar contains event cards outside dated month tables")
        return list(events.values())
