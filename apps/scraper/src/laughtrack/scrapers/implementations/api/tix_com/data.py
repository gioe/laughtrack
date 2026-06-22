"""Data models for the Tix.com (tix.com) ticketing-platform scraper.

Tix.com venues expose their on-sale events through an anonymous JSON endpoint
keyed by organization id:

  https://www.tix.com/api_ots/onlinesales/events/organization/<org_id>

The response is ``{payload: {groupedEvents: [[event, ...], ...]}}`` where each
event carries ``EventId``, ``ProductionName``, ``EventDate`` (naive local ISO),
``MinPrice``/``MaxPrice``, ``Category``/``SubCategory``, and venue fields. The
public ticket page for an event is
``https://www.tix.com/ticket-sales/<slug>/<org_id>/event/<EventId>``.

Mixed-use Tix.com venues (community theaters that run a recurring comedy series
among musicals/plays) opt into comedy isolation via
``scraping_sources.metadata.comedy_filter``.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class TixComEvent(ShowConvertible):
    """A single Tix.com event. ``date`` is tz-aware in the venue's timezone."""

    event_id: int
    title: str
    date: datetime
    show_page_url: str
    price: Optional[float] = None
    description: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        purchase_url = url or self.show_page_url
        if not purchase_url:
            return None
        tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url, price=self.price)]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=self.date,
            show_page_url=self.show_page_url or purchase_url,
            lineup=[],
            tickets=tickets,
            description=self.description,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )


@dataclass
class TixComPageData(EventListContainer[TixComEvent]):
    """Extracted events from a Tix.com organization feed."""

    event_list: List[TixComEvent]
