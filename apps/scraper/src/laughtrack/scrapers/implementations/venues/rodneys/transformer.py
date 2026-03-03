"""
Rodney's Comedy Club data transformer for converting RodneyEvent objects to Show objects.
"""

from typing import List

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

    def transform_to_shows(self, raw_data: RodneyEvent, source_url: str = "") -> List[Show]:
        """
        Transform RodneyEvent to Show objects.

        Args:
            raw_data: RodneyEvent object to transform
            source_url: URL where the data was extracted from (optional, uses raw_data.source_url)

        Returns:
            List containing single Show object, or empty list if transformation failed
        """
        try:
            # Use the source URL from the RodneyEvent if not provided
            show_url = source_url or raw_data.source_url

            # Ensure timezone-aware datetime
            date_str = raw_data.date_time.isoformat() if raw_data.date_time else ""
            if not date_str:
                Logger.error(f"No date available for event: {raw_data.title}")
                return []

            show_date = DateTimeUtils.parse_datetime_with_timezone(date_str, self.club.timezone)

            if not show_date:
                Logger.error(f"Failed to parse date for event: {raw_data.title}")
                return []

            # Extract lineup
            lineup = self._extract_lineup(raw_data)

            # Extract tickets
            tickets = self._extract_tickets(raw_data, show_url)

            # Create Show object
            show = Show(
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

            return [show]

        except Exception as e:
            Logger.error(
                f"Failed to transform RodneyEvent data from {source_url}: {e}",
                {"club": self.club.name, "source_type": raw_data.source_type},
            )
            return []

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
            # JSON-LD tickets
            price = ticket_info.get("price")
            if price:
                try:
                    # Clean up price string and convert to float
                    price_value = float(str(price).replace("$", "").replace(",", ""))
                    sold_out = ticket_info.get("availability", "").lower() == "soldout"
                    tickets.append(
                        Ticket(
                            price=price_value,
                            type="General Admission",
                            purchase_url=ticket_info.get("purchase_url", source_url),
                            sold_out=sold_out,
                        )
                    )
                except (ValueError, TypeError):
                    pass

        elif event.source_type in ["eventbrite", "22rams"]:
            # API-based tickets with min/max pricing
            min_price = ticket_info.get("min_price")
            max_price = ticket_info.get("max_price")
            purchase_url = ticket_info.get("purchase_url", source_url)

            if min_price is not None:
                tickets.append(
                    Ticket(price=float(min_price), type="Starting at", purchase_url=purchase_url, sold_out=False)
                )

            if max_price is not None and max_price != min_price:
                tickets.append(Ticket(price=float(max_price), type="Up to", purchase_url=purchase_url, sold_out=False))

        return tickets
