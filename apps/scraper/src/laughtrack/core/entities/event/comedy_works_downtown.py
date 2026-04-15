"""Data model for a single event scraped from Comedy Works Downtown."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# "Thursday, Apr 16 2026  7:15PM"  — double-space before time
_DATETIME_RE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*,\s+"  # day-of-week + comma
    r"(\w{3}\s+\d{1,2}\s+\d{4})"               # "Apr 16 2026"
    r"\s+"                                       # whitespace (often double-space)
    r"(\d{1,2}:\d{2}\s*[AP]M)",                 # "7:15PM"
    re.IGNORECASE,
)


@dataclass
class ComedyWorksDowntownShowtime:
    """A single showtime within a comedian's engagement at Comedy Works Downtown."""

    datetime_str: str       # e.g. "Thursday, Apr 16 2026  7:15PM"
    age_restriction: str    # e.g. "21+"
    sold_out: bool
    tiers: List[dict] = field(default_factory=list)   # [{"name": "General", "price": 30.0, "sold_out": False}]
    section_id: str = ""    # seating-sections-19425 → "19425"


@dataclass
class ComedyWorksDowntownEvent(ShowConvertible):
    """
    Data model for a comedian's engagement at Comedy Works Downtown.

    Each event represents one comedian + one showtime. The scraper flattens
    multi-showtime detail pages into individual events for the pipeline.
    """

    slug: str                           # e.g. "craig-conant"
    name: str                           # e.g. "Craig Conant"
    showtime: ComedyWorksDowntownShowtime = field(default_factory=lambda: ComedyWorksDowntownShowtime(datetime_str="", age_restriction="", sold_out=False))

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Convert this single-showtime event to a Show object."""
        return self._showtime_to_show(self.showtime, club, enhanced)

    def _showtime_to_show(
        self, st: ComedyWorksDowntownShowtime, club: Club, enhanced: bool
    ) -> Optional[Show]:
        try:
            m = _DATETIME_RE.search(st.datetime_str)
            if not m:
                return None

            date_part = m.group(1)  # "Apr 16 2026"
            time_part = m.group(2).strip()  # "7:15PM"
            # Ensure space before AM/PM
            time_part = re.sub(r"(\d)([AP]M)", r"\1 \2", time_part, flags=re.IGNORECASE)

            dt_obj = datetime.strptime(f"{date_part} {time_part}", "%b %d %Y %I:%M %p")
            dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")

            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, club.timezone or "America/Denver"
            )
        except Exception:
            return None

        ticket_url = f"https://www.comedyworks.com/comedians/{self.slug}"

        # Build tickets from tiers
        tickets: List[Ticket] = []
        for tier in st.tiers:
            tickets.append(
                Ticket(
                    price=tier.get("price", 0.0),
                    purchase_url=ticket_url,
                    sold_out=tier.get("sold_out", False),
                    type=tier.get("name", "General Admission"),
                )
            )

        if not tickets:
            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=st.sold_out)
            )

        # Build description
        desc_parts = []
        if st.age_restriction:
            desc_parts.append(f"Ages: {st.age_restriction}")
        description = ShowFactoryUtils.build_description_from_parts(desc_parts)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=ShowFactoryUtils.create_lineup_from_performers([self.name] if self.name else []),
            tickets=tickets,
            description=description,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
