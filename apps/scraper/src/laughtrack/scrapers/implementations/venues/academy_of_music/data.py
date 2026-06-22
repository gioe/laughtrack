"""Data models for the Academy of Music (Northampton, MA) scraper.

The venue (aomtheatre.com) is a WooCommerce/Divi WordPress site that exposes its
events as a custom ``aom_event`` post type via the WordPress REST API:

  https://aomtheatre.com/wp-json/wp/v2/aom_event?per_page=100

Each record's ``content.rendered`` holds a structured ``event_info`` block
(``event_start_full`` = "Friday, October 9th, 2026 at 8:00pm", ``event_title``,
``ticket_price``) plus a ``/purchase-tickets/?eventId=<id>`` buy link. The
per-event pages carry no schema.org Event JSON-LD, so the generic json_ld
scraper does not fit — hence this venue-specific parser.
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
class AcademyOfMusicEvent(ShowConvertible):
    """A single Academy of Music event parsed from the WP REST feed.

    ``date`` is a timezone-aware datetime in the venue's local timezone.
    ``price`` is the lowest advertised ticket price, or ``None`` when unknown
    (``0.0`` only for events explicitly marked FREE).
    """

    title: str
    date: datetime
    show_page_url: str
    ticket_url: str = ""
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        purchase_url = url or self.ticket_url or self.show_page_url
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
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )


@dataclass
class AcademyOfMusicPageData(EventListContainer[AcademyOfMusicEvent]):
    """Extracted events from the Academy of Music WP REST feed."""

    event_list: List[AcademyOfMusicEvent]
