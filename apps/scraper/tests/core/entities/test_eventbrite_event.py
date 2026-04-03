import pytest

from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.models.api.eventbrite import EventbriteTicket
from laughtrack.core.entities.ticket.model import Ticket


def make_club() -> Club:
    return Club(
        id=1,
        name="Eventbrite Venue",
        address="",
        website="https://example.com",
        scraping_url="example.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def test_to_show_with_performers_and_ticket_offers_parses_prices_and_sold_out():
    ev = EventbriteEvent(
        name="Headliner Night",
        event_url="https://eventbrite.com/e/123",
        start_date="2025-08-30T20:00:00Z",
        description="Great show",
        performers=["Headliner A", "Opener B"],
        ticket_offers=[
            EventbriteTicket(price="$20.00", price_currency="USD", url="https://buy/ga", name="GA", availability="InStock"),
            EventbriteTicket(price="25", price_currency="USD", url="https://buy/vip", name="VIP", availability="OutOfStock"),
        ],
    )

    show = ev.to_show(make_club(), enhanced=False)

    assert show is not None
    assert show.name == "Headliner Night"
    assert show.date.tzinfo is not None  # timezone applied
    assert len(show.lineup) == 2

    # Tickets converted
    assert len(show.tickets) == 2
    t1, t2 = show.tickets
    assert isinstance(t1, Ticket) and isinstance(t2, Ticket)
    assert t1.price == 20.0 and t1.purchase_url == "https://buy/ga" and t1.type == "GA" and (t1.sold_out is False)
    assert t2.price == 25.0 and t2.purchase_url == "https://buy/vip" and t2.type == "VIP" and (t2.sold_out is True)


def test_to_show_extracts_lineup_from_title_when_no_performers():
    ev = EventbriteEvent(
        name="Alice & Bob",
        event_url="https://event/abc",
        start_date="2025-09-01T00:00:00Z",
        performers=None,
        ticket_offers=[],
    )

    show = ev.to_show(make_club(), enhanced=False)
    assert show is not None
    names = [c.name for c in (show.lineup or [])]
    assert names == ["Alice", "Bob"]


def test_to_show_returns_none_when_no_date():
    ev = EventbriteEvent(
        name="No Date Event",
        event_url="https://event/nodate",
        start_date="",
    )
    assert ev.to_show(make_club(), enhanced=False) is None


def test_to_show_returns_none_when_date_unparsable():
    ev = EventbriteEvent(
        name="Bad Date Event",
        event_url="https://event/baddate",
        start_date="2025-99-99T25:61:00Z",
    )
    assert ev.to_show(make_club(), enhanced=False) is None


def test_to_show_creates_default_ticket_when_no_offers():
    ev = EventbriteEvent(
        name="Basic Show",
        event_url="https://event/basic",
        start_date="2025-10-10T19:00:00Z",
        ticket_offers=None,
    )

    show = ev.to_show(make_club(), enhanced=False)
    assert show is not None
    assert len(show.tickets) == 1
    t = show.tickets[0]
    assert t.price == 0.0
    assert t.purchase_url == "https://event/basic"
    assert t.type == "General Admission"


def test_to_show_skips_music_category_events():
    """Events with category_id=103 (Music) and no comedy subcategory are filtered out."""
    ev = EventbriteEvent(
        name="Triplet Threat with DJ Mariko",
        event_url="https://eventbrite.com/e/456",
        start_date="2099-01-01T22:00:00Z",
        category_id="103",
        subcategory_id=None,
    )
    assert ev.to_show(make_club(), enhanced=False) is None


def test_to_show_skips_music_category_with_music_subcategory():
    """Events with category_id=103 and a non-comedy subcategory (e.g., 3001) are filtered out."""
    ev = EventbriteEvent(
        name="Young Adult Friction: indie dance party",
        event_url="https://eventbrite.com/e/457",
        start_date="2099-01-01T21:00:00Z",
        category_id="103",
        subcategory_id="3001",
    )
    assert ev.to_show(make_club(), enhanced=False) is None


def test_to_show_allows_music_category_with_comedy_subcategory_103003():
    """Events with category_id=103 but subcategory_id=103003 (comedy in the search API) are kept."""
    ev = EventbriteEvent(
        name="Stand-Up Night",
        event_url="https://eventbrite.com/e/458",
        start_date="2099-01-01T19:00:00Z",
        category_id="103",
        subcategory_id="103003",
    )
    assert ev.to_show(make_club(), enhanced=False) is not None


def test_to_show_includes_comedy_category_events():
    """Events with category_id=105 (Performing & Visual Arts) are not filtered — comedy lives here."""
    ev = EventbriteEvent(
        name="Whiplash",
        event_url="https://eventbrite.com/e/789",
        start_date="2099-01-01T19:00:00Z",
        category_id="105",
    )
    assert ev.to_show(make_club(), enhanced=False) is not None


def test_to_show_includes_events_with_no_category():
    """Events with no category_id set are not filtered out."""
    ev = EventbriteEvent(
        name="Open Mic Night",
        event_url="https://eventbrite.com/e/000",
        start_date="2099-01-01T20:00:00Z",
        category_id=None,
    )
    assert ev.to_show(make_club(), enhanced=False) is not None
