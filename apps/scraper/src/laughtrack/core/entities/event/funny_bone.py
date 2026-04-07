"""
Funny Bone Comedy Club event data model.

Represents a single show extracted from the Funny Bone shows listing page.
All data (title, date, time, prices, ticket URL) is available on the listing
page — no per-event detail fetching is required.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class FunnyBoneEvent:
    """A single show from a Funny Bone Comedy Club listing page."""

    name: str
    date_text: str           # e.g. "Tue, Apr 21"
    time_text: str           # e.g. "Doors: 5:45 pm // Show: 7 pm"
    price_text: str          # e.g. "$32 to $57"
    event_url: str           # e.g. "https://omaha.funnybone.com/event/anna-przy/..."
    ticket_url: str          # Etix URL
    description: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Transform this event into a Show object."""
        try:
            start_dt = self._parse_datetime(club.timezone)
            if not start_dt:
                Logger.error(
                    f"Could not parse date/time for '{self.name}': "
                    f"date='{self.date_text}', time='{self.time_text}'"
                )
                return None

            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.name,
                club=club,
                date=start_dt,
                show_page_url=self.event_url,
                lineup=[],
                tickets=self._extract_tickets(),
                description=self.description,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Failed to transform FunnyBoneEvent '{self.name}': {e}")
            return None

    def _parse_datetime(self, timezone: str) -> Optional[datetime]:
        """
        Parse date and time from listing page text.

        Date format: "Tue, Apr 21" or "Fri, May 09 - Sat, May 10" (multi-day).
        Time format: "Doors: 5:45 pm // Show: 7 pm" or "Show: 9:45 pm".
        """
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)

            # Extract the first date from potentially multi-day text
            # e.g. "Fri, May 09 - Sat, May 10" → use "Fri, May 09"
            date_str = self.date_text.split(' - ')[0].strip()

            # Parse "Tue, Apr 21" → month + day
            date_match = re.match(r'\w+,\s+(\w+)\s+(\d+)', date_str)
            if not date_match:
                return None

            month_str, day_str = date_match.group(1), date_match.group(2)

            # Determine year — if the month is before current month, it's next year
            try:
                month_num = datetime.strptime(month_str, "%b").month
            except ValueError:
                return None

            year = now.year
            if month_num < now.month or (month_num == now.month and int(day_str) < now.day):
                year += 1

            # Extract show time from time_text
            show_time_match = re.search(r'Show:\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', self.time_text, re.I)
            if show_time_match:
                time_str = show_time_match.group(1)
            else:
                # Fallback: try doors time
                doors_match = re.search(r'Doors:\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', self.time_text, re.I)
                if doors_match:
                    time_str = doors_match.group(1)
                else:
                    time_str = "8 pm"  # default

            # Parse time
            try:
                time_dt = datetime.strptime(time_str.strip(), "%I:%M %p")
            except ValueError:
                try:
                    time_dt = datetime.strptime(time_str.strip(), "%I %p")
                except ValueError:
                    return None

            naive = datetime(year, month_num, int(day_str), time_dt.hour, time_dt.minute)
            return tz.localize(naive, is_dst=False)

        except Exception as e:
            Logger.error(f"Error parsing FunnyBone date/time: {e}")
            return None

    def _extract_tickets(self) -> List[Ticket]:
        """Extract ticket info from price text like '$32 to $57'."""
        tickets: List[Ticket] = []
        try:
            prices = re.findall(r'\$(\d+(?:\.\d+)?)', self.price_text)
            if len(prices) >= 2:
                tickets.append(Ticket(price=float(prices[0]), purchase_url=self.ticket_url, type="Standard"))
                tickets.append(Ticket(price=float(prices[1]), purchase_url=self.ticket_url, type="Premium"))
            elif len(prices) == 1:
                tickets.append(Ticket(price=float(prices[0]), purchase_url=self.ticket_url, type="General Admission"))
        except Exception as e:
            Logger.error(f"Failed to extract tickets for '{self.name}': {e}")
        return tickets
