from datetime import datetime

from laughtrack.core.entities.event.event import JsonLdEvent, Offer
from laughtrack.utilities.domain.show.enhancement import ShowEnhancement


def test_schema_org_availability_url_does_not_become_ticket_type():
    offer = Offer(
        url="https://www.ticketweb.com/event/show",
        price_currency="USD",
        price="37.17",
        availability="http://schema.org/InStock",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)

    assert ticket is not None
    assert ticket.type == "General Admission"
    assert ticket.sold_out is False


def test_schema_org_sold_out_url_sets_sold_out():
    offer = Offer(
        url="https://www.ticketweb.com/event/show",
        price_currency="USD",
        price="37.17",
        availability="https://schema.org/SoldOut",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)

    assert ticket is not None
    assert ticket.type == "General Admission"
    assert ticket.sold_out is True


def test_zero_price_offer_creates_ticket():
    offer = Offer(
        url="https://www.tickettailor.com/events/westrivercomedyclub/2041184",
        price_currency="",
        price=0,
        availability="https://schema.org/InStock",
        name="General Admission",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)

    assert ticket is not None
    assert ticket.price == 0.0
    assert ticket.purchase_url == "https://www.tickettailor.com/events/westrivercomedyclub/2041184"
    assert ticket.type == "General Admission"
    assert ticket.sold_out is False


def test_empty_string_price_emits_ticket_with_none_price():
    offer = Offer(
        url="https://example.com/tix",
        price_currency="USD",
        price="",
        availability="https://schema.org/InStock",
        name="General Admission",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)

    assert ticket is not None
    assert ticket.price is None
    assert ticket.purchase_url == "https://example.com/tix"
    assert ticket.type == "General Admission"
    assert ticket.sold_out is False


def test_none_price_emits_ticket_with_none_price():
    offer = Offer(
        url="https://example.com/tix",
        price_currency="USD",
        price=None,
        availability="https://schema.org/SoldOut",
        name="VIP",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)

    assert ticket is not None
    assert ticket.price is None
    assert ticket.purchase_url == "https://example.com/tix"
    assert ticket.type == "VIP"
    assert ticket.sold_out is True


def test_unparseable_price_emits_ticket_with_none_price():
    offer = Offer(
        url="https://example.com/tix",
        price_currency="USD",
        price="see venue",
        availability="https://schema.org/InStock",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)

    assert ticket is not None
    assert ticket.price is None
    assert ticket.purchase_url == "https://example.com/tix"
    assert ticket.sold_out is False


def test_urless_offer_uses_fallback_url():
    # An AggregateOffer summarizing a price range carries no url of its own.
    offer = Offer(
        url="",
        price_currency="USD",
        price="",
        availability="https://schema.org/InStock",
    )

    ticket = ShowEnhancement._create_enhanced_ticket_from_offer(
        offer, fallback_url="https://events.humanitix.com/some-show"
    )

    assert ticket is not None
    assert ticket.purchase_url == "https://events.humanitix.com/some-show"


def test_aggregate_offer_without_url_falls_back_to_event_url():
    # Humanitix collections pages lead with a urless AggregateOffer followed by
    # concrete Offers. Without a fallback, the urless ticket has an empty
    # purchase_url and the whole show is dropped by validation.
    event = JsonLdEvent(
        name="Safe Words Queer Comedy Showcase",
        start_date=datetime(2099, 1, 1, 19, 0, 0),
        location=None,
        offers=[
            Offer(url="", price_currency="USD", price="", availability="https://schema.org/InStock"),
            Offer(
                url="https://events.humanitix.com/safe-words/tickets",
                price_currency="USD",
                price=0,
                availability="https://schema.org/InStock",
                name="General Admission",
            ),
        ],
        url="https://events.humanitix.com/safe-words",
        description="",
    )

    tickets = ShowEnhancement.enhance_tickets_from_event(event)

    assert len(tickets) == 2
    assert all(t.purchase_url for t in tickets)
    assert tickets[0].purchase_url == "https://events.humanitix.com/safe-words"
    assert tickets[1].purchase_url == "https://events.humanitix.com/safe-words/tickets"
