"""Empire Comedy Club data extraction from the shows listing page."""

import re
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.event.empire import EmpireEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

BASE_URL = "https://empirecomedyme.com"


class EmpireEventExtractor:
    """Extracts EmpireEvent objects from the empirecomedyme.com/shows/ listing page."""

    @staticmethod
    def extract_events(html_content: str) -> List[EmpireEvent]:
        """Parse all show cards from the shows listing page.

        The page is organized into month sections (<section class="month-section"
        data-month-section="April 2026">) containing <article class="show-card">
        elements. The year is taken from the month section header since individual
        cards only display abbreviated dates like "Apr 16".
        """
        try:
            soup = HtmlScraper._parse_html(html_content)
            events: List[EmpireEvent] = []

            for section in soup.select("section.month-section"):
                year = EmpireEventExtractor._extract_year_from_section(section)
                if not year:
                    continue

                for card in section.select("article.show-card"):
                    event = EmpireEventExtractor._parse_show_card(card, year)
                    if event:
                        events.append(event)

            Logger.info(f"Empire Comedy Club: extracted {len(events)} events")
            return events

        except Exception as e:
            Logger.error(f"Empire Comedy Club: failed to extract events: {e}")
            return []

    @staticmethod
    def _extract_year_from_section(section) -> Optional[int]:
        """Extract the year from a month section's data-month-section attribute.

        Attribute format: "April 2026", "May 2026", etc.
        """
        month_label = section.get("data-month-section", "")
        match = re.search(r"\d{4}", month_label)
        if match:
            return int(match.group())
        return None

    @staticmethod
    def _parse_show_card(card, year: int) -> Optional[EmpireEvent]:
        """Parse a single <article class="show-card"> into an EmpireEvent.

        Card structure:
          <h3><a href="/show/slug">Show Name</a></h3>
          <p class="status ...">On Sale</p>
          <p class="meta">Thu</p>        (day of week)
          <p class="meta">Apr 16</p>     (month + day)
          <p class="time"><time>7:00 PM</time></p>
        """
        try:
            # Name + URL from h3 > a
            h3 = card.select_one("h3 a")
            if not h3:
                return None
            name = h3.get_text(strip=True)
            href = h3.get("href", "")
            show_page_url = f"{BASE_URL}{href}" if href.startswith("/") else href

            # Status
            status_el = card.select_one("p.status")
            status = status_el.get_text(strip=True) if status_el else None

            # Date: second <p class="meta"> has "Apr 16" format
            meta_tags = card.select("p.meta")
            if len(meta_tags) < 2:
                return None
            date_text = meta_tags[1].get_text(strip=True)  # e.g. "Apr 16"

            # Time: <time> element inside <p class="time">
            time_el = card.select_one("p.time time")
            time_text = time_el.get_text(strip=True) if time_el else ""

            date_time = EmpireEventExtractor._parse_date_time(date_text, time_text, year)
            if not date_time:
                return None

            return EmpireEvent(
                name=name,
                date_time=date_time,
                show_page_url=show_page_url,
                status=status,
            )

        except Exception as e:
            Logger.warn(f"Empire Comedy Club: failed to parse show card: {e}")
            return None

    @staticmethod
    def _parse_date_time(date_text: str, time_text: str, year: int) -> Optional[datetime]:
        """Parse 'Apr 16' + '7:00 PM' + year into a naive datetime.

        Args:
            date_text: Month and day, e.g. "Apr 16"
            time_text: Time string, e.g. "7:00 PM" or "9:00 PM"
            year: Four-digit year from the month section header
        """
        try:
            # Parse "Apr 16" with year
            dt = datetime.strptime(f"{date_text} {year}", "%b %d %Y")

            # Parse time
            time_match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                ampm = time_match.group(3).upper()
                if ampm == "PM" and hour != 12:
                    hour += 12
                elif ampm == "AM" and hour == 12:
                    hour = 0
                dt = dt.replace(hour=hour, minute=minute)

            return dt
        except ValueError:
            return None
