"""Data models for the Nantucket Dreamland Live Comedy scraper.

Dreamland (nantucketdreamland.org) is a WordPress film/arts center whose comedy
programming lives under a dedicated "Live Comedy" taxonomy archive:

  https://www.nantucketdreamland.org/event-type/live-comedy

Each event card on that archive carries a show title, a detail-page link
(/events/<slug>), and an AgileTicketing "Next Show" link whose text holds the
date/time/room (e.g. "Jul 3, 2026 at 8:00 pm in the Main Theater") and whose
href is the ticket-purchase URL. The archive is already comedy-only (the venue's
own category), so no comedy_filter is needed. Per-event pages carry no schema.org
Event JSON-LD, so the generic json_ld scraper does not fit.
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
class DreamlandEvent(ShowConvertible):
    """A single Dreamland Live Comedy event. ``date`` is tz-aware (venue tz)."""

    title: str
    date: datetime
    show_page_url: str
    ticket_url: str = ""
    room: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        purchase_url = url or self.ticket_url or self.show_page_url
        if not purchase_url:
            return None
        tickets = [ShowFactoryUtils.create_fallback_ticket(purchase_url)]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=self.date,
            show_page_url=self.show_page_url or purchase_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room=self.room or "",
            supplied_tags=["event"],
            enhanced=enhanced,
        )


@dataclass
class DreamlandPageData(EventListContainer[DreamlandEvent]):
    """Extracted events from the Dreamland Live Comedy archive."""

    event_list: List[DreamlandEvent]
