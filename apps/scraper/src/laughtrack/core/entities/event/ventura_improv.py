"""Data model for a single show scraped from Ventura Improv Company (club 8884).

venturaimprov.com/shows is a hand-maintained WordPress page whose "Coming Up"
GenerateBlocks block lists one upcoming show at a time (no JSON-LD, no tribe
API). The extractor parses that block into VenturaImprovEvent objects; tickets
are sold off-site via NAMBA Arts (Tickera/WooCommerce), so the per-show ticket
URL points at the nambaarts.com event page.
"""

from dataclasses import dataclass
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# Stable fallback when a show has no off-site ticket link in the block.
_SHOWS_URL = "https://venturaimprov.com/shows/"


@dataclass
class VenturaImprovEvent(ShowConvertible):
    """A single upcoming show from the Ventura Improv "Coming Up" block.

    Fields:
      name      ← the show title (e.g. "Improv Match")
      dt_str    ← local "YYYY-MM-DD HH:MM:00" computed by the extractor
      price     ← lowest advertised online price (None if unknown)
      ticket_url← off-site ticket page (nambaarts.com) or the shows page
    """

    name: str
    dt_str: str
    price: Optional[float] = None
    ticket_url: str = _SHOWS_URL

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this show to a Show domain object, or None if unparseable."""
        try:
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.dt_str, club.timezone or "America/Los_Angeles"
            )
        except Exception:
            return None

        ticket_url = url or self.ticket_url or _SHOWS_URL
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
