"""
Largo at the Coronet event data model.

Represents a single show extracted from the largo-la.com WordPress listing page.
Date format: "Fri Apr 10", time in spans: "Show: 8:00 PM", price in div.price.
Ticket URLs point to wl.seetickets.us.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class LargoAtTheCoronetEvent:
    """A single show from the Largo at the Coronet listing page."""

    name: str
    date_text: str       # e.g. "Fri Apr 10"
    time_text: str       # e.g. "Will Call: 6:00 PM / Doors: 7:00 PM / Show: 8:00 PM"
    price_text: str      # e.g. "$40.00"
    ticket_url: str      # SeeTickets URL

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
                show_page_url=self.ticket_url,
                lineup=[],
                tickets=self._extract_tickets(),
                description=None,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Failed to transform LargoAtTheCoronetEvent '{self.name}': {e}")
            return None

    def _parse_datetime(self, timezone: str) -> Optional[datetime]:
        """
        Parse date and time from listing page text.

        Date format: "Fri Apr 10" (day-of-week month day).
        Time format: "Will Call: 6:00 PM / Doors: 7:00 PM / Show: 8:00 PM".
        """
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)

            # Parse "Fri Apr 10" -> month + day
            date_match = re.match(r'\w+\s+(\w+)\s+(\d+)', self.date_text.strip())
            if not date_match:
                return None

            month_str, day_str = date_match.group(1), date_match.group(2)

            try:
                month_num = datetime.strptime(month_str, "%b").month
            except ValueError:
                return None

            year = now.year
            if month_num < now.month or (month_num == now.month and int(day_str) < now.day):
                year += 1

            # Extract show time
            show_time_match = re.search(r'Show:\s*(\d{1,2}(?::\d{2})?\s*[AP]M)', self.time_text, re.I)
            if show_time_match:
                time_str = show_time_match.group(1)
            else:
                doors_match = re.search(r'Doors:\s*(\d{1,2}(?::\d{2})?\s*[AP]M)', self.time_text, re.I)
                if doors_match:
                    time_str = doors_match.group(1)
                else:
                    time_str = "8:00 PM"

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
            Logger.error(f"Error parsing Largo date/time: {e}")
            return None

    def _extract_tickets(self) -> List[Ticket]:
        """Extract ticket info from price text like '$40.00'."""
        tickets: List[Ticket] = []
        try:
            prices = re.findall(r'\$(\d+(?:\.\d+)?)', self.price_text)
            if prices:
                tickets.append(Ticket(
                    price=float(prices[0]),
                    purchase_url=self.ticket_url,
                    type="General Admission",
                ))
        except Exception as e:
            Logger.error(f"Failed to extract tickets for '{self.name}': {e}")
        return tickets
