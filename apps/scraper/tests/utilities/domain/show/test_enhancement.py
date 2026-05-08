from laughtrack.core.entities.event.event import Offer
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
