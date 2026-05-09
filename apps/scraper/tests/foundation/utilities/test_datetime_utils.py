from laughtrack.foundation.utilities.datetime import DateTimeUtils


def test_month_name_to_number_accepts_abbreviations_and_full_names_case_insensitively():
    assert DateTimeUtils.month_name_to_number("jan") == 1
    assert DateTimeUtils.month_name_to_number("SEPTEMBER") == 9
    assert DateTimeUtils.month_name_to_number("ApR") == 4


def test_month_name_to_number_returns_none_for_unknown_input():
    assert DateTimeUtils.month_name_to_number("notamonth") is None
