"""Grove34 ticket model for Grove34-specific ticket handling."""

from typing import List, Optional

from laughtrack.core.entities.ticket.model import Ticket


class Grove34Ticket:
    """Helpers to translate Grove34 warmup data into Ticket entities."""

    @staticmethod
    def create_tickets_from_grove34_event(
        *,
        lowest_price: Optional[float],
        highest_price: Optional[float],
        purchase_url: str,
        sold_out: bool = False,
    ) -> List[Ticket]:
        """Create Ticket list from Grove34 warmup event data.

        Prefers the lowest price when available and falls back to highest price.
        If neither price is available, returns an empty list.

        Args:
            lowest_price: Parsed lowest ticket price (float) or None
            highest_price: Parsed highest ticket price (float) or None
            purchase_url: URL to the event details or checkout page
            sold_out: Whether the event is sold out

        Returns:
            List[Ticket]: Typically a single "General Admission" ticket.
        """
        # Choose a usable price, preferring the lowest if present
        price: Optional[float] = lowest_price if lowest_price is not None else highest_price

        # If we still don't have a price, we can't construct a meaningful ticket
        if price is None:
            return []

        # Normalize price to be non-negative
        try:
            price = float(price)
        except (TypeError, ValueError):
            return []
        price = max(0.0, price)

        ticket = Ticket(
            price=price,
            purchase_url=purchase_url or "",
            sold_out=bool(sold_out),
            type="General Admission",
        )

        return [ticket]