"""Kenosha Comedy Club event model.

The club's public site redirects to Happenings Magazine, where upcoming club
shows are maintained as WordPress posts in category 506. The post title carries
the show name/date/time and the post URL is the stable ticket/detail link.
"""

from dataclasses import dataclass
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class KenoshaComedyClubEvent(ShowConvertible):
    """A show parsed from a Happenings Magazine WordPress post."""

    name: str
    start_date: str
    url: str
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            parsed_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.start_date, club.timezone or "America/Chicago"
            )
        except Exception:
            return None

        show_url = url or self.url
        tickets = [ShowFactoryUtils.create_fallback_ticket(show_url)] if show_url else []

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=parsed_date,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            room="",
            supplied_tags=["event"],
            description=self.description or None,
            enhanced=enhanced,
        )
