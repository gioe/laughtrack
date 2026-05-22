"""Unit tests for the Ticket dataclass and its factory helpers.

Focuses on `Ticket.from_offer`'s null-vs-zero contract (TASK-2405): an Offer
with no parseable price must produce `Ticket(price=None)` — proven-free 0 from
JSON-LD still passes through as 0.0.
"""

from laughtrack.core.entities.event.event import Offer
from laughtrack.core.entities.ticket.model import Ticket


def _offer(price) -> Offer:
    return Offer(
        url="https://example.com/event",
        price_currency="USD",
        price=price,
        availability="https://schema.org/InStock",
    )


def test_from_offer_none_price_is_unknown():
    ticket = Ticket.from_offer(_offer(None))
    assert ticket.price is None


def test_from_offer_empty_string_price_is_unknown():
    ticket = Ticket.from_offer(_offer(""))
    assert ticket.price is None


def test_from_offer_unparseable_price_is_unknown():
    ticket = Ticket.from_offer(_offer("free"))
    assert ticket.price is None


def test_from_offer_explicit_zero_string_is_free():
    # Proven-free JSON-LD Offer { price: "0" } must round-trip as 0.0, not None.
    ticket = Ticket.from_offer(_offer("0"))
    assert ticket.price == 0.0


def test_from_offer_numeric_string_preserved():
    ticket = Ticket.from_offer(_offer("25.50"))
    assert ticket.price == 25.5
