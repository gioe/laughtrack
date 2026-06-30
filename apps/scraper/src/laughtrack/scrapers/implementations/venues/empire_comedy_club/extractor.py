"""Empire Comedy Club data extraction from the shows listing page."""

import re
from datetime import datetime
from typing import List, Optional, Sequence

from laughtrack.core.entities.event.empire import EmpireEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
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
                    events.extend(EmpireEventExtractor._parse_show_card(card, year))

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
    def _parse_show_card(card, year: int) -> List[EmpireEvent]:
        """Parse a single <article class="show-card"> into EmpireEvent objects.

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
                return []
            name = h3.get_text(strip=True)
            href = h3.get("href", "")
            show_page_url = f"{BASE_URL}{href}" if href.startswith("/") else href

            # Status
            status_el = card.select_one("p.status")
            status = status_el.get_text(strip=True) if status_el else None

            # Date: second <p class="meta"> has "Apr 16" format
            meta_tags = card.select("p.meta")
            if len(meta_tags) < 2:
                return []
            date_text = meta_tags[1].get_text(strip=True)  # e.g. "Apr 16"

            # Time: <time> element inside <p class="time">
            time_el = card.select_one("p.time time")
            time_text = time_el.get_text(strip=True) if time_el else ""

            date_times = EmpireEventExtractor._parse_date_times(date_text, time_text, year)
            if not date_times:
                return []

            return [
                EmpireEvent(
                    name=name,
                    date_time=date_time,
                    show_page_url=show_page_url,
                    status=status,
                )
                for date_time in date_times
            ]

        except Exception as e:
            Logger.warn(f"Empire Comedy Club: failed to parse show card: {e}")
            return []

    @staticmethod
    def _parse_date_times(date_text: str, time_text: str, year: int) -> List[datetime]:
        """Parse card date/time text into one datetime per performance.

        Args:
            date_text: Month and day, e.g. "Apr 16" or "Jul 10-11"
            time_text: Time string, e.g. "7:00 PM" or "7:00 PM & 9:30 PM"
            year: Four-digit year from the month section header
        """
        if not time_text:
            return []

        dates = EmpireEventExtractor._expand_date_text(date_text)
        times = EmpireEventExtractor._split_time_text(time_text)
        date_times: List[datetime] = []

        for date_part in dates:
            for time_part in times:
                parsed = DateTimeUtils.parse_flexible_date(f"{date_part} {year} {time_part}")
                if parsed:
                    date_times.append(parsed)

        return date_times

    @staticmethod
    def _expand_date_text(date_text: str) -> Sequence[str]:
        """Expand Empire date text into date parts parseable with a year/time."""
        normalized = " ".join(date_text.split())
        same_month_range = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2})-(\d{1,2})", normalized)
        if not same_month_range:
            return [normalized]

        month, start_day_text, end_day_text = same_month_range.groups()
        start_day = int(start_day_text)
        end_day = int(end_day_text)
        if end_day < start_day:
            return [normalized]

        return [f"{month} {day}" for day in range(start_day, end_day + 1)]

    @staticmethod
    def _split_time_text(time_text: str) -> List[str]:
        """Split combined Empire time text into individual time strings."""
        parts = [part.strip() for part in re.split(r"\s*(?:&|,|\band\b)\s*", time_text) if part.strip()]
        if len(parts) < 2:
            return parts

        trailing_meridiem = None
        for part in reversed(parts):
            match = re.search(r"\b([AP]M)\b", part, re.IGNORECASE)
            if match:
                trailing_meridiem = match.group(1).upper()
                break

        if not trailing_meridiem:
            return parts

        return [
            part if re.search(r"\b[AP]M\b", part, re.IGNORECASE) else f"{part} {trailing_meridiem}"
            for part in parts
        ]
