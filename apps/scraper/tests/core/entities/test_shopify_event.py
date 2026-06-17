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
from laughtrack.core.entities.club.model import Club, ScrapingSource

TZ = "America/Los_Angeles"


def make_club() -> Club:
    _c = Club(id=99, name='American Comedy Co.', address='818 Sixth Ave, San Diego, CA 92101', website='https://www.americancomedyco.com', popularity=10, zip_code='92101', phone_number='', visible=True, timezone=TZ)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.americancomedyco.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


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

    def test_ticket_carries_variant_price(self):
        """The extracted lowest variant price reaches the ticket (TASK-2827:
        it was previously dropped — create_fallback_ticket got no price arg)."""
        event = self._make_event(price="25.00")
        show = event.to_show(make_club(), enhanced=False)

        assert show is not None
        assert show.tickets[0].price == 25.0

    def test_zero_price_treated_as_unknown(self):
        """A 0.00 variant price is a placeholder, not a proven-free show."""
        event = self._make_event(price="0.00")
        show = event.to_show(make_club(), enhanced=False)

        assert show is not None
        assert show.tickets[0].price is None

    def test_unparseable_price_treated_as_unknown(self):
        event = self._make_event(price="")
        show = event.to_show(make_club(), enhanced=False)

        assert show is not None
        assert show.tickets[0].price is None


# ---------------------------------------------------------------------------
# Format C: handle/numeric-title date + clock time (TASK-2949)
# ---------------------------------------------------------------------------

from datetime import datetime as _dt  # noqa: E402

import laughtrack.core.entities.event.shopify as _shopify_mod  # noqa: E402
from laughtrack.core.entities.event.shopify import (  # noqa: E402
    parse_clock_time,
    parse_handle_title_date,
)


class _FixedNow(_dt):
    """datetime subclass with a frozen now() for hermetic year-inference tests."""

    @classmethod
    def now(cls, tz=None):
        return _dt(2026, 6, 17, 12, 0, 0, tzinfo=tz)


class TestParseClockTime:
    def test_pm_no_minutes(self):
        assert parse_clock_time("7pm") == (19, 0)

    def test_pm_with_minutes_and_text(self):
        assert parse_clock_time("6:30 PM - The Audacity / Anecdotal Harmony") == (18, 30)

    def test_leading_variant_time(self):
        assert parse_clock_time("6pm - Who Are We Anyway? / Awkward Noize") == (18, 0)

    def test_noon_and_midnight(self):
        assert parse_clock_time("12pm") == (12, 0)
        assert parse_clock_time("12am") == (0, 0)

    def test_no_time(self):
        assert parse_clock_time("Default Title") is None
        assert parse_clock_time("Any two shows") is None
        assert parse_clock_time("") is None


class TestParseHandleTitleDate:
    def test_explicit_ymd_handle_uses_title_day_and_handle_year(self):
        # handle says 0625, title (advertised) says 6/26 → trust title day, handle year
        dt = parse_handle_title_date("20260625-capybara-comedy-hour", "6/26 7pm - Capybara", TZ)
        assert (dt.year, dt.month, dt.day) == (2026, 6, 26)

    def test_explicit_ymd_handle_without_title_md(self):
        dt = parse_handle_title_date("20260625-capybara-comedy-hour", "Capybara Comedy Hour", TZ)
        assert (dt.year, dt.month, dt.day) == (2026, 6, 25)

    def test_explicit_year_is_not_dropped_when_past(self, monkeypatch):
        # explicit YYYYMMDD year is trusted verbatim, never the drop-if-past path
        monkeypatch.setattr(_shopify_mod, "datetime", _FixedNow)
        dt = parse_handle_title_date("20240101-old-show", "Old Show", TZ)
        assert (dt.year, dt.month, dt.day) == (2024, 1, 1)

    def test_inferred_future_md_is_kept(self, monkeypatch):
        monkeypatch.setattr(_shopify_mod, "datetime", _FixedNow)
        dt = parse_handle_title_date("7-10-cool-kids", "7/10 7pm - Cool Kids", TZ)
        assert (dt.year, dt.month, dt.day) == (2026, 7, 10)

    def test_inferred_past_md_is_dropped(self, monkeypatch):
        # 6/6 is past relative to frozen now 2026-06-17 → stale listing, dropped
        monkeypatch.setattr(_shopify_mod, "datetime", _FixedNow)
        assert parse_handle_title_date("6-6-improv", "6/6 Saturday Night Improv Shows", TZ) is None

    def test_handle_md_prefix_used_when_no_title_md(self, monkeypatch):
        monkeypatch.setattr(_shopify_mod, "datetime", _FixedNow)
        dt = parse_handle_title_date("6-27-saturday-night-improv", "Saturday Night Improv Shows", TZ)
        assert (dt.year, dt.month, dt.day) == (2026, 6, 27)

    def test_no_date_returns_none(self):
        assert parse_handle_title_date("makers-market", "Makers Market", TZ) is None


class TestExtractComedianNameFormatC:
    def test_strips_numeric_date_time_prefix(self):
        assert (
            extract_comedian_name("6/26 7pm - Capybara Comedy Hour Featuring Jon Flanagan")
            == "Capybara Comedy Hour Featuring Jon Flanagan"
        )

    def test_strips_numeric_date_prefix_without_time(self):
        assert extract_comedian_name("6/27 Saturday Night Improv Shows") == "Saturday Night Improv Shows"
