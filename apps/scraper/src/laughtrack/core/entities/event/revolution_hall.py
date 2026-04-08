"""
Revolution Hall event data model.

Represents a single show extracted from the Revolution Hall homepage.
The page provides an ISO datetime in the data-event-doors attribute,
making date parsing straightforward compared to text-only scrapers.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class RevolutionHallEvent:
    """A single show from the Revolution Hall homepage."""

    name: str
    date_text: str           # e.g. "Fri, April 10th, 2026"
    doors_iso: str           # e.g. "2026-04-11T01:00:00Z" (UTC doors time)
    time_text: str           # e.g. "Doors: 6PM / Show: 7PM"
    ticket_url: str          # e.g. "https://www.etix.com/ticket/p/77680474/..."
    age_restriction: str = ""
    status: str = "on_sale"
    image_url: str = ""

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Transform this event into a Show object."""
        try:
            start_dt = self._parse_datetime(club.timezone)
            if not start_dt:
                Logger.error(
                    f"Could not parse date/time for '{self.name}': "
                    f"doors_iso='{self.doors_iso}', time='{self.time_text}'"
                )
                return None

            # Strip "SOLD OUT:" prefix from names
            clean_name = re.sub(r'^SOLD\s*OUT\s*:?\s*', '', self.name, flags=re.I).strip()

            return ShowFactoryUtils.create_enhanced_show_base(
                name=clean_name,
                club=club,
                date=start_dt,
                show_page_url=self.ticket_url,
                lineup=[],
                tickets=[ShowFactoryUtils.create_fallback_ticket(self.ticket_url)],
                description="",
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Failed to transform RevolutionHallEvent '{self.name}': {e}")
            return None

    def _parse_datetime(self, timezone: str) -> Optional[datetime]:
        """
        Parse show datetime.

        Primary: use the doors_iso attribute (UTC ISO-8601) and extract the
        show time offset from time_text (e.g. "Doors: 6PM / Show: 7PM").

        Fallback: parse date_text (e.g. "Fri, April 10th, 2026") with
        show time from time_text.
        """
        tz = pytz.timezone(timezone)

        # Extract show time from time_text (prefer show time over doors time)
        show_hour, show_minute = self._extract_show_time()

        # Primary path: use doors_iso
        if self.doors_iso:
            try:
                doors_utc = datetime.fromisoformat(self.doors_iso.replace("Z", "+00:00"))
                doors_local = doors_utc.astimezone(tz)

                if show_hour is not None:
                    # Replace doors time with show time
                    return doors_local.replace(hour=show_hour, minute=show_minute)
                return doors_local
            except (ValueError, TypeError):
                pass

        # Fallback: parse date_text
        return self._parse_date_text(tz, show_hour, show_minute)

    def _extract_show_time(self) -> tuple:
        """Extract show start time from time_text like 'Doors: 6PM / Show: 7PM'."""
        if not self.time_text:
            return None, 0

        show_match = re.search(r'Show:\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)', self.time_text, re.I)
        if show_match:
            hour = int(show_match.group(1))
            minute = int(show_match.group(2)) if show_match.group(2) else 0
            ampm = show_match.group(3).upper()
            if ampm == "PM" and hour != 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0
            return hour, minute

        # Fallback to doors time
        doors_match = re.search(r'Doors:\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)', self.time_text, re.I)
        if doors_match:
            hour = int(doors_match.group(1))
            minute = int(doors_match.group(2)) if doors_match.group(2) else 0
            ampm = doors_match.group(3).upper()
            if ampm == "PM" and hour != 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0
            return hour, minute

        return None, 0

    def _parse_date_text(self, tz, show_hour, show_minute) -> Optional[datetime]:
        """Parse date from text like 'Fri, April 10th, 2026'."""
        try:
            if not self.date_text:
                return None

            # Remove ordinal suffixes (st, nd, rd, th)
            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', self.date_text)

            # Try "Day, Month DD, YYYY" format
            match = re.match(r'\w+,\s+(\w+)\s+(\d+),\s+(\d{4})', cleaned)
            if match:
                month_str, day_str, year_str = match.group(1), match.group(2), match.group(3)
                dt = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
                hour = show_hour if show_hour is not None else 20
                minute = show_minute if show_hour is not None else 0
                naive = dt.replace(hour=hour, minute=minute)
                return tz.localize(naive, is_dst=False)

            # Try "Day, Month DD" without year (infer year)
            match = re.match(r'\w+,\s+(\w+)\s+(\d+)', cleaned)
            if match:
                month_str, day_str = match.group(1), match.group(2)
                now = datetime.now(tz)
                dt = datetime.strptime(f"{month_str} {day_str}", "%B %d")
                year = now.year
                if dt.month < now.month or (dt.month == now.month and dt.day < now.day):
                    year += 1
                hour = show_hour if show_hour is not None else 20
                minute = show_minute if show_hour is not None else 0
                naive = datetime(year, dt.month, int(day_str), hour, minute)
                return tz.localize(naive, is_dst=False)

        except Exception as e:
            Logger.error(f"RevolutionHallEvent: Error parsing date text '{self.date_text}': {e}")

        return None
