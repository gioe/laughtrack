"""Gotham Comedy Club live events feed data models.

The venue rebuilt its site on Webflow; events are served by a Cloudflare
Worker proxying the Webflow CMS collection:

    GET https://square-mountain-7159.alex-cdc.workers.dev/items?limit=<N>&offset=<M>

Response shape:
    {
        "items": [
            {
                "id": "<webflow item id>",
                "isArchived": false,
                "isDraft": false,
                "fieldData": {
                    "event-title": "The Gotham All-Stars",
                    "event-times": "2026-06-20T20:00:00-04:00",
                    "event-id": "10378853",          # Showclix event id
                    "event-url-slug": "the-gotham-all-stars2526rbueuau",
                    "event-category": "Stand-up Comedy Shows",
                    ...
                }
            },
            ...
        ],
        "pagination": {"limit": 100, "offset": 0, "total": 193}
    }

Each showtime is its own item (recurring shows share a ``parent-id`` but
carry distinct ``event-id`` values), so no flattening step is needed.
"""

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.core.clients.showclix.models import ShowclixEventData
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# Gotham is in Chelsea, NYC. event-times values carry their own UTC offset
# (e.g. "2026-06-20T20:00:00-04:00"); this is only the fallback for the
# unexpected case of a naive timestamp.
_GOTHAM_TIMEZONE = "America/New_York"


@dataclass
class GothamFeedEvent(ShowConvertible):
    """A single showtime from the Gotham live events feed.

    Field mapping from a feed item:
        id        ← item["id"] (Webflow item id)
        name      ← fieldData["event-title"]
        start     ← fieldData["event-times"] (ISO 8601 with UTC offset)
        event_id  ← fieldData["event-id"] (Showclix event id — used directly
                    for ticket enrichment, no HTML discovery step needed)
        slug      ← fieldData["event-url-slug"] (Showclix event page slug)
        category  ← fieldData["event-category"]
    """

    id: str
    name: str
    start: str
    event_id: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[str] = None

    # Enrichment fields populated from the Showclix API
    price: Optional[float] = None
    sold_out: bool = False
    inventory: Optional[int] = None

    # Raw feed item for reference
    _raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_feed_item(cls, item: Dict[str, Any]) -> Optional["GothamFeedEvent"]:
        """Build a GothamFeedEvent from a raw feed item dict.

        Returns None for items that should never become shows: archived or
        draft items, and items missing a title or start time.
        """
        if not isinstance(item, dict):
            return None
        if item.get("isArchived") or item.get("isDraft"):
            return None

        field_data = item.get("fieldData")
        if not isinstance(field_data, dict):
            return None

        name = (field_data.get("event-title") or field_data.get("name") or "").strip()
        start = field_data.get("event-times") or ""
        if not name or not start:
            return None

        event_id = field_data.get("event-id")
        return cls(
            id=item.get("id") or "unknown",
            name=name,
            start=start,
            event_id=str(event_id) if event_id else None,
            slug=field_data.get("event-url-slug") or None,
            category=field_data.get("event-category") or None,
            _raw_data=item,
        )

    @property
    def start_datetime(self) -> Optional[datetime]:
        """Parse the start time, preserving the feed-supplied UTC offset.

        Falls back to localizing in America/New_York for the unexpected case
        of a naive timestamp. Returns None when the value is unparseable.
        """
        try:
            return DateTimeUtils.parse_datetime_with_timezone(self.start, _GOTHAM_TIMEZONE)
        except (TypeError, ValueError):
            return None

    @property
    def show_page_url(self) -> str:
        """Showclix event page URL for this showtime."""
        if self.slug:
            return f"https://www.showclix.com/event/{self.slug}"
        # Fallback when the feed item carries no slug — point at the venue's
        # own events calendar so the ticket link is still actionable.
        return "https://www.gothamcomedyclub.com/events"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this feed event into a Show domain object.

        Returns None if required fields are missing or the start time is
        unparseable.
        """
        try:
            if not self.name:
                Logger.warn("Gotham feed event missing name field")
                return None

            date = self.start_datetime
            if date is None:
                Logger.warn(f"Failed to parse start time {self.start!r} for event {self.name}")
                return None

            show_page_url = self.show_page_url

            # Extract room information from the name
            room_patterns = {"vintage lounge": "The Vintage Lounge"}
            room = ShowFactoryUtils.extract_room_from_name(self.name, room_patterns) or "Main Room"

            # Every show emits at least one ticket (project invariant);
            # price/sold_out carry Showclix enrichment when it succeeded.
            tickets = [
                ShowFactoryUtils.create_fallback_ticket(
                    show_page_url,
                    price=self.price,
                    sold_out=self.sold_out,
                )
            ]

            description = f"Comedy show: {self.name}"

            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.name,
                club=club,
                date=date,
                show_page_url=show_page_url,
                lineup=[],  # No comedian lineup info in the feed
                tickets=tickets,
                description=description,
                room=room,
                supplied_tags=["event"],
                enhanced=False,  # Gotham events use basic processing
            )

        except Exception as e:
            Logger.error(f"Error transforming Gotham feed event: {e}")
            return None

    def enrich_with_showclix_data(self, event_data: ShowclixEventData) -> "GothamFeedEvent":
        """Return a copy of this event enriched with Showclix ticket data."""
        try:
            price: Optional[float] = None
            primary_price = event_data.get_primary_price()
            if primary_price is not None:
                try:
                    price = float(primary_price)
                except (TypeError, ValueError):
                    price = None
                else:
                    # A 0.00 ShowClix level is a hidden/comp placeholder, not
                    # proven-free — keep it price-unknown per the zero-stays-None
                    # convention (TASK-2827), mirroring the comedy_store
                    # _resolve_and_fetch_price guard (TASK-2841/TASK-2852).
                    if price <= 0:
                        price = None

            available_tickets = event_data.get_available_tickets()

            return dataclasses.replace(
                self,
                price=price,
                sold_out=event_data.is_sold_out(),
                inventory=available_tickets,
            )
        except Exception as e:
            Logger.error(f"Error enriching Gotham event {self.event_id} with Showclix data: {e}")
            return self


@dataclass
class GothamFeedPagination:
    """Pagination block of a feed response."""

    limit: int
    offset: int
    total: int

    @classmethod
    def from_dict(cls, data: Any) -> "GothamFeedPagination":
        if not isinstance(data, dict):
            data = {}

        def _as_int(value: Any, default: int = 0) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        return cls(
            limit=_as_int(data.get("limit")),
            offset=_as_int(data.get("offset")),
            total=_as_int(data.get("total")),
        )


@dataclass
class GothamFeedResponse:
    """One page of the Gotham live events feed."""

    events: List[GothamFeedEvent] = field(default_factory=list)
    pagination: GothamFeedPagination = field(
        default_factory=lambda: GothamFeedPagination(limit=0, offset=0, total=0)
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GothamFeedResponse":
        """Parse a raw feed response dict.

        Archived/draft items and items missing a title or start time are
        skipped; malformed individual items never fail the whole page.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Gotham feed response must be a dict, got {type(data).__name__}")

        items = data.get("items")
        if not isinstance(items, list):
            raise ValueError("Gotham feed response missing 'items' list")

        events = []
        for item in items:
            event = GothamFeedEvent.from_feed_item(item)
            if event is not None:
                events.append(event)

        return cls(
            events=events,
            pagination=GothamFeedPagination.from_dict(data.get("pagination")),
        )
