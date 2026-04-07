"""
Unit tests for FlappersEvent.to_show() — conversion from scraped event to Show model.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.flappers import FlappersEvent, FlappersTicketTier

TZ = "America/Los_Angeles"


def _club() -> Club:
    return Club(
        id=42,
        name="Flappers Comedy Club",
        address="102 E Magnolia Blvd",
        website="https://www.flapperscomedy.com",
        scraping_url="https://www.flapperscomedy.com/site/shows.php",
        popularity=0,
        zip_code="91502",
        phone_number="",
        visible=True,
        timezone=TZ,
    )


def _event(**overrides) -> FlappersEvent:
    defaults = dict(
        title="Friday Night Headliner",
        event_id="5678",
        year=2099,
        month=6,
        day=15,
        time_str="8:00 PM",
        timezone=TZ,
        room="Main Room",
    )
    defaults.update(overrides)
    return FlappersEvent(**defaults)


# ---------------------------------------------------------------------------
# Basic to_show() conversion
# ---------------------------------------------------------------------------


class TestToShowBasic:
    def test_returns_show_with_correct_name(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.name == "Friday Night Headliner"

    def test_correct_club_id(self):
        show = _event().to_show(_club())
        assert show.club_id == 42

    def test_correct_date_components(self):
        show = _event(time_str="7:30 PM").to_show(_club())
        assert show is not None
        assert show.date.year == 2099
        assert show.date.month == 6
        assert show.date.day == 15
        assert show.date.hour == 19
        assert show.date.minute == 30

    def test_noon_time(self):
        show = _event(time_str="12:00 PM").to_show(_club())
        assert show.date.hour == 12
        assert show.date.minute == 0

    def test_midnight_time(self):
        show = _event(time_str="12:00 AM").to_show(_club())
        assert show.date.hour == 0

    def test_show_page_url_uses_event_id(self):
        show = _event(event_id="9999").to_show(_club())
        assert "event_id=9999" in show.show_page_url

    def test_custom_url_override(self):
        show = _event().to_show(_club(), url="https://custom.com/tickets")
        assert show.show_page_url == "https://custom.com/tickets"

    def test_room_passed_through(self):
        show = _event(room="Yoo Hoo Room").to_show(_club())
        assert show.room == "Yoo Hoo Room"

    def test_description_passed_through(self):
        show = _event(description="Great show tonight").to_show(_club())
        assert show.description == "Great show tonight"


# ---------------------------------------------------------------------------
# to_show() — returns None on invalid input
# ---------------------------------------------------------------------------


class TestToShowReturnsNone:
    def test_empty_title(self):
        assert _event(title="").to_show(_club()) is None

    def test_empty_time_str(self):
        assert _event(time_str="").to_show(_club()) is None

    def test_unparseable_time_str(self):
        assert _event(time_str="not a time").to_show(_club()) is None


# ---------------------------------------------------------------------------
# to_show() — ticket tiers
# ---------------------------------------------------------------------------


class TestToShowTickets:
    def test_fallback_ticket_when_no_tiers(self):
        show = _event(ticket_tiers=[]).to_show(_club())
        assert len(show.tickets) == 1
        assert "event_id=5678" in show.tickets[0].purchase_url

    def test_multiple_tiers_produce_multiple_tickets(self):
        tiers = [
            FlappersTicketTier(price=25.0, ticket_type="General Admission"),
            FlappersTicketTier(price=40.0, ticket_type="VIP", sold_out=True),
        ]
        show = _event(ticket_tiers=tiers).to_show(_club())
        assert len(show.tickets) == 2
        assert show.tickets[0].price == 25.0
        assert show.tickets[1].price == 40.0
        assert show.tickets[1].sold_out is True

    def test_tier_ticket_type_preserved(self):
        tiers = [FlappersTicketTier(price=30.0, ticket_type="Premium Seating")]
        show = _event(ticket_tiers=tiers).to_show(_club())
        assert show.tickets[0].type == "Premium Seating"


# ---------------------------------------------------------------------------
# to_show() — lineup
# ---------------------------------------------------------------------------


class TestToShowLineup:
    def test_lineup_from_performer_names(self):
        show = _event(lineup_names=["Alice", "Bob"]).to_show(_club())
        assert len(show.lineup) == 2

    def test_empty_lineup_names(self):
        show = _event(lineup_names=[]).to_show(_club())
        assert show.lineup == []
