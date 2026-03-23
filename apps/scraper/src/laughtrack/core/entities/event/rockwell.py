"""Data model for a single event from The Rockwell's Tribe Events REST API."""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_SOLD_OUT_RE = re.compile(r"^\s*SOLD\s+OUT!?\s*", re.IGNORECASE)


@dataclass
class RockwellEvent(ShowConvertible):
    """
    Data model for a single event from The Rockwell's Tribe Events REST API.

    The API endpoint is:
      https://therockwell.org/wp-json/tribe/events/v1/events

    Fields map directly from the API response.
    """

    id: str
    title: str
    start_date: str  # "YYYY-MM-DD HH:MM:SS" local time
    timezone: str  # e.g. "America/New_York"
    url: str  # WordPress event-page URL (also used as ticket link)
    cost: str  # e.g. "$15 – $25" (display string)
    cost_values: List[str] = field(default_factory=list)  # ["15", "25"]
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a RockwellEvent to a Show domain object."""
        name = _SOLD_OUT_RE.sub("", self.title).strip() or "Comedy Show"

        try:
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.start_date, self.timezone or club.timezone
            )
        except Exception:
            return None

        show_url = url or self.url

        tickets = []
        if self.cost_values:
            try:
                price = float(self.cost_values[0])
                tickets.append(ShowFactoryUtils.create_fallback_ticket(show_url, price=price))
            except (ValueError, TypeError):
                pass
        if not tickets and show_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(show_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
