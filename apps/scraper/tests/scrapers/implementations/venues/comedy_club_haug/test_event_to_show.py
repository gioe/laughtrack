"""
Unit tests for ComedyClubHaugEvent.to_show() — conversion from scraped event to Show model.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_club_haug import ComedyClubHaugEvent

TZ = "Europe/Amsterdam"


def _club(**overrides) -> Club:
    defaults = dict(
        id=157,
        name="Comedy Club Haug",
        address="Nieuwe Binnenweg 19",
        website="https://comedyclubhaug.com",
        scraping_url="https://comedyclubhaug.com/shows",
        popularity=0,
        zip_code="3014 GA",
        phone_number="",
        visible=True,
        timezone=TZ,
    )
    defaults.update(overrides)
    return Club(**defaults)


def _event(**overrides) -> ComedyClubHaugEvent:
    defaults = dict(
        title="Best of Stand-Up",
        subtitle="MC Hidde van Gestel",
        start_time="2026-04-09T18:30:00+00:00",
        end_time="2026-04-09T20:30:00+00:00",
        ticket_url="https://stager.co/events/best-of-stand-up",
        show_page_url="https://comedyclubhaug.com/shows/best-of-stand-up",
        performers=["Theo Maassen", "Hans Teeuwen"],
    )
    defaults.update(overrides)
    return ComedyClubHaugEvent(**defaults)


# ---------------------------------------------------------------------------
# Basic to_show() conversion
# ---------------------------------------------------------------------------


class TestToShowBasic:
    def test_returns_show_with_correct_name(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.name == "Best of Stand-Up"

    def test_correct_club_id(self):
        show = _event().to_show(_club())
        assert show.club_id == 157

    def test_correct_date_components(self):
        # 18:30 UTC → 20:30 CEST (Europe/Amsterdam is UTC+2 in April)
        show = _event(start_time="2026-04-09T18:30:00+00:00").to_show(_club())
        assert show is not None
        assert show.date.year == 2026
        assert show.date.month == 4
        assert show.date.day == 9
        assert show.date.hour == 20
        assert show.date.minute == 30

    def test_timezone_conversion_with_offset(self):
        # Event already has +02:00 offset (CEST) — should stay 20:30 Amsterdam
        show = _event(start_time="2026-04-09T20:30:00+02:00").to_show(_club())
        assert show is not None
        assert show.date.hour == 20
        assert show.date.minute == 30

    def test_default_timezone_europe_amsterdam(self):
        # Club with no timezone should default to Europe/Amsterdam
        club = _club(timezone=None)
        show = _event(start_time="2026-04-09T18:30:00+00:00").to_show(club)
        assert show is not None
        assert show.date.hour == 20  # UTC+2 in April

    def test_show_page_url(self):
        show = _event().to_show(_club())
        assert show.show_page_url == "https://comedyclubhaug.com/shows/best-of-stand-up"

    def test_custom_url_override(self):
        show = _event().to_show(_club(), url="https://custom.com/tickets")
        # When url is passed, it becomes the ticket URL but show_page_url stays
        assert show is not None


# ---------------------------------------------------------------------------
# to_show() — returns None on invalid input
# ---------------------------------------------------------------------------


class TestToShowReturnsNone:
    def test_empty_title(self):
        assert _event(title="").to_show(_club()) is None

    def test_empty_start_time(self):
        assert _event(start_time="").to_show(_club()) is None

    def test_unparseable_start_time(self):
        assert _event(start_time="not-a-date").to_show(_club()) is None


# ---------------------------------------------------------------------------
# to_show() — tickets
# ---------------------------------------------------------------------------


class TestToShowTickets:
    def test_ticket_from_ticket_url(self):
        show = _event(ticket_url="https://stager.co/events/comedy-night").to_show(_club())
        assert len(show.tickets) == 1
        assert "stager.co" in show.tickets[0].purchase_url

    def test_fallback_to_show_page_url_when_no_ticket_url(self):
        show = _event(
            ticket_url="",
            show_page_url="https://comedyclubhaug.com/shows/comedy-night",
        ).to_show(_club())
        assert len(show.tickets) == 1
        assert "comedyclubhaug.com" in show.tickets[0].purchase_url

    def test_no_tickets_when_no_urls(self):
        show = _event(ticket_url="", show_page_url="").to_show(_club())
        assert show is not None
        assert show.tickets == []


# ---------------------------------------------------------------------------
# to_show() — lineup
# ---------------------------------------------------------------------------


class TestToShowLineup:
    def test_lineup_from_performers(self):
        show = _event(performers=["Alice", "Bob", "Carol"]).to_show(_club())
        assert len(show.lineup) == 3

    def test_empty_performers(self):
        show = _event(performers=[]).to_show(_club())
        assert show.lineup == []
