"""Data model for one dated Ludus (ludus.com) show instance.

Ludus (formerly Tixato) embeds a box-office widget per venue subdomain. Each
comedy show's detail page lists one or more upcoming showtimes; the extractor
fans those out into one :class:`LudusEvent` per future showtime, which converts
to a Show here. The buy URL is the per-show detail page.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class LudusEvent(ShowConvertible):
    """One upcoming Ludus showtime."""

    title: str
    # Naive local datetime parsed from the detail page's showtime row.
    start: datetime
    show_url: str

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
            self.start.strftime("%Y-%m-%d %H:%M:%S"),
            club.timezone or "America/Detroit",
        )

        source_url = url or self.show_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(source_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or club.name,
            club=club,
            date=start_date,
            show_page_url=source_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )
