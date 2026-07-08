from datetime import date, datetime

import pytz

from laughtrack.foundation.utilities.datetime import DateTimeUtils


def test_month_name_to_number_accepts_abbreviations_and_full_names_case_insensitively():
    assert DateTimeUtils.month_name_to_number("jan") == 1
    assert DateTimeUtils.month_name_to_number("SEPTEMBER") == 9
    assert DateTimeUtils.month_name_to_number("ApR") == 4


def test_month_name_to_number_returns_none_for_unknown_input():
    assert DateTimeUtils.month_name_to_number("notamonth") is None


def test_parse_flexible_date_accepts_time_only_without_spaces():
    parsed = DateTimeUtils.parse_flexible_date("7:30PM")

    assert parsed is not None
    assert parsed.hour == 19
    assert parsed.minute == 30


def test_parse_flexible_date_accepts_month_day_year_with_time():
    parsed = DateTimeUtils.parse_flexible_date("May 2 2026 3:00 pm")

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 5
    assert parsed.day == 2
    assert parsed.hour == 15
    assert parsed.minute == 0


def test_parse_flexible_date_accepts_full_month_day_year_without_comma():
    parsed = DateTimeUtils.parse_flexible_date("May 2 2026")

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 5
    assert parsed.day == 2


def test_infer_year_rolls_january_forward_from_late_december_clock():
    today = date(2026, 12, 28)

    assert DateTimeUtils.infer_year(1, 2, today=today) == 2027


def test_infer_year_keeps_recent_late_december_from_early_january_clock():
    today = date(2027, 1, 2)

    assert DateTimeUtils.infer_year(12, 31, today=today) == 2026


def test_infer_year_respects_horizon_for_recent_past_dates():
    today = date(2027, 1, 2)

    assert DateTimeUtils.infer_year(12, 31, today=today, horizon_days=2) == 2026
    assert DateTimeUtils.infer_year(12, 30, today=today, horizon_days=2) == 2027


def test_infer_year_uses_weekday_to_disambiguate_across_years():
    today = date(2026, 12, 28)

    assert DateTimeUtils.infer_year(1, 2, today=today, weekday_abbr="Sat") == 2027
    assert DateTimeUtils.infer_year(1, 2, today=today, weekday_abbr="Fri") == 2026


def test_venue_wall_clock_to_utc_summer_uses_edt_offset():
    # July in America/New_York is EDT (UTC-4): 8pm local -> midnight UTC next day.
    result = DateTimeUtils.venue_wall_clock_to_utc(datetime(2026, 7, 15, 20, 0), "America/New_York")

    assert result.tzinfo == pytz.UTC
    assert result == datetime(2026, 7, 16, 0, 0, tzinfo=pytz.UTC)


def test_venue_wall_clock_to_utc_winter_uses_est_offset():
    # January in America/New_York is EST (UTC-5): 8pm local -> 1am UTC next day.
    result = DateTimeUtils.venue_wall_clock_to_utc(datetime(2026, 1, 15, 20, 0), "America/New_York")

    assert result == datetime(2026, 1, 16, 1, 0, tzinfo=pytz.UTC)


def test_venue_wall_clock_to_utc_honors_west_coast_zone():
    # July in America/Los_Angeles is PDT (UTC-7): 8pm local -> 3am UTC next day.
    result = DateTimeUtils.venue_wall_clock_to_utc(datetime(2026, 7, 15, 20, 0), "America/Los_Angeles")

    assert result == datetime(2026, 7, 16, 3, 0, tzinfo=pytz.UTC)


def test_venue_wall_clock_to_utc_passes_through_aware_datetime():
    aware = pytz.timezone("America/New_York").localize(datetime(2026, 7, 15, 20, 0))

    result = DateTimeUtils.venue_wall_clock_to_utc(aware, "America/Los_Angeles")

    # Already-aware input is converted directly, ignoring tz_name.
    assert result == datetime(2026, 7, 16, 0, 0, tzinfo=pytz.UTC)
