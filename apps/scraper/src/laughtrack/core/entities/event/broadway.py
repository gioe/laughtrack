from dataclasses import dataclass
from typing import Any, List, Optional

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.utilities.coercion import CoercionUtils as C


@dataclass
class BroadwayEvent(ShowConvertible):
    """
    Data model representing a single event from Broadway Comedy Club's API.

    This corresponds to the JSON structure returned by their event endpoint.
    """

    id: str
    eventDate: str
    additionalInformation: str
    mainArtist: List[str]
    additionalArtists: List[str]
    venue: str
    image: str
    isTesseraProduct: bool
    externalLink: str
    externalLinkButtonText: str
    doors: str
    buyNowButtonText: str
    tags: List[str]
    ages: str
    room: str = ""

    # Optional fields for enrichment
    _ticket_data: Optional[Any] = None  # Ticket data from Tessera API (object with to_ticket())
    show_page_url: str = ""  # Enriched from card anchors on listing pages

    @classmethod
    def from_dict(cls, data: dict) -> "BroadwayEvent":
        """Create a BroadwayEvent from a dictionary.

        This normalizes list-like fields and applies safe defaults when keys are missing.
        """
        return cls(
            id=C.str_or_default(data.get("id")),
            eventDate=C.str_or_default(data.get("eventDate")),
            additionalInformation=C.str_or_default(data.get("additionalInformation")),
            mainArtist=C.to_str_list(data.get("mainArtist", [])),
            additionalArtists=C.to_str_list(data.get("additionalArtists", [])),
            venue=C.str_or_default(data.get("venue")),
            image=C.str_or_default(data.get("image")),
            isTesseraProduct=C.to_bool(data.get("isTesseraProduct"), False),
            externalLink=C.str_or_default(data.get("externalLink")),
            externalLinkButtonText=C.str_or_default(data.get("externalLinkButtonText")),
            doors=C.str_or_default(data.get("doors")),
            buyNowButtonText=C.str_or_default(data.get("buyNowButtonText")),
            tags=C.to_str_list(data.get("tags", [])),
            ages=C.str_or_default(data.get("ages")),
            room=C.str_or_default(data.get("room")),
            show_page_url=C.str_or_default(data.get("show_page_url")),
        )

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        # Local import to avoid package-level circular imports during lightweight uses (e.g., from_dict tests)
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        # Parse event date (required)
        start_date = None
        if self.eventDate:
            start_date = ShowFactoryUtils.safe_parse_datetime_string(
                self.eventDate, "%m/%d/%Y %I:%M %p", "America/New_York"
            )

        if not start_date:
            raise ValueError("No valid start_date found for Broadway event")

        # Create lineup from main and additional artists
        lineup = []
        if self.mainArtist:
            lineup.extend(ShowFactoryUtils.create_lineup_from_performers(self.mainArtist))
        if self.additionalArtists:
            lineup.extend(ShowFactoryUtils.create_lineup_from_performers(self.additionalArtists))

        # Create tickets - use Tessera data if available, otherwise fallback
        tickets = []
        if self._ticket_data:
            # Use enriched ticket data from Tessera API
            try:
                # _ticket_data may be a single adapter or a list from the client
                if isinstance(self._ticket_data, list):
                    # Choose the first available adapter that can convert
                    for t in self._ticket_data:
                        if hasattr(t, "to_ticket") and callable(getattr(t, "to_ticket")):
                            tickets.append(t.to_ticket())
                            break
                elif hasattr(self._ticket_data, "to_ticket") and callable(getattr(self._ticket_data, "to_ticket")):
                    tickets.append(self._ticket_data.to_ticket())
            except Exception:
                # Fall through to externalLink fallback if present
                pass

        effective_url = self.show_page_url or self.externalLink
        if not tickets and effective_url:
            # Fallback to basic ticket if no Tessera data
            tickets.append(ShowFactoryUtils.create_fallback_ticket(effective_url))

        # Build description from available parts
        description_parts = [
            self.additionalInformation,
            f"Doors: {self.doors}" if self.doors else None,
            f"Ages: {self.ages}" if self.ages else None,
        ]
        description = ShowFactoryUtils.build_description_from_parts(description_parts)

        # Event name from main artist or default
        name = self.mainArtist[0] if self.mainArtist else "Comedy Show"

        # Create standardized show
        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=effective_url or "",
            lineup=lineup,
            tickets=tickets,
            description=description,
            room=(self.room or self.venue or ""),
            supplied_tags=["event"],
            enhanced=enhanced,
        )
