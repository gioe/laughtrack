from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from psycopg2.extras import DictRow

from laughtrack.foundation.models.price_range import PriceRange
from laughtrack.foundation.protocols.database_entity import DatabaseEntity

if TYPE_CHECKING:
    # Only imported for type checking to avoid circular imports at runtime
    from laughtrack.core.entities.event.event import Offer


@dataclass
class Ticket(DatabaseEntity):
    """Data model for a ticket to a show."""

    price: Optional[float]
    purchase_url: str
    sold_out: bool = False
    type: str = "General Admission"
    show_id: Optional[int] = None

    @property
    def price_tag(self) -> Optional[int]:
        """Get the price range tag ID for this ticket."""
        try:
            price = float(self.price)

            if price <= 0:
                return PriceRange.FREE.value
            elif price <= 20:
                return PriceRange.LOW.value
            elif price <= 50:
                return PriceRange.MEDIUM.value
            elif price <= 100:
                return PriceRange.HIGH.value
            else:
                return PriceRange.PREMIUM.value

        except (ValueError, TypeError):
            return None

    @classmethod
    def from_db_row(cls, row: DictRow) -> "Ticket":
        """Create Ticket entity from database row."""
        return cls(
            price=float(row["price"]) if row["price"] is not None else None,
            purchase_url=row["purchase_url"],
            sold_out=bool(row.get("sold_out", False)),
            type=row.get("type", "General Admission"),
            show_id=row.get("show_id"),
        )

    @classmethod
    def from_offer(cls, offer: "Offer") -> "Ticket":
        """Create Ticket entity from an offer object.

        Args:
            offer: An Offer object with price, url, availability, and price_currency attributes

        Returns:
            Ticket: A new Ticket instance created from the offer
        """
        return cls(
            price=float(offer.price) if offer.price else 0.0,
            purchase_url=offer.url,
            sold_out=offer.availability == "SoldOut",
            type=offer.price_currency or "General Admission",
        )

    @classmethod
    def key_from_db_row(cls, row: DictRow) -> tuple:
        """Create a unique key from a database row."""
        return (row.get("show_id"), row.get("type", "General Admission"))

    def to_tuple(self) -> tuple:
        """Transform Ticket entity to database tuple."""
        return (
            self.show_id,
            self.purchase_url,
            self.price,
            self.sold_out,
            self.type,
        )

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the Ticket entity."""
        return (self.show_id, self.type)
