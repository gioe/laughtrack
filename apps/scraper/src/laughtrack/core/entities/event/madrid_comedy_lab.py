"""Data model for a single event from Madrid Comedy Lab's Fienta calendar."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


# Keywords that indicate a show/event title rather than a comedian name.
_SHOW_TITLE_KEYWORDS = frozenset({
    "mic", "open", "comedy", "show", "night", "showcase", "jam",
    "dark", "humour", "humor", "late", "improv", "roast", "battle",
    "workshop", "course", "class", "special", "marathon", "festival",
    "standup", "stand-up", "english", "spanish", "lab", "madrid",
})


def _infer_comedian_name(event_title: str) -> Optional[str]:
    """Return comedian name if event_title looks like a person's name, else None.

    Rules:
    - Strip common suffixes like " Live", " LIVE", " - Live"
    - Require 2-4 words
    - Reject if any word matches a known show-title keyword
    """
    name = event_title.strip()
    for suffix in (" Live", " LIVE", " - Live", " - LIVE"):
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
            break

    words = name.split()
    if not (2 <= len(words) <= 4):
        return None

    word_lower = {w.lower().rstrip(":,!") for w in words}
    if word_lower & _SHOW_TITLE_KEYWORDS:
        return None

    return name


@dataclass
class MadridComedyLabEvent(ShowConvertible):
    """Data model for a single event from Madrid Comedy Lab via Fienta API.

    Fienta organizer API endpoint:
      https://fienta.com/api/v1/public/events?organizer=24814

    Field mapping from JSON:
      event_id    <- id
      title       <- title
      starts_at   <- starts_at  (e.g. "2026-04-09 20:30:00", local Madrid time)
      ends_at     <- ends_at    (e.g. "2026-04-09 22:00:00")
      url         <- url        (Fienta ticket URL)
      sale_status <- sale_status (e.g. "onSale", "soldOut")
      description <- description (HTML string)
    """

    event_id: Optional[int]
    title: str
    starts_at: str
    ends_at: str
    url: str
    sale_status: str = ""
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this Fienta event to a Show domain object."""
        if not self.title:
            return None

        try:
            tz = ZoneInfo(club.timezone or "Europe/Madrid")
            # Fienta returns times in the organizer's local timezone (no TZ offset)
            show_date = datetime.strptime(self.starts_at, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=tz
            )
        except Exception as e:
            Logger.warn(f"MadridComedyLabEvent: failed to parse date '{self.starts_at}': {e}")
            return None

        ticket_url = url or self.url
        sold_out = self.sale_status == "soldOut"
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=sold_out)]

        comedian_name = _infer_comedian_name(self.title)
        lineup = [Comedian(name=comedian_name)] if comedian_name else []

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=ticket_url,
            lineup=lineup,
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
