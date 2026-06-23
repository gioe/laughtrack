"""Data model for a single event from an Elfsight Event Calendar widget."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.utilities.html.utils import HtmlUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class ElfsightEvent(ShowConvertible):
    """A single event from an Elfsight Event Calendar widget's events API.

    Elfsight is a third-party widget embedded on Squarespace/Wix/etc. venue
    sites. The events API returns a JSON array under ``payload`` with fields:
      name          ← event["name"]
      start_iso     ← event["start"]["dateTime"] (ISO8601 w/ offset) or ["date"]
      description   ← event["description"] (HTML; ticket link often embedded)
      ticket_url    ← event["buttonLink"] or first href in the description
      image_url     ← event["image"]["url"]

    The widget calendar is commonly backed by a Google Calendar, so events
    carry no per-event ticket field; ``ticket_url`` falls back to the embedded
    description link, then to the venue's own calendar page (``page_url``),
    which also serves as ``show_page_url``.
    """

    name: str
    start_iso: str          # "2026-06-24T18:00:00-07:00" or "2026-06-24"
    page_url: str           # venue calendar page, e.g. https://venue.com/event-calendar
    description_html: str = ""
    ticket_url: str = ""
    image_url: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert an ElfsightEvent to a Show domain object."""
        try:
            start_date = datetime.fromisoformat(self.start_iso)
        except (ValueError, TypeError):
            return None

        # All-day events (start.date) parse to a naive midnight datetime; pin
        # them to the club timezone so downstream tz handling matches dated shows.
        if start_date.tzinfo is None:
            try:
                start_date = start_date.replace(tzinfo=ZoneInfo(club.timezone or "UTC"))
            except Exception:
                pass

        show_page_url = url or self.page_url
        ticket_purchase_url = self.ticket_url or show_page_url
        description = HtmlUtils.strip_tags(self.description_html) or None
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_purchase_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=description,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
