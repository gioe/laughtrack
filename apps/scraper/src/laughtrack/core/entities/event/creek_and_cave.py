"""Data model for a single show slot from The Creek and The Cave's S3 calendar API."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


# Keywords that indicate a show/event title rather than a comedian name.
# If any word in the event name (lowercased) matches one of these, we treat the
# entire name as a show title and produce an empty lineup.
_SHOW_TITLE_KEYWORDS = frozenset({
    "mic", "open", "battle", "roast", "bingo", "therapy", "comedy",
    "show", "night", "creek", "cave", "wild", "king", "bear",
    "arms", "word", "banana", "dunk", "tank", "hood", "gone",
    "circus", "fire", "clocked", "purple", "park", "gamble", "gimmick",
    "noctis", "optimum", "featured", "main", "course",
    "freaky", "room", "absolute", "bilt", "powered", "cuff",
    "litty", "titty", "adult", "standupatodos", "lemon",
})


def _infer_comedian_name(event_name: str) -> Optional[str]:
    """Return comedian name if event_name looks like a person's name, else None.

    Rules:
    - Strip trailing " Live" / " LIVE" suffix (e.g. "Liza Treyger Live" → "Liza Treyger")
    - Require 2–4 words after stripping
    - Reject if any word matches a known show-title keyword
    """
    name = event_name.strip()
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
class CreekAndCaveEvent(ShowConvertible):
    """
    Data model for a single show slot from The Creek and The Cave (Austin, TX).

    The S3 monthly JSON is keyed by day-of-month.  Each day entry is a list of
    event dicts, and each event dict has a ``shows`` array with individual time
    slots.  One ``CreekAndCaveEvent`` is created per time slot.

    S3 endpoint pattern:
      https://creekandcaveevents.s3.amazonaws.com/events/month/YYYY-MM.json

    Field mapping from JSON:
      slug        ← event.slug
      name        ← event.name
      date_utc    ← shows[n].date   (ISO 8601 UTC, e.g. "2026-04-11T00:00:00.000Z")
      time_local  ← shows[n].time   (local time string, e.g. "7:00 pm")
      listing_url ← shows[n].listing_url  (Showclix ticket URL)
      inventory   ← shows[n].inventory   (available ticket count, optional)
    """

    slug: str
    name: str
    date_utc: str
    time_local: str
    listing_url: str
    inventory: Optional[int] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this show slot to a Show domain object."""
        try:
            dt = datetime.fromisoformat(self.date_utc.replace("Z", "+00:00"))
            tz = ZoneInfo(club.timezone or "America/Chicago")
            show_date = dt.astimezone(tz)
        except Exception as e:
            Logger.warn(f"CreekAndCaveEvent: failed to parse date '{self.date_utc}': {e}")
            return None

        ticket_url = url or self.listing_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        comedian_name = _infer_comedian_name(self.name)
        lineup = [Comedian(name=comedian_name)] if comedian_name else []

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=show_date,
            show_page_url=ticket_url,
            lineup=lineup,
            tickets=tickets,
            description=None,
            room="Main Room",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
