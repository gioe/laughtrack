"""HTML extractor for Flappers calendar and show detail pages."""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.flappers import FlappersEvent, FlappersTicketTier

_TIME_RE = re.compile(r"\d{1,2}(?::\d{2})?\s*(?:AM|PM)", re.IGNORECASE)
_PRICE_RE = re.compile(r"\$(\d+(?:\.\d{2})?)")

# Room name normalization
_ROOM_MAP = {
    "main room": "Main Room",
    "mainroom": "Main Room",
    "yoo hoo room": "Yoo Hoo Room",
    "bar": "Bar",
    "patio": "Patio",
}


@dataclass
class ShowDetails:
    """Extracted data from a Flappers show detail page."""

    lineup_names: List[str] = field(default_factory=list)
    ticket_tiers: List[FlappersTicketTier] = field(default_factory=list)
    description: Optional[str] = None


def _normalize_room(raw: str) -> str:
    """Normalize room text from the button content."""
    lower = raw.lower().strip()
    for key, val in _ROOM_MAP.items():
        if key in lower:
            return val
    return raw.strip()


def _extract_month_year(url: str) -> tuple[int, int]:
    """Extract month and year from calendar URL query params."""
    from datetime import date

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    today = date.today()
    month = int(qs.get("month", [str(today.month)])[0])
    year = int(qs.get("year", [str(today.year)])[0])
    return month, year


class FlappersEventExtractor:
    """Static extractor for Flappers calendar and show detail HTML."""

    @staticmethod
    def extract_shows(html: str, url: str = "", timezone: str = "America/Los_Angeles") -> List[FlappersEvent]:
        """Parse Flappers calendar HTML and return all show events.

        Each calendar day cell (<td>) contains <form> elements with
        <button class="event-btn"> holding show data.
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[FlappersEvent] = []

        month, year = _extract_month_year(url) if url else (0, 0)

        for td in soup.find_all("td"):
            day_tag = td.find("strong")
            if not day_tag:
                continue
            try:
                day = int(day_tag.get_text(strip=True))
            except ValueError:
                continue

            for form in td.find_all("form"):
                event = FlappersEventExtractor._parse_form(
                    form, year, month, day, timezone
                )
                if event:
                    events.append(event)

        return events

    @staticmethod
    def extract_show_details(html: str) -> Optional[ShowDetails]:
        """Parse a Flappers show detail page (shows.php?event_id=N).

        Extracts:
          - Lineup from <div class="also-starring"> <a> tags
          - Ticket tiers from <ul class="ticket-list"> radio inputs + price divs
          - Description from <span id="showDesc" data-full="...">
        """
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        details = ShowDetails()

        # --- Lineup ---
        starring_div = soup.find("div", class_="also-starring")
        if starring_div:
            for a_tag in starring_div.find_all("a"):
                name = a_tag.get_text(strip=True)
                if name:
                    details.lineup_names.append(name)

        # --- Ticket tiers ---
        ticket_list = soup.find("ul", id="ticket_choices")
        if ticket_list:
            for li in ticket_list.find_all("li"):
                tier = FlappersEventExtractor._parse_ticket_card(li)
                if tier:
                    details.ticket_tiers.append(tier)

        # --- Description ---
        desc_span = soup.find("span", id="showDesc")
        if desc_span:
            full_desc = desc_span.get("data-full", "")
            if full_desc:
                details.description = full_desc

        return details

    @staticmethod
    def _parse_ticket_card(li: Tag) -> Optional[FlappersTicketTier]:
        """Parse a single <li> ticket card into a FlappersTicketTier."""
        card = li.find("label", class_="ticket-card")
        if not card:
            return None

        radio = card.find("input", class_="ticket-radio")
        if not radio:
            return None

        # Sold out check
        sold_out = "is-soldout" in (card.get("class") or [])

        # Remaining tickets
        remaining = None
        data_left = radio.get("data-left", "")
        if data_left:
            try:
                remaining = int(data_left)
            except ValueError:
                pass

        # Ticket type/description
        ticket_type = radio.get("data-description", "General Admission") or "General Admission"

        # Price from .ticket-price div
        price = 0.0
        price_div = card.find("div", class_="ticket-price")
        if price_div:
            price_text = price_div.get_text(strip=True)
            price_match = _PRICE_RE.search(price_text)
            if price_match:
                price = float(price_match.group(1))

        return FlappersTicketTier(
            price=price,
            ticket_type=ticket_type,
            sold_out=sold_out,
            remaining=remaining,
        )

    @staticmethod
    def _parse_form(
        form: Tag, year: int, month: int, day: int, timezone: str
    ) -> Optional[FlappersEvent]:
        """Parse a single <form> element into a FlappersEvent."""
        event_id_input = form.find("input", {"name": "event_id"})
        if not event_id_input:
            return None
        event_id = event_id_input.get("value", "")
        if not event_id:
            return None

        btn = form.find("button", class_="event-btn")
        if not btn:
            return None

        title_tag = btn.find("b")
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        if not title:
            return None

        data_type = btn.get("data-type", "")
        room = _normalize_room(data_type) if data_type else ""

        btn_text = btn.get_text(separator="\n", strip=True)
        time_match = _TIME_RE.search(btn_text)
        time_str = time_match.group(0) if time_match else ""

        if not time_str:
            return None

        return FlappersEvent(
            title=title,
            event_id=event_id,
            year=year,
            month=month,
            day=day,
            time_str=time_str,
            timezone=timezone,
            room=room,
        )
