"""
Data model for a single event from an AXS-skinned venue homepage.

Many AXS/AEG venues run a stock venue website (royalSlider event cards) whose
homepage lists every upcoming show with a name, a date, the venue's own detail
URL, and an AXS ticket link (``axs.com/events/<id>/...?skin=<venue>``). The
``axs.com`` detail pages are DataDome-protected, but the venue homepage is plain
server-rendered HTML, so it is the scrapable seam.

The homepage carries the date but **no show time**, so ``to_show`` combines the
parsed date with a configurable default show time (``default_show_time`` on the
scraping source, default 19:00) localized to the club timezone.
"""

import pytz

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible

# Homepage date format, e.g. "Tue, Jun 16, 2026".
_AXS_DATE_FORMAT = "%a, %b %d, %Y"
_DEFAULT_SHOW_TIME = "19:00"


def _parse_default_time(raw: Optional[str]) -> time:
    """Parse an ``HH:MM`` default show time, falling back to 19:00."""
    try:
        hh, mm = (raw or _DEFAULT_SHOW_TIME).split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return time(19, 0)


@dataclass
class AXSEvent(ShowConvertible):
    """A single event scraped from an AXS-skinned venue homepage."""

    title: str            # e.g. "Ilana Glazer Live!"
    date_str: str         # e.g. "Tue, Jun 16, 2026" (date only — no time)
    show_page_url: str    # the venue's own detail page (drives traffic to venue)
    ticket_url: Optional[str] = None  # the axs.com ticket URL

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object, or None if required fields are
        missing or the show date is in the past."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.date_str or not self.show_page_url:
            return None

        try:
            date_only = datetime.strptime(self.date_str.strip(), _AXS_DATE_FORMAT).date()
        except ValueError:
            return None

        default_time = _parse_default_time(club.metadata_value("default_show_time"))
        naive = datetime.combine(date_only, default_time)
        start_dt = pytz.timezone(club.timezone or "America/New_York").localize(naive)

        if start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        purchase_url = self.ticket_url or show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
