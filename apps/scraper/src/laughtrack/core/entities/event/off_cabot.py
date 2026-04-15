"""
Off Cabot Comedy and Events event data model.

Represents a single show extracted from an Off Cabot event detail page.
Each show_row on a detail page becomes a separate OffCabotEvent with its
own date, time, price, and ticket URL.
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
class OffCabotEvent:
    """A single show from an Off Cabot event detail page."""

    name: str
    date_text: str       # e.g. "April 16, 2026"
    time_text: str       # e.g. "7:00pm"
    price_text: str      # e.g. "$36.60"
    ticket_url: str      # Etix URL or thecabot.org/book/ URL
    event_page_url: str  # thecabot.org/event/<slug>/

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
                show_page_url=self.event_page_url,
                lineup=[],
                tickets=self._extract_tickets(),
                description=None,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Failed to transform OffCabotEvent '{self.name}': {e}")
            return None

    def _parse_datetime(self, timezone: str) -> Optional[datetime]:
        """
        Parse date and time from event detail page text.

        Date format: "April 16, 2026"
        Time format: "7:00pm"
        """
        try:
            tz = pytz.timezone(timezone)

            # Parse "April 16, 2026"
            date_match = re.match(r'(\w+)\s+(\d{1,2}),\s*(\d{4})', self.date_text.strip())
            if not date_match:
                return None

            month_str = date_match.group(1)
            day = int(date_match.group(2))
            year = int(date_match.group(3))

            try:
                month_num = datetime.strptime(month_str, "%B").month
            except ValueError:
                try:
                    month_num = datetime.strptime(month_str, "%b").month
                except ValueError:
                    return None

            # Parse "7:00pm" or "8:00pm"
            time_match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)', self.time_text.strip(), re.I)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                ampm = time_match.group(3).lower()
                if ampm == "pm" and hour != 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
            else:
                hour, minute = 20, 0  # default 8pm

            naive = datetime(year, month_num, day, hour, minute)
            return tz.localize(naive, is_dst=False)

        except Exception as e:
            Logger.error(f"Error parsing OffCabot date/time: {e}")
            return None

    def _extract_tickets(self) -> List[Ticket]:
        """Extract ticket info from price text like '$36.60'."""
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
