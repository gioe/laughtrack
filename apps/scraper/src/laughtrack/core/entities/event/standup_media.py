"""Data model for a single show fetched from the StandUp Media reservation API.

StandUp Media (apireservation.standupmedia.com) is the self-hosted ASP.NET
ticketing platform that powers the Funny Bone national comedy-club chain (and
other Levity Entertainment venues). Each venue site (e.g. stlouisfunnybone.com)
exposes the same per-location JSON contract::

    GET https://apireservation.standupmedia.com/api/Show/GetAllShows/{location_id}/false/{dbname}
    -> [ {"ShowID": ..., "ShowDt": ..., "ShowTm": ..., "ComicName": ...,
          "ShowPrice": ..., "soldout": 0, "isprivate": false, ...}, ... ]

One record is returned per price section, so a single showtime can appear as
several rows sharing one ``ShowID``; the extractor de-duplicates by ``ShowID``.
``ShowTm`` is a naive local datetime string (no offset) localized with the club
timezone.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class StandUpMediaEvent(ShowConvertible):
    """A single comedy show fetched from the StandUp Media reservation API.

    ``start_str`` is the naive local ``ShowTm`` ISO string (e.g.
    ``"2026-06-26T19:00:00"``) localized with the club timezone. ``price`` is
    the cheapest section price for the showtime (``None`` when unknown).
    ``purchase_url`` is the venue's ticketing page, used as the access record
    for every show.
    """

    show_id: str
    name: str
    start_str: str            # naive local ISO datetime from ShowTm
    purchase_url: str
    price: Optional[float] = None
    sold_out: bool = False
    timezone_name: str = "America/Chicago"

    def _resolve_date(self) -> Optional[datetime]:
        """Localize the naive ShowTm ISO string with the club timezone."""
        if not self.start_str:
            return None
        try:
            return DateTimeUtils.parse_datetime_with_timezone(
                self.start_str, self.timezone_name
            )
        except (ValueError, TypeError):
            return None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a StandUpMediaEvent to a Show domain object."""
        start_date = self._resolve_date()
        if start_date is None:
            return None

        page_url = url or self.purchase_url
        tickets = []
        if page_url:
            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(
                    page_url, price=self.price, sold_out=self.sold_out
                )
            )

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
