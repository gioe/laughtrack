"""
Data model for a single event from a FriendlySky ticketing platform.

FriendlySky is used by Delirious Comedy Club (and potentially other venues).
Events are fetched from the REST API at:
  GET /rest/events/$<eventHash>?_branch=findByDomainNameOrHashId&_s=1

The API returns a JSON envelope with a ``data.games`` array.  Each game object
contains the show name (comma-separated comedian names), date/time, venue info,
and a ``hashId`` used to construct the ticket purchase URL.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class FriendlySkyEvent(ShowConvertible):
    """A single game/show from the FriendlySky API."""

    hash_id: str
    name: str
    beg_date: str        # "YYYY-MM-DD"
    beg_time: str        # "HH:MM" (24-hour)
    venue_name: str
    status: str          # "Y" = active
    url_name: str        # slug for ticket page
    hash_event_id: str   # parent event hash (e.g. "EKR")
    base_url: str        # e.g. "https://tickets.deliriouscomedyclub.com"
    description: str = ""
    doors: str = ""
    ages: str = ""

    @classmethod
    def from_api_response(cls, data: dict, base_url: str) -> "FriendlySkyEvent":
        """Create a FriendlySkyEvent from a raw API game dict."""
        return cls(
            hash_id=data.get("hashId") or "",
            name=data.get("name") or "",
            beg_date=data.get("begDate") or "",
            beg_time=data.get("begTime") or "",
            venue_name=data.get("venueName") or "",
            status=data.get("status") or "",
            url_name=data.get("urlName") or "",
            hash_event_id=data.get("hashEventId") or "",
            base_url=base_url,
            description=data.get("description") or "",
            doors=data.get("doors") or "",
            ages=data.get("ages") or "",
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.name or not self.beg_date or not self.beg_time:
            return None

        try:
            start_date = datetime.strptime(
                f"{self.beg_date} {self.beg_time}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            return None

        ticket_url = f"{self.base_url}/event?e={self.hash_event_id}&g={self.hash_id}"
        show_page_url = ticket_url

        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
