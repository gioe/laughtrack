import json
from pathlib import Path

from laughtrack.core.clients.eventbrite.models import EventbriteListEventsResponse
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.eventbrite import EventbriteEvent


FIXTURES = Path(__file__).parent / "fixtures"


def make_club() -> Club:
    club = Club(
        id=1,
        name="Eventbrite Venue",
        address="",
        website="https://example.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="eventbrite",
        scraper_key="eventbrite",
        source_url="https://www.eventbrite.com/e/current-paid-comedy-night-tickets-1234567890",
        external_id="1234567890",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_eventbrite_price_extraction_uses_current_ticket_availability_shape():
    payload = json.loads((FIXTURES / "current_event_with_ticket_availability.json").read_text())
    api_event = EventbriteListEventsResponse.from_dict(payload).events[0]

    event = EventbriteEvent.from_api_model(api_event)
    show = event.to_show(make_club(), enhanced=False)

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 32.0
    assert show.tickets[0].purchase_url == event.event_url
    assert show.tickets[0].sold_out is False


def test_eventbrite_unknown_paid_price_stays_null_instead_of_zero():
    event = EventbriteEvent(
        name="Paid show with no availability expansion",
        event_url="https://www.eventbrite.com/e/no-expanded-price-tickets-123",
        start_date="2026-06-02T00:00:00Z",
        ticket_offers=None,
    )

    show = event.to_show(make_club(), enhanced=False)

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price is None
