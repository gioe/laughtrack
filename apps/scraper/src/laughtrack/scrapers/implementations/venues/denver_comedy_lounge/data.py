"""Data models for the Denver Comedy Lounge scraper."""

from dataclasses import dataclass
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# Naive-local datetime format the extractor produces from each show slug.
_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
# Fallback timezone for the venue (RiNo Arts District, Denver, CO) when the
# club row has no timezone set.
_DEFAULT_TIMEZONE = "America/Denver"


@dataclass
class DenverComedyLoungeShow:
    """A single Denver Comedy Lounge show parsed from the /shows ItemList.

    The venue runs a custom Next.js (Vercel + Sanity) site that sells each show
    via on-site Stripe checkout, so there is no ticketing-platform feed to read.
    The ``/shows`` page server-renders a schema.org ``ItemList`` of upcoming
    shows where each item exposes a name and a detail URL whose slug encodes the
    weekday, start time, and date (e.g. ``/shows/friday-7pm-2026-06-26``). The
    extractor parses that slug into ``datetime_str`` (naive local) and keeps the
    detail URL as ``show_page_url``.
    """

    title: str
    datetime_str: str
    show_page_url: str

    def to_show(
        self,
        club: Club,
        enhanced: bool = True,
        url: Optional[str] = None,
    ) -> Optional[Show]:
        """Convert to a Show entity, or None when the datetime can't be parsed."""
        date = ShowFactoryUtils.safe_parse_datetime_string(
            self.datetime_str,
            _DATETIME_FORMAT,
            timezone_name=club.timezone or _DEFAULT_TIMEZONE,
        )
        if not date:
            Logger.warn(
                f"Denver Comedy Lounge ({club.name}): could not parse datetime "
                f"'{self.datetime_str}' for show '{self.title}'"
            )
            return None

        # On-site Stripe checkout exposes no public price in the page data, so
        # every show carries one priceless fallback ticket pointing at its own
        # detail page (preserving the one-ticket-per-show invariant).
        tickets: List[Ticket] = [
            ShowFactoryUtils.create_fallback_ticket(purchase_url=self.show_page_url)
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=date,
            show_page_url=self.show_page_url,
            tickets=tickets,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )


@dataclass
class DenverComedyLoungePageData(EventListContainer[DenverComedyLoungeShow]):
    """Container for DenverComedyLoungeShow objects (5-component pattern)."""

    event_list: List[DenverComedyLoungeShow]
