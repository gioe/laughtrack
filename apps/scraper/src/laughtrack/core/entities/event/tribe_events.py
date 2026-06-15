"""Data model for a single event from a The Events Calendar (Tribe) REST API.

"The Events Calendar" is a widely-used WordPress plugin that exposes a public
REST API at ``/wp-json/tribe/events/v1/events``. The response shape is
identical across every site running the plugin, so this entity is shared by
all venues onboarded via the generic ``the_events_calendar`` scraper.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_SOLD_OUT_RE = re.compile(r"^\s*SOLD\s+OUT!?\s*", re.IGNORECASE)


@dataclass
class TribeEvent(ShowConvertible):
    """A single event from a The Events Calendar (Tribe) REST API response.

    Fields map directly from the API JSON returned by
    ``/wp-json/tribe/events/v1/events``.
    """

    id: str
    title: str
    start_date: str  # "YYYY-MM-DD HH:MM:SS" local time
    timezone: str  # e.g. "America/New_York"
    url: str  # WordPress event-page URL (also used as ticket link)
    cost: str  # e.g. "$15 – $25" or "Varies" (display string)
    cost_values: List[str] = field(default_factory=list)  # ["15", "25"]
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a TribeEvent to a Show domain object."""
        is_sold_out = bool(_SOLD_OUT_RE.match(self.title))
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
                tickets.append(ShowFactoryUtils.create_fallback_ticket(show_url, price=price, sold_out=is_sold_out))
            except (ValueError, TypeError):
                pass
        if not tickets and show_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(show_url, sold_out=is_sold_out))

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
