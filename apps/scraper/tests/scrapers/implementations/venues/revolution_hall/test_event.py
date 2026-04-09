"""Unit tests for RevolutionHallEvent: date parsing (ISO primary, date_text fallback,
show time extraction) and to_show conversion (sold_out ticket, SOLD OUT prefix stripping)."""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.revolution_hall import RevolutionHallEvent
from laughtrack.core.entities.ticket.model import Ticket


def _club() -> Club:
    return Club(
        id=99,
        name="Revolution Hall",
        address="1300 SE Stark St, Portland, OR 97214",
        website="https://www.revolutionhallpdx.com",
        scraping_url="https://www.revolutionhallpdx.com",
        popularity=0,
        zip_code="97214",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _event(**overrides) -> RevolutionHallEvent:
    defaults = dict(
        name="Shane Gillis",
        date_text="Fri, April 10th, 2026",
        doors_iso="2026-04-11T01:00:00Z",
        time_text="Doors: 6PM / Show: 7PM",
        ticket_url="https://www.etix.com/ticket/p/77680474/shane-gillis",
        age_restriction="All Ages",
        status="on_sale",
        image_url="https://cdn.etix.com/images/poster.jpg",
    )
    defaults.update(overrides)
    return RevolutionHallEvent(**defaults)


# ---------------------------------------------------------------------------
# _extract_show_time
# ---------------------------------------------------------------------------


class TestExtractShowTime:
    def test_show_time_preferred_over_doors(self):
        e = _event(time_text="Doors: 6PM / Show: 7PM")
        hour, minute = e._extract_show_time()
        assert hour == 19
        assert minute == 0

    def test_show_time_with_minutes(self):
        e = _event(time_text="Doors: 6PM / Show: 7:30PM")
        hour, minute = e._extract_show_time()
        assert hour == 19
        assert minute == 30

    def test_doors_fallback_when_no_show(self):
        e = _event(time_text="Doors: 6PM")
        hour, minute = e._extract_show_time()
        assert hour == 18
        assert minute == 0

    def test_am_time(self):
        e = _event(time_text="Show: 11AM")
        hour, minute = e._extract_show_time()
        assert hour == 11
        assert minute == 0

    def test_noon(self):
        e = _event(time_text="Show: 12PM")
        hour, minute = e._extract_show_time()
        assert hour == 12
        assert minute == 0

    def test_midnight(self):
        e = _event(time_text="Show: 12AM")
        hour, minute = e._extract_show_time()
        assert hour == 0
        assert minute == 0

    def test_empty_time_text(self):
        e = _event(time_text="")
        hour, minute = e._extract_show_time()
        assert hour is None
        assert minute == 0

    def test_unparseable_time_text(self):
        e = _event(time_text="TBA")
        hour, minute = e._extract_show_time()
        assert hour is None
        assert minute == 0


# ---------------------------------------------------------------------------
# _parse_datetime — primary ISO path
# ---------------------------------------------------------------------------


class TestParseDatetimePrimary:
    def test_iso_with_show_time(self):
        """Primary path: doors_iso date + show time from time_text."""
        e = _event(
            doors_iso="2026-04-11T01:00:00Z",  # UTC midnight = April 10 PDT
            time_text="Doors: 6PM / Show: 7PM",
        )
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is not None
        assert dt.hour == 19
        assert dt.minute == 0
        assert dt.month == 4
        assert dt.day == 10  # April 10 in PDT

    def test_iso_without_show_time_uses_doors(self):
        """When time_text is empty, use the doors time directly."""
        e = _event(doors_iso="2026-04-11T01:00:00Z", time_text="")
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is not None
        # 01:00 UTC = 18:00 PDT (April 10)
        assert dt.hour == 18
        assert dt.day == 10

    def test_invalid_iso_falls_back_to_date_text(self):
        e = _event(doors_iso="not-a-date", date_text="Fri, April 10th, 2026", time_text="Show: 7PM")
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is not None
        assert dt.month == 4
        assert dt.day == 10
        assert dt.hour == 19


# ---------------------------------------------------------------------------
# _parse_date_text — fallback path
# ---------------------------------------------------------------------------


class TestParseDateText:
    def test_full_format_with_year(self):
        e = _event(doors_iso="", date_text="Sat, June 20th, 2026", time_text="Show: 8PM")
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 6
        assert dt.day == 20
        assert dt.hour == 20

    def test_ordinal_suffixes_stripped(self):
        """All ordinal suffixes (st, nd, rd, th) are handled."""
        for suffix, day in [("1st", 1), ("2nd", 2), ("3rd", 3), ("15th", 15)]:
            e = _event(doors_iso="", date_text=f"Mon, June {suffix}, 2026", time_text="Show: 8PM")
            dt = e._parse_datetime("America/Los_Angeles")
            assert dt is not None, f"Failed for {suffix}"
            assert dt.day == day

    def test_no_year_infers_future(self):
        """Date without year infers the next occurrence."""
        e = _event(doors_iso="", date_text="Sat, December 20", time_text="Show: 9PM")
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is not None
        assert dt.month == 12
        assert dt.day == 20

    def test_default_hour_when_no_show_time(self):
        """When time_text is unparseable, defaults to 8PM (20:00)."""
        e = _event(doors_iso="", date_text="Fri, April 10th, 2026", time_text="TBA")
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is not None
        assert dt.hour == 20
        assert dt.minute == 0

    def test_empty_date_text_returns_none(self):
        e = _event(doors_iso="", date_text="")
        dt = e._parse_datetime("America/Los_Angeles")
        assert dt is None


# ---------------------------------------------------------------------------
# to_show — conversion
# ---------------------------------------------------------------------------


class TestToShow:
    def test_happy_path(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.name == "Shane Gillis"
        assert show.club_id == 99
        assert show.show_page_url == "https://www.etix.com/ticket/p/77680474/shane-gillis"

    def test_sold_out_prefix_stripped(self):
        show = _event(name="SOLD OUT: Shane Gillis").to_show(_club())
        assert show is not None
        assert show.name == "Shane Gillis"

    def test_sold_out_no_colon_stripped(self):
        show = _event(name="SOLD OUT Shane Gillis").to_show(_club())
        assert show is not None
        assert show.name == "Shane Gillis"

    def test_sold_out_case_insensitive(self):
        show = _event(name="sold out: Mark Normand").to_show(_club())
        assert show is not None
        assert show.name == "Mark Normand"

    def test_sold_out_ticket_flag(self):
        show = _event(status="sold_out").to_show(_club())
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].sold_out is True

    def test_on_sale_ticket_flag(self):
        show = _event(status="on_sale").to_show(_club())
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].sold_out is False

    def test_tags_include_event(self):
        show = _event().to_show(_club())
        assert show is not None
        assert "event" in show.supplied_tags

    def test_date_is_timezone_aware(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.date.tzinfo is not None

    def test_returns_none_on_unparseable_date(self):
        show = _event(doors_iso="bad", date_text="bad").to_show(_club())
        assert show is None
