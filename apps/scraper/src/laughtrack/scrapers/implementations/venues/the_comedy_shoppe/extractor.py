"""ShowSlinger widget data extraction.

Parses the HTML returned by the promo_widget_v3/combo_widget endpoint.
Each event card may list multiple showtimes; this extractor expands them
into one ShowSlingerEvent per showtime.
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.show_slinger import ShowSlingerEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_BASE_URL = "https://app.showslinger.com"

# Matches "Sat, May  2, 3:00 pm" or "Thu, June  4, 7:00 pm"
_FULL_DATE_RE = re.compile(
    r"[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{1,2}:\d{2}\s*[ap]m)",
    re.IGNORECASE,
)

# Matches bare time like "7:30 PM" or "4:00 PM"
_TIME_ONLY_RE = re.compile(r"(\d{1,2}:\d{2}\s*[AP]M)", re.IGNORECASE)

# Matches "$10", "$54.99", etc.
_PRICE_RE = re.compile(r"\$([\d,]+(?:\.\d{2})?)")

# Event card CSS selector
_EVENT_CARD_SEL = "div.signUP-admin"


class ShowSlingerExtractor:
    """Extracts ShowSlingerEvent objects from a ShowSlinger combo widget page."""

    @staticmethod
    def extract_events(html_content: str) -> List[ShowSlingerEvent]:
        """Parse all event cards from the ShowSlinger combo widget HTML."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            events: List[ShowSlingerEvent] = []

            for card in soup.select(_EVENT_CARD_SEL):
                card_events = ShowSlingerExtractor._parse_event_card(card)
                events.extend(card_events)

            Logger.info(f"ShowSlinger: extracted {len(events)} events")
            return events

        except Exception as e:
            Logger.error(f"ShowSlinger: failed to extract events: {e}")
            return []

    @staticmethod
    def _parse_event_card(card: Tag) -> List[ShowSlingerEvent]:
        """Parse a single event card, expanding multiple showtimes into separate events."""
        try:
            # Title
            title_el = card.select_one("h4.widget-name")
            if not title_el:
                return []
            name = title_el.get_text(strip=True)

            # Ticket link and ID
            ticket_link = card.select_one("a.mrk_ticket_event_url")
            if not ticket_link:
                return []
            href = ticket_link.get("href", "")
            ticket_id_match = re.search(r"ticket_payment/(\d+)", href)
            if not ticket_id_match:
                return []

            ticket_id = ticket_id_match.group(1)
            ticket_url = f"{_BASE_URL}/ticket_payment/{ticket_id}/checkout_ticket"

            # Image
            img_el = card.select_one("img.grid-img")
            image_url = img_el.get("src") if img_el else None

            # Price
            price = ShowSlingerExtractor._extract_price(card)

            # Sold out
            sold_out = bool(card.find(string=re.compile(r"sold\s*out", re.IGNORECASE)))

            # Showtimes — two patterns:
            # 1. Multiple full-date spans: "Sat, May  2, 3:00 pm"
            # 2. Single time-only span: "7:30 PM" with date from the badge
            time_spans = card.select("span.widget-time")
            date_badge = card.select_one(".widget-date-month")

            showtimes = ShowSlingerExtractor._parse_showtimes(
                time_spans, date_badge
            )
            if not showtimes:
                return []

            return [
                ShowSlingerEvent(
                    name=name,
                    date_time=dt,
                    ticket_url=ticket_url,
                    ticket_id=ticket_id,
                    price=price,
                    image_url=image_url,
                    sold_out=sold_out,
                )
                for dt in showtimes
            ]

        except Exception as e:
            Logger.warn(f"ShowSlinger: failed to parse event card: {e}")
            return []

    @staticmethod
    def _parse_showtimes(
        time_spans: List[Tag], date_badge: Optional[Tag]
    ) -> List[datetime]:
        """Parse showtime spans into datetime objects.

        Handles two formats:
        - Full date: "Sat, May  2, 3:00 pm"  (month + day + time in span)
        - Time only: "7:30 PM"  (date comes from the date badge like "Apr 27")
        """
        results: List[datetime] = []
        current_year = datetime.now().year

        for span in time_spans:
            text = span.get_text(strip=True)
            dt = ShowSlingerExtractor._parse_full_date_time(text, current_year)
            if dt:
                results.append(dt)
                continue

            # Fall back to time-only with date badge
            if date_badge:
                dt = ShowSlingerExtractor._parse_time_with_badge(
                    text, date_badge.get_text(strip=True), current_year
                )
                if dt:
                    results.append(dt)

        return results

    @staticmethod
    def _parse_full_date_time(text: str, year: int) -> Optional[datetime]:
        """Parse 'Sat, May  2, 3:00 pm' into a datetime."""
        match = _FULL_DATE_RE.search(text)
        if not match:
            return None
        month_str, day_str, time_str = match.group(1), match.group(2), match.group(3)
        return ShowSlingerExtractor._build_datetime(month_str, day_str, time_str, year)

    @staticmethod
    def _parse_time_with_badge(
        time_text: str, badge_text: str, year: int
    ) -> Optional[datetime]:
        """Parse '7:30 PM' with badge 'Apr 27' into a datetime."""
        time_match = _TIME_ONLY_RE.search(time_text)
        if not time_match:
            return None
        time_str = time_match.group(1)

        # Badge format: "Apr 27", "May  2", "June 14"
        badge_match = re.match(r"([A-Za-z]+)\s+(\d{1,2})", badge_text.strip())
        if not badge_match:
            return None
        month_str, day_str = badge_match.group(1), badge_match.group(2)
        return ShowSlingerExtractor._build_datetime(month_str, day_str, time_str, year)

    @staticmethod
    def _build_datetime(
        month_str: str, day_str: str, time_str: str, year: int
    ) -> Optional[datetime]:
        """Build a datetime from month name, day, time string, and year.

        Tries both abbreviated ('May') and full ('August') month formats.
        If the resulting date is in the past, bumps to next year.
        """
        date_string = f"{month_str} {day_str} {year} {time_str}"
        for fmt in ("%B %d %Y %I:%M %p", "%b %d %Y %I:%M %p"):
            try:
                dt = datetime.strptime(date_string, fmt)
                # If the date is more than 30 days in the past, assume next year
                if (datetime.now() - dt).days > 30:
                    dt = dt.replace(year=year + 1)
                return dt
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_price(card: Tag) -> Optional[float]:
        """Extract the first dollar price from the card text."""
        # Look for a dedicated price element first
        price_el = card.select_one(".widget-price, .price")
        text = price_el.get_text() if price_el else card.get_text()
        match = _PRICE_RE.search(text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                pass
        return None
