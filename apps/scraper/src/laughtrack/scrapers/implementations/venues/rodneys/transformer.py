"""
Rodney's Comedy Club data transformer for converting RodneyEvent objects to Show objects.
"""

from typing import List, Optional

from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class RodneyEventTransformer(DataTransformer[RodneyEvent]):
    """
    Transformer for converting RodneyEvent objects to Show objects.

    Handles events from multiple sources:
    - Direct HTML pages with JSON-LD
    - Eventbrite API responses
    - 22Rams API responses
    """

    def can_transform(self, raw_data: RodneyEvent) -> bool:
        """Check if this transformer can handle the given data."""
        return (
            isinstance(raw_data, RodneyEvent)
            and hasattr(raw_data, "title")
            and hasattr(raw_data, "date_time")
            and bool(raw_data.title)
            and raw_data.date_time is not None
        )

    def transform_to_show(self, raw_data: RodneyEvent, source_url: str = "") -> Optional[Show]:
        """
        Transform RodneyEvent to a single Show object.

        Args:
            raw_data: RodneyEvent object to transform
            source_url: URL where the data was extracted from (optional, uses raw_data.source_url)

        Returns:
            Show object, or None if transformation failed
        """
        try:
            # Use the source URL from the RodneyEvent if not provided
            show_url = source_url or raw_data.source_url

            # Ensure timezone-aware datetime
            date_str = raw_data.date_time.isoformat() if raw_data.date_time else ""
            if not date_str:
                Logger.error(f"No date available for event: {raw_data.title}")
                return None

            show_date = DateTimeUtils.parse_datetime_with_timezone(date_str, self.club.timezone)

            if not show_date:
                Logger.error(f"Failed to parse date for event: {raw_data.title}")
                return None

            # Extract lineup
            lineup = self._extract_lineup(raw_data)

            # Extract tickets
            tickets = self._extract_tickets(raw_data, show_url)

            # Create Show object
            return Show(
                name=raw_data.title,
                date=show_date,
                description=raw_data.description or "",
                show_page_url=show_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=[],
                timezone=self.club.timezone,
                club_id=self.club.id,
                room="",  # Rodney's doesn't have separate rooms
            )

        except Exception as e:
            Logger.error(
                f"Failed to transform RodneyEvent data from {source_url}: {e}: club={self.club.name} source_type={raw_data.source_type}"
            )
            return None

    def _extract_lineup(self, event: RodneyEvent) -> List[Comedian]:
        """Extract comedian lineup from RodneyEvent."""
        lineup = []

        if event.performers:
            for performer_name in event.performers:
                if performer_name and performer_name.strip():
                    comedian = Comedian(name=performer_name.strip())
                    lineup.append(comedian)

        return lineup

    def _extract_tickets(self, event: RodneyEvent, source_url: str) -> List[Ticket]:
        """Extract ticket information from RodneyEvent."""
        tickets = []

        if not event.ticket_info:
            return tickets

        ticket_info = event.ticket_info

        # Handle different ticket info structures based on source type
        if event.source_type == "html":
            purchase_url = ticket_info.get("purchase_url", source_url)
            price = ticket_info.get("price")
            sold_out = ticket_info.get("availability", "").lower() == "soldout"
            if price:
                try:
                    price_value = float(str(price).replace("$", "").replace(",", ""))
                    tickets.append(
                        Ticket(
                            price=price_value,
                            type="General Admission",
                            purchase_url=purchase_url,
                            sold_out=sold_out,
                        )
                    )
                except (ValueError, TypeError):
                    pass
            elif purchase_url:
                # No price in HTML — create a ticket with the purchase URL only
                tickets.append(
                    Ticket(
                        price=0.0,
                        type="General Admission",
                        purchase_url=purchase_url,
                        sold_out=sold_out,
                    )
                )

        return tickets
