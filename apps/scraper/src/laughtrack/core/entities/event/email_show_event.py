"""
Shared event model for email-based scrapers.

EmailShowEvent represents a single comedy show parsed from a venue newsletter.
It implements the ShowConvertible protocol and is used by email scraper
implementations for Comedy Cellar and Gotham Comedy Club.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class EmailShowEvent:
    """
    A show event parsed from a venue email newsletter.

    Attributes:
        date:        Parsed show datetime (timezone-aware).
        headliner:   Name of the headlining comedian.
        ticket_link: URL for purchasing tickets or making a reservation.
        show_name:   Optional show title; falls back to headliner name.
        room:        Optional venue room / stage name.
    """

    date: datetime
    headliner: str
    ticket_link: str
    show_name: Optional[str] = None
    room: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """
        Convert this email event into a Show object.

        The resulting Show is compatible with the upsert pipeline used by
        the corresponding web scraper for the same venue: both set the same
        club, a timezone-aware date, and a headliner-derived lineup.

        Args:
            club:     Club entity this show belongs to.
            enhanced: Whether to run enhanced validation/processing.
            url:      Unused; present for ShowConvertible protocol compliance.

        Returns:
            Show object, or None if a required field is missing.
        """
        try:
            name = self.show_name or self.headliner
            if not name or not self.date:
                return None

            lineup = ShowFactoryUtils.create_lineup_from_performers([self.headliner])
            tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url=self.ticket_link)]

            return ShowFactoryUtils.create_enhanced_show_base(
                name=name,
                club=club,
                date=self.date,
                show_page_url=self.ticket_link,
                lineup=lineup,
                tickets=tickets,
                room=self.room or "",
                supplied_tags=["comedy"],
                enhanced=enhanced,
            )
        except Exception:
            return None
