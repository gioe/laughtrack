"""
Unit tests for StandupNY ticket extraction — specifically the empty/None price coercion fix.
"""

from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.standup_ny.transformer import StandupNYEventTransformer


def _make_club() -> Club:
    return Club(
        id=1,
        name="StandUp NY",
        address="",
        zip_code="10023",
        website="https://standupny.com",
        timezone="America/New_York",
        scraping_url="https://standupny.com/events",
        popularity=0,
        phone_number="",
        visible=True,
    )


def _make_event(**kwargs) -> StandupNYEvent:
    defaults = dict(id="1", name="Test Show", date="2026-03-10", start_time="20:00:00", ticket_url="https://standupny.com/tickets/1")
    defaults.update(kwargs)
    return StandupNYEvent(**defaults)


def _transformer() -> StandupNYEventTransformer:
    return StandupNYEventTransformer(club=_make_club())


class TestVenuePilotTicketPriceCoercion:
    def test_empty_string_price_coerces_to_zero(self):
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": ""}, "soldOut": False, "type": "General Admission"},
        ])
        show = _transformer().transform_to_show(event)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 0.0

    def test_none_price_coerces_to_zero(self):
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": None}, "soldOut": False, "type": "General Admission"},
        ])
        show = _transformer().transform_to_show(event)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 0.0

    def test_valid_price_preserved(self):
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": "25.00"}, "soldOut": False, "type": "General Admission"},
        ])
        show = _transformer().transform_to_show(event)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 25.0
