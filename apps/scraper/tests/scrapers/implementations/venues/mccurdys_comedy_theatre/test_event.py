"""
Unit tests for McCurdysEvent._parse_performance year inference and to_show.
"""

from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest

from laughtrack.core.entities.event.mccurdys_comedy_theatre import (
    McCurdysEvent,
    _parse_performance,
)


# ── _parse_performance ──────────────────────────────────────────────────


class TestParsePerformance:
    def test_basic_parse(self):
        with patch(
            "laughtrack.core.entities.event.mccurdys_comedy_theatre.date"
        ) as mock_date:
            mock_date.today.return_value = date(2026, 4, 1)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            result = _parse_performance("Thursday, April 09 at 7:00 PM")
        assert result is not None
        parsed_date, time_str = result
        assert parsed_date == date(2026, 4, 9)
        assert time_str == "7:00 PM"

    def test_am_time(self):
        with patch(
            "laughtrack.core.entities.event.mccurdys_comedy_theatre.date"
        ) as mock_date:
            mock_date.today.return_value = date(2026, 4, 1)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            result = _parse_performance("Sunday, April 12 at 11:00 AM")
        assert result is not None
        assert result[1] == "11:00 AM"

    def test_year_inference_uses_next_year_when_past(self):
        """If the month/day already passed this year, pick next year."""
        with patch(
            "laughtrack.core.entities.event.mccurdys_comedy_theatre.date"
        ) as mock_date:
            mock_date.today.return_value = date(2026, 6, 15)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            result = _parse_performance("Wednesday, January 07 at 8:00 PM")
        assert result is not None
        assert result[0] == date(2027, 1, 7)

    def test_allows_yesterday(self):
        """Dates 1 day in the past are still accepted (today - 1 threshold)."""
        with patch(
            "laughtrack.core.entities.event.mccurdys_comedy_theatre.date"
        ) as mock_date:
            mock_date.today.return_value = date(2026, 4, 10)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            result = _parse_performance("Thursday, April 09 at 7:00 PM")
        assert result is not None
        assert result[0] == date(2026, 4, 9)

    def test_rejects_date_more_than_one_day_past(self):
        """Dates more than 1 day in the past for both years return None."""
        with patch(
            "laughtrack.core.entities.event.mccurdys_comedy_theatre.date"
        ) as mock_date:
            # Set today to Dec 31 — Jan 7 of current year is ~358 days ago,
            # and Jan 7 of next year is still in the future, so it should resolve.
            # Instead use a date where both years fail:
            # today = March 15, date_str = March 1 → Mar 1 2026 is 14 days ago,
            # Mar 1 2027 is in the future → should pick 2027
            mock_date.today.return_value = date(2026, 3, 15)
            mock_date.side_effect = lambda *a, **k: date(*a, **k)
            result = _parse_performance("Sunday, March 01 at 7:00 PM")
        # March 1 2026 is 14 days ago, but March 1 2027 is future → picks 2027
        assert result is not None
        assert result[0] == date(2027, 3, 1)

    def test_unparseable_returns_none(self):
        assert _parse_performance("Not a date at all") is None

    def test_malformed_time_returns_none(self):
        assert _parse_performance("Thursday, April 09 at 25:00 ZM") is None

    def test_missing_weekday_returns_none(self):
        assert _parse_performance("April 09 at 7:00 PM") is None


# ── McCurdysEvent.to_show ───────────────────────────────────────────────


class TestToShow:
    def _make_club(self):
        club = MagicMock()
        club.id = 999
        club.timezone = "America/New_York"
        return club

    def test_returns_none_for_empty_title(self):
        event = McCurdysEvent(title="", date_str="Friday, April 10 at 7:30 PM", ticket_url="https://etix.com/ticket/p/1")
        assert event.to_show(self._make_club()) is None

    def test_returns_none_for_empty_date_str(self):
        event = McCurdysEvent(title="Test", date_str="", ticket_url="https://etix.com/ticket/p/1")
        assert event.to_show(self._make_club()) is None

    def test_returns_none_for_empty_ticket_url(self):
        event = McCurdysEvent(title="Test", date_str="Friday, April 10 at 7:30 PM", ticket_url="")
        assert event.to_show(self._make_club()) is None

    def test_returns_none_for_unparseable_date(self):
        event = McCurdysEvent(title="Test", date_str="not a date", ticket_url="https://etix.com/ticket/p/1")
        assert event.to_show(self._make_club()) is None

    @patch("laughtrack.core.entities.event.mccurdys_comedy_theatre._parse_performance")
    @patch("laughtrack.core.entities.event.mccurdys_comedy_theatre.Logger")
    def test_successful_to_show(self, _mock_logger, mock_parse):
        mock_parse.return_value = (date(2026, 4, 10), "7:30 PM")
        club = self._make_club()
        event = McCurdysEvent(
            title="Jamie Lissow",
            date_str="Friday, April 10 at 7:30 PM",
            ticket_url="https://www.etix.com/ticket/p/80809269",
        )
        show = event.to_show(club)
        assert show is not None
        assert show.name == "Jamie Lissow"
