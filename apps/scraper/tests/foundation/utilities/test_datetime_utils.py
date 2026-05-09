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
