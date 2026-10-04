"""Extract SeeTickets/Eventim whitelabel event cards from rendered HTML."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.seetickets_whitelabel import SeeTicketsWhitelabelEvent
from laughtrack.foundation.utilities.number import parse_price_text

_BUY_LABEL_RE = re.compile(r"^Buy tickets for (?P<name>.+) on (?P<date>[A-Za-z]+ \d{1,2} \d{4})$")
_EVENT_ID_RE = re.compile(r"/event/[^/?#]+/(?P<id>\d+)")
_PRICE_RE = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*[-–]\s*\$\d+(?:,\d{3})*(?:\.\d{2})?)?")


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
                    sold_out=card.select_one(".button-soldout") is not None,
                )
                prior = events.get(event_id)
                if prior and (prior.name, prior.start_datetime) != (event.name, event.start_datetime):
                    raise ValueError(f"SeeTickets calendar event {event_id} has conflicting performances")
                events[event_id] = event
                parsed_cards += 1
        if parsed_cards != len(cards):
            raise ValueError("SeeTickets calendar contains event cards outside dated month tables")
        SeeTicketsWhitelabelExtractor._attach_calendar_prices(soup, events, base_url)
        return list(events.values())

    @staticmethod
    def _attach_calendar_prices(soup: BeautifulSoup, events: dict[str, SeeTicketsWhitelabelEvent], base_url: str):
        """Join parallel list evidence to the calendar's dated performance.

        List dates omit the year: the calendar owns it. Every occurrence for
        an ID must agree, including its date, show clock, price and buy link.
        This avoids selecting the cheapest of conflicting or stale cards.
        """
        evidence: dict[str, set[tuple[float, str] | None]] = {}

        def identity(href):
            parsed = urlparse(urljoin(base_url, href or ""))
            match = _EVENT_ID_RE.fullmatch(parsed.path.rstrip("/"))
            return (parsed.hostname, match.group("id")) if match else None

        for card in soup.select(".seetickets-list-event-content-container"):
            title = card.select_one(".event-info-block .event-title a[href]")
            ident = identity(title.get("href")) if title else None
            if ident is None or ident[1] not in events:
                continue
            event = events[ident[1]]
            values = evidence.setdefault(event.event_id, set())
            date = card.select_one(".event-info-block .event-date")
            clock = card.select_one(".event-info-block .see-showtime")
            prices = card.select(".event-info-block .price")
            buy = card.select_one("a.seetickets-buy-btn[href]")
            value = None
            if (
                ident == identity(event.ticket_url)
                and date is not None
                and clock is not None
                and len(prices) == 1
                and buy is not None
                and identity(buy.get("href")) == ident
                and buy.get_text(" ", strip=True).casefold() == "buy tickets"
                and not event.sold_out
            ):
                start = datetime.fromisoformat(event.start_datetime)
                try:
                    listed = datetime.strptime(
                        f"{date.get_text(' ', strip=True)} {start.year} {clock.get_text('', strip=True)}",
                        "%a %b %d %Y %I:%M%p",
                    )
                except ValueError:
                    listed = None
                text = prices[0].get_text(" ", strip=True)
                price = (
                    parse_price_text(text, detect_free=False, dollar_only=True) if _PRICE_RE.fullmatch(text) else None
                )
                if (
                    listed == start
                    and date.get_text(" ", strip=True).split()[0] == start.strftime("%a")
                    and price is not None
                    and price > 0
                ):
                    value = (price, text)
            values.add(value)

        for event_id, values in evidence.items():
            if len(values) == 1 and None not in values:
                events[event_id].price, events[event_id].price_text = next(iter(values))
