"""Data model for a single event from Ice House Comedy Club's Tockify calendar API."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


def _normalize_showclix_url(url: str) -> str:
    """Normalize embed.showclix.com ticket URLs to www.showclix.com URLs.

    Tockify's customButtonLink uses embed.showclix.com for iframe embeds.
    The publicly linkable ticket URL is on www.showclix.com.
    """
    return url.replace("https://embed.showclix.com/", "https://www.showclix.com/")


@dataclass
class IceHouseEvent(ShowConvertible):
    """
    Data model for a single event from Ice House Comedy Club's Tockify calendar.

    The Tockify API endpoint is:
      https://tockify.com/api/ngevent?calname=theicehouse&max=200&startms={now_ms}

    Fields map directly from the API response:
      uid        ← eid.uid (unique event identifier)
      title      ← content.summary.text
      start_ms   ← when.start.millis (Unix milliseconds)
      ticket_url ← content.customButtonLink (ShowClix embed URL, normalized to www)
      timezone   ← when.start.tzid
    """

    uid: str
    title: str
    start_ms: int          # Unix milliseconds
    ticket_url: str        # ShowClix URL (may need embed → www normalization)
    timezone: str = "America/Los_Angeles"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert an IceHouseEvent to a Show domain object."""
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.timezone or club.timezone or "America/Los_Angeles")
            start_date = datetime.fromtimestamp(self.start_ms / 1000, tz=timezone.utc).astimezone(tz)
        except Exception:
            return None

        ticket_url = _normalize_showclix_url(url or self.ticket_url)
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
