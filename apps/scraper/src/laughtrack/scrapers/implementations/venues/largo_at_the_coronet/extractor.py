"""
Largo at the Coronet data extraction utilities.

Extracts event data from the largo-la.com WordPress listing page HTML.
Events are rendered as <article class="event_listing"> elements with
title, date, time, price, and SeeTickets ticket URLs.
"""

from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.largo_at_the_coronet import LargoAtTheCoronetEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class LargoAtTheCoronetExtractor:
    """Pure parsing utilities for Largo at the Coronet listing pages."""

    @staticmethod
    def extract_events(html: str) -> List[LargoAtTheCoronetEvent]:
        """Extract all events from the Largo shows listing page."""
        events: List[LargoAtTheCoronetEvent] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("article", class_="event_listing")

            for card in cards:
                event = LargoAtTheCoronetExtractor._parse_event_card(card)
                if event:
                    events.append(event)

        except Exception as e:
            Logger.error(f"LargoAtTheCoronetExtractor: Failed to extract events: {e}")

        return events

    @staticmethod
    def _parse_event_card(card) -> Optional[LargoAtTheCoronetEvent]:
        """Parse a single event_listing article into a LargoAtTheCoronetEvent."""
        try:
            # Title + ticket URL from h2 > a
            h2 = card.find("h2")
            if not h2:
                return None
            title_link = h2.find("a")
            if not title_link:
                return None

            name = title_link.get("title") or title_link.get_text(strip=True)
            ticket_url = title_link.get("href", "")

            if not name or not ticket_url:
                return None

            # Date and time from <p> inside event-details
            details_div = card.find("div", class_="event-details")
            if not details_div:
                return None

            p_tag = details_div.find("p")
            if not p_tag:
                return None

            # The <p> contains: "Fri Apr 10 <br> <span>Will Call: ...</span> ..."
            # Get the date text (text before <br>)
            date_text = ""
            for child in p_tag.children:
                if hasattr(child, 'name') and child.name == 'br':
                    break
                if isinstance(child, str):
                    date_text += child.strip()

            # Get time text from spans
            spans = p_tag.find_all("span")
            time_text = " ".join(span.get_text(strip=True) for span in spans)

            if not date_text:
                return None

            # Price from div.price
            price_el = card.find("div", class_="price")
            price_text = price_el.get_text(strip=True) if price_el else ""

            return LargoAtTheCoronetEvent(
                name=name,
                date_text=date_text,
                time_text=time_text,
                price_text=price_text,
                ticket_url=ticket_url,
            )
        except Exception as e:
            Logger.error(f"LargoAtTheCoronetExtractor: Failed to parse event card: {e}")
            return None
