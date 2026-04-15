"""Unit tests for ShopifyEvent entity and helper functions.

Covers:
  - extract_comedian_name (Format A / Format B titles)
  - parse_variant_datetime (Format A variant titles)
  - parse_product_title_datetime (Format B product titles)
  - ShopifyEvent.to_show conversion
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.shopify import (
    ShopifyEvent,
    extract_comedian_name,
    parse_variant_datetime,
    parse_product_title_datetime,
)
from laughtrack.core.entities.club.model import Club

TZ = "America/Los_Angeles"


def make_club() -> Club:
    return Club(
        id=99,
        name="American Comedy Co.",
        address="818 Sixth Ave, San Diego, CA 92101",
        website="https://www.americancomedyco.com",
        scraping_url="https://www.americancomedyco.com",
        popularity=10,
        zip_code="92101",
        phone_number="",
        visible=True,
        timezone=TZ,
    )


# ---------------------------------------------------------------------------
# extract_comedian_name
# ---------------------------------------------------------------------------


class TestExtractComedianName:
    """Format A: strip LIVE!, [DAY], parentheticals. Format B: split on ' - '."""

    def test_format_a_live_bang(self):
        assert extract_comedian_name("Michael Rapaport LIVE! [THU]") == "Michael Rapaport"

    def test_format_a_live_no_bang(self):
        assert extract_comedian_name("John Mulaney Live") == "John Mulaney"

    def test_format_a_day_bracket_only(self):
        assert extract_comedian_name("Jo Koy [FRI]") == "Jo Koy"

    def test_format_a_parenthetical(self):
        assert extract_comedian_name("Ali Wong (Early Show)") == "Ali Wong"

    def test_format_a_multiple_suffixes(self):
        assert extract_comedian_name("Dave Chappelle LIVE! [SAT] (Late Show)") == "Dave Chappelle"

    def test_format_b_with_date(self):
        name = extract_comedian_name(
            "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"
        )
        assert name == "Des Mulrooney, Caleb Synan and Landry"

    def test_format_b_with_prefix(self):
        name = extract_comedian_name(
            "*Late Show Pricing* Fri Apr 17th @9:30pm - Ross Bennett, JJ Whitehead and Brian Kiley"
        )
        assert name == "Ross Bennett, JJ Whitehead and Brian Kiley"

    def test_plain_name_no_suffixes(self):
        assert extract_comedian_name("Mark Normand") == "Mark Normand"

    def test_empty_string(self):
        assert extract_comedian_name("") == ""


# ---------------------------------------------------------------------------
# parse_variant_datetime
# ---------------------------------------------------------------------------


class TestParseVariantDatetime:
    """Format A: 'DayOfWeek Month DD YYYY / H:MMam/pm ...' """

    def test_canonical(self):
        dt = parse_variant_datetime("Thursday April 9 2026 / 8:00pm General Admission", TZ)
        assert dt is not None
        assert dt == datetime(2026, 4, 9, 20, 0, tzinfo=ZoneInfo(TZ))

    def test_spaced_am_pm(self):
        dt = parse_variant_datetime("Friday April 10 2026 / 7:30 PM VIP", TZ)
        assert dt is not None
        assert dt == datetime(2026, 4, 10, 19, 30, tzinfo=ZoneInfo(TZ))

    def test_morning_time(self):
        dt = parse_variant_datetime("Saturday January 3 2026 / 11:00AM Brunch Show", TZ)
        assert dt is not None
        assert dt.hour == 11

    def test_different_timezone(self):
        dt = parse_variant_datetime("Monday June 1 2026 / 9:00pm GA", "America/New_York")
        assert dt is not None
        assert dt.tzinfo == ZoneInfo("America/New_York")

    def test_tier_only_returns_none(self):
        """Variant titles like 'General Admission' (no date) should return None."""
        assert parse_variant_datetime("General Admission", TZ) is None

    def test_vip_tier_returns_none(self):
        assert parse_variant_datetime("VIP", TZ) is None

    def test_empty_string_returns_none(self):
        assert parse_variant_datetime("", TZ) is None

    def test_garbage_returns_none(self):
        assert parse_variant_datetime("not a date at all", TZ) is None

    def test_missing_year_returns_none(self):
        """Without year in variant, regex should not match."""
        assert parse_variant_datetime("Thursday April 9 / 8:00pm General Admission", TZ) is None


# ---------------------------------------------------------------------------
# parse_product_title_datetime
# ---------------------------------------------------------------------------


class TestParseProductTitleDatetime:
    """Format B: 'Day Mon DDth @H:MMam/pm - comedian(s)' """

    def test_canonical(self):
        dt = parse_product_title_datetime("Sat Apr 11th @6:30pm - Des Mulrooney", TZ)
        assert dt is not None
        assert dt.month == 4
        assert dt.day == 11
        assert dt.hour == 18
        assert dt.minute == 30

    def test_no_ordinal(self):
        dt = parse_product_title_datetime("Fri Apr 17 @9:30pm - Ross Bennett", TZ)
        assert dt is not None
        assert dt.day == 17
        assert dt.hour == 21
        assert dt.minute == 30

    def test_hour_only_no_colon(self):
        """Time like '@7pm' (no minutes) should parse as 7:00 PM."""
        dt = parse_product_title_datetime("Tue Mar 3rd @7pm - Test Comic", TZ)
        assert dt is not None
        assert dt.hour == 19
        assert dt.minute == 0

    def test_with_prefix_text(self):
        dt = parse_product_title_datetime(
            "*Late Show Pricing* Fri Apr 17th @9:30pm - Brian Kiley", TZ
        )
        assert dt is not None
        assert dt.hour == 21

    def test_timezone_aware(self):
        dt = parse_product_title_datetime("Sat Apr 11th @6:30pm - Test", TZ)
        assert dt is not None
        assert dt.tzinfo == ZoneInfo(TZ)

    def test_no_match_returns_none(self):
        assert parse_product_title_datetime("Michael Rapaport LIVE! [THU]", TZ) is None

    def test_empty_string_returns_none(self):
        assert parse_product_title_datetime("", TZ) is None

    def test_garbage_returns_none(self):
        assert parse_product_title_datetime("not a date at all", TZ) is None


# ---------------------------------------------------------------------------
# ShopifyEvent.to_show
# ---------------------------------------------------------------------------


class TestShopifyEventToShow:
    def _make_event(self, **overrides) -> ShopifyEvent:
        defaults = dict(
            product_id=12345,
            title="Michael Rapaport LIVE! [THU]",
            handle="michael-rapaport-live-thu",
            show_date=datetime(2026, 4, 9, 20, 0, tzinfo=ZoneInfo(TZ)),
            price="25.00",
            available=True,
            image_url="https://cdn.shopify.com/image.jpg",
            body_html="<p>Great show</p>",
            timezone=TZ,
            tags=["comedy"],
        )
        defaults.update(overrides)
        return ShopifyEvent(**defaults)

    def test_basic_conversion(self):
        event = self._make_event()
        club = make_club()
        show = event.to_show(club, enhanced=False)

        assert show is not None
        assert show.name == "Michael Rapaport"
        assert show.club_id == club.id
        assert show.date == datetime(2026, 4, 9, 20, 0, tzinfo=ZoneInfo(TZ))

    def test_ticket_url_uses_handle(self):
        event = self._make_event(handle="my-show")
        club = make_club()
        show = event.to_show(club, enhanced=False)

        assert show is not None
        assert "/products/my-show" in show.show_page_url

    def test_custom_url_override(self):
        event = self._make_event()
        club = make_club()
        show = event.to_show(club, enhanced=False, url="https://custom.com/tickets")

        assert show is not None
        assert show.show_page_url == "https://custom.com/tickets"

    def test_format_b_title_extracts_comedian(self):
        event = self._make_event(
            title="Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan"
        )
        show = event.to_show(make_club(), enhanced=False)

        assert show is not None
        assert show.name == "Des Mulrooney, Caleb Synan"

    def test_has_tickets(self):
        event = self._make_event()
        show = event.to_show(make_club(), enhanced=False)

        assert show is not None
        assert len(show.tickets) >= 1
