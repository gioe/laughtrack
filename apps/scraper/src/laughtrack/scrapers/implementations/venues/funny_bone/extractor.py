"""
Funny Bone Comedy Club data extraction utilities.

Extracts event data from the Funny Bone shows listing page HTML.
All event data (title, date, time, prices, ticket URL) is available
on the listing page — no per-event detail fetching is needed.
"""

import re
from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.funny_bone import FunnyBoneEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class FunnyBoneExtractor:
    """Pure parsing utilities for Funny Bone Comedy Club listing pages."""

    @staticmethod
    def extract_events(html: str) -> List[FunnyBoneEvent]:
        """
        Extract all events from a Funny Bone shows listing page.

        Parses the Rockhouse Partners WordPress theme event cards
        (class="rhpSingleEvent") to extract event details.
        """
        events: List[FunnyBoneEvent] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("div", class_="rhpSingleEvent")

            for card in cards:
                event = FunnyBoneExtractor._parse_event_card(card)
                if event:
                    events.append(event)

        except Exception as e:
            Logger.error(f"FunnyBoneExtractor: Failed to extract events: {e}")

        return events

    @staticmethod
    def _parse_event_card(card) -> Optional[FunnyBoneEvent]:
        """Parse a single rhpSingleEvent card into a FunnyBoneEvent."""
        try:
            # Title + event URL
            title_link = card.find("a", id="eventTitle")
            if not title_link:
                return None
            name = title_link.get("title") or title_link.get_text(strip=True)
            event_url = title_link.get("href", "")

            if not name or not event_url:
                return None

            # Date (e.g. "Tue, Apr 21")
            date_el = card.find(class_="singleEventDate")
            date_text = date_el.get_text(strip=True) if date_el else ""

            # Time (e.g. "Doors: 5:45 pm // Show: 7 pm")
            time_el = card.find(class_=re.compile(r"rhp-event__time-text"))
            time_text = time_el.get_text(strip=True) if time_el else ""

            # Price (e.g. "$32 to $57")
            price_el = card.find(class_=re.compile(r"rhp-event__cost-text"))
            price_text = price_el.get_text(strip=True) if price_el else ""

            # Etix ticket URL
            etix_link = card.find("a", href=re.compile(r"etix\.com", re.I))
            ticket_url = etix_link.get("href", "") if etix_link else event_url

            if not date_text:
                return None

            return FunnyBoneEvent(
                name=name,
                date_text=date_text,
                time_text=time_text,
                price_text=price_text,
                event_url=event_url,
                ticket_url=ticket_url,
            )
        except Exception as e:
            Logger.error(f"FunnyBoneExtractor: Failed to parse event card: {e}")
            return None
