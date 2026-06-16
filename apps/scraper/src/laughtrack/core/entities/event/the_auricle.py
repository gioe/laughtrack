"""Data model for a single comedy event scraped from The Auricle (Canton, OH)."""

from dataclasses import dataclass
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class TheAuricleEvent(ShowConvertible):
    """
    A single comedy event at The Auricle (Canton, OH).

    The Auricle is primarily a live-music/variety venue; its event listings come
    from its Facebook Page, surfaced on theauricle.net/events via a SociableKit
    widget backed by the data.accentapi.com JSON feed. The extractor keeps only
    comedy events (e.g. the recurring "Comedy Open Mic"); music/drag/karaoke
    events are excluded.

    Fields:
      name     ← Facebook event name
      dt_str   ← local "YYYY-MM-DD HH:MM:00" (from start_date_raw + start_time)
      url      ← ticket URI if present, else the Facebook event page
      price    ← advertised ticket price (None when free / unknown)
    """

    name: str
    dt_str: str
    url: str
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this event to a Show domain object."""
        try:
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.dt_str, club.timezone or "America/New_York"
            )
        except Exception:
            return None

        ticket_url = url or self.url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
