"""
Revolution Hall data extraction utilities.

Extracts event data from the Revolution Hall homepage HTML.
Events are rendered in a custom WordPress theme with Etix ticket links.
Only events for the main hall (class "event-wrapper revolution-hall") are
extracted — Show Bar events are excluded.
"""

import re
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.revolution_hall import RevolutionHallEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class RevolutionHallExtractor:
    """Pure parsing utilities for Revolution Hall listing pages."""

    @staticmethod
    def extract_events(html: str) -> List[RevolutionHallEvent]:
        """Extract all main-hall events from the Revolution Hall homepage."""
        events: List[RevolutionHallEvent] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            wrappers = soup.find_all("div", class_="event-wrapper")

            for wrapper in wrappers:
                if not RevolutionHallExtractor._is_main_hall(wrapper):
                    continue
                event_div = wrapper.find("div", class_="event")
                if not event_div:
                    continue
                event = RevolutionHallExtractor._parse_event(event_div)
                if event:
                    events.append(event)

        except Exception as e:
            Logger.error(f"RevolutionHallExtractor: Failed to extract events: {e}")

        return events

    @staticmethod
    def _is_main_hall(wrapper: Tag) -> bool:
        """Check if the event wrapper is for the main hall (not Show Bar)."""
        classes = wrapper.get("class", [])
        return "revolution-hall" in classes and "show-bar-at-revolution-hall" not in classes

    @staticmethod
    def _parse_event(event_div: Tag) -> Optional[RevolutionHallEvent]:
        """Parse a single event div into a RevolutionHallEvent."""
        try:
            # Title from h3[itemprop="name"] > a
            h3 = event_div.find("h3", attrs={"itemprop": "name"})
            if not h3:
                return None
            title_link = h3.find("a")
            if not title_link:
                return None

            name = title_link.get_text(strip=True)
            ticket_url = title_link.get("href", "")

            if not name or not ticket_url:
                return None

            # Date from span.event-date--full (e.g. "Fri, April 10th, 2026")
            date_el = event_div.find("span", class_="event-date--full")
            date_text = date_el.get_text(strip=True) if date_el else ""

            # ISO datetime from data-event-doors attribute
            doors_el = event_div.find("span", class_="event-doors-showtime")
            doors_iso = doors_el.get("data-event-doors", "") if doors_el else ""
            time_text = doors_el.get_text(strip=True) if doors_el else ""

            # Age restriction
            age_el = event_div.find("span", class_="event-age-restriction")
            age_text = age_el.get_text(strip=True) if age_el else ""

            # Presenter from the <p> inside event__content (e.g. "OUTBACK PRESENTS")
            content_div = event_div.find("div", class_="event__content")
            presenter = ""
            if content_div:
                p_tag = content_div.find("p")
                if p_tag:
                    presenter = p_tag.get_text(strip=True)

            # Status from button class
            status_link = event_div.find("a", class_=re.compile(r"event-status--"))
            status = "on_sale"
            if status_link:
                classes = status_link.get("class", [])
                if "event-status--sold-out" in classes:
                    status = "sold_out"
                elif "event-status--not-on-sale" in classes:
                    status = "not_on_sale"

            # Image URL from cdn.etix.com
            img = event_div.find("img", src=re.compile(r"cdn\.etix\.com"))
            image_url = img.get("src", "") if img else ""

            if not date_text and not doors_iso:
                return None

            return RevolutionHallEvent(
                name=name,
                date_text=date_text,
                doors_iso=doors_iso,
                time_text=time_text,
                ticket_url=ticket_url,
                age_restriction=age_text,
                status=status,
                image_url=image_url,
            )
        except Exception as e:
            Logger.error(f"RevolutionHallExtractor: Failed to parse event: {e}")
            return None
