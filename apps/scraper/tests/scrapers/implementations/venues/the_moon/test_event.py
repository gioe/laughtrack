"""Unit tests for TheMoonEvent: _parse_date, _normalize_time, _extract_door_time,
and to_show conversion."""

from datetime import datetime

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.the_moon import (
    TheMoonEvent,
    _extract_door_time,
    _normalize_time,
    _parse_date,
)


def _club() -> Club:
    return Club(
        id=200,
        name="The Moon",
        address="1105 E Lafayette St, Tallahassee, FL 32301",
        website="https://moonevents.com",
        scraping_url="https://moonevents.com/events/",
        popularity=0,
        zip_code="32301",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _event(**overrides) -> TheMoonEvent:
    defaults = dict(
        title="Rob Schneider",
        date_str="Sat, May 30, 2026",
        time_str="Door Time Is: 6:30 pm",
        ticket_url="https://www.etix.com/ticket/p/37927456/rob-schneider",
    )
    defaults.update(overrides)
    return TheMoonEvent(**defaults)


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_full_format_with_weekday_and_year(self):
        result = _parse_date("Sat, May 30, 2026")
        assert result == datetime(2026, 5, 30)

    def test_format_without_weekday(self):
        result = _parse_date("May 30, 2026")
        assert result == datetime(2026, 5, 30)

    def test_without_year_infers_future(self):
        """Date without year picks the next occurrence >= yesterday."""
        result = _parse_date("Sat, Dec 15")
        assert result is not None
        assert result.month == 12
        assert result.day == 15

    def test_without_year_uses_far_future(self):
        """A date string with explicit year parses correctly."""
        result = _parse_date("Jun 15, 2099")
        assert result is not None
        assert result.year == 2099
        assert result.month == 6
        assert result.day == 15

    def test_invalid_date_returns_none(self):
        assert _parse_date("not a date") is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_extra_whitespace_stripped(self):
        result = _parse_date("  Sat,  May  30,  2026  ")
        assert result == datetime(2026, 5, 30)


# ---------------------------------------------------------------------------
# _normalize_time
# ---------------------------------------------------------------------------


class TestNormalizeTime:
    def test_bare_hour_pm(self):
        assert _normalize_time("8 pm") == "8:00 PM"

    def test_hour_with_minutes(self):
        assert _normalize_time("6:30 pm") == "6:30 PM"

    def test_am(self):
        assert _normalize_time("11 am") == "11:00 AM"

    def test_uppercase_input(self):
        assert _normalize_time("8 PM") == "8:00 PM"

    def test_no_space_before_ampm(self):
        """Regex allows optional whitespace — '8pm' is still valid."""
        assert _normalize_time("8pm") == "8:00 PM"

    def test_invalid_returns_none(self):
        assert _normalize_time("noon") is None

    def test_empty_returns_none(self):
        assert _normalize_time("") is None


# ---------------------------------------------------------------------------
# _extract_door_time
# ---------------------------------------------------------------------------


class TestExtractDoorTime:
    def test_full_door_time_string(self):
        assert _extract_door_time("Door Time Is: 6:30 pm") == "6:30 PM"

    def test_door_time_bare_hour(self):
        assert _extract_door_time("Door Time Is: 8 pm") == "8:00 PM"

    def test_bare_time_fallback(self):
        """When no 'Door Time Is:' prefix, tries to parse as bare time."""
        assert _extract_door_time("7 pm") == "7:00 PM"

    def test_unparseable_returns_none(self):
        assert _extract_door_time("TBA") is None

    def test_empty_returns_none(self):
        assert _extract_door_time("") is None


# ---------------------------------------------------------------------------
# to_show — conversion
# ---------------------------------------------------------------------------


class TestToShow:
    def test_happy_path(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.name == "Rob Schneider"
        assert show.club_id == 200
        assert show.show_page_url == "https://www.etix.com/ticket/p/37927456/rob-schneider"

    def test_ticket_url_in_tickets(self):
        show = _event().to_show(_club())
        assert show is not None
        assert len(show.tickets) == 1
        assert "etix.com" in show.tickets[0].purchase_url

    def test_date_is_timezone_aware(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.date.tzinfo is not None

    def test_uses_door_time_for_show_time(self):
        show = _event(time_str="Door Time Is: 7 pm").to_show(_club())
        assert show is not None
        assert show.date.hour == 19

    def test_defaults_to_noon_when_no_time(self):
        show = _event(time_str="").to_show(_club())
        assert show is not None
        assert show.date.hour == 12

    def test_returns_none_on_missing_title(self):
        show = _event(title="").to_show(_club())
        assert show is None

    def test_returns_none_on_missing_date(self):
        show = _event(date_str="").to_show(_club())
        assert show is None

    def test_returns_none_on_missing_ticket_url(self):
        show = _event(ticket_url="").to_show(_club())
        assert show is None

    def test_returns_none_on_unparseable_date(self):
        show = _event(date_str="not a date").to_show(_club())
        assert show is None

    def test_url_override(self):
        show = _event().to_show(_club(), url="https://override.com/ticket")
        assert show is not None
        assert show.show_page_url == "https://override.com/ticket"
