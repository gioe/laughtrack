"""Unit tests for _is_valid_lineup_name() structural rejection rules added in TASK-638."""

import pytest

from laughtrack.utilities.domain.show.factory import _is_valid_lineup_name


class TestPipeRejection:
    def test_pipe_in_name_rejected(self):
        assert _is_valid_lineup_name("Title | Subtitle") is False

    def test_pipe_only_rejected(self):
        assert _is_valid_lineup_name("A | B") is False

    def test_no_pipe_passes(self):
        assert _is_valid_lineup_name("Dave Chappelle") is True


class TestLengthRejection:
    def test_exactly_60_chars_passes(self):
        name = "A" * 60
        assert _is_valid_lineup_name(name) is True

    def test_61_chars_rejected(self):
        name = "A" * 61
        assert _is_valid_lineup_name(name) is False

    def test_long_show_title_rejected(self):
        assert _is_valid_lineup_name("A Very Long Show Title That Goes Well Beyond Sixty Characters Total") is False


class TestTitleKeywordRejection:
    @pytest.mark.parametrize("keyword", [
        "Revue", "Burlesque", "Variety", "Showcase", "Production",
        "Presents", "Festival", "Extravaganza", "Theatre", "Theater",
        "Entertainment", "Brigade",
    ])
    def test_keyword_in_name_rejected(self, keyword):
        assert _is_valid_lineup_name(f"The {keyword}") is False

    def test_keyword_case_insensitive(self):
        assert _is_valid_lineup_name("comedy VARIETY show") is False

    def test_legitimate_name_passes(self):
        assert _is_valid_lineup_name("Ali Wong") is True


class TestVenueCodePrefixRejection:
    def test_uppercase_letter_prefix_rejected(self):
        assert _is_valid_lineup_name("(T)Foo Bar") is False

    def test_r_prefix_rejected(self):
        assert _is_valid_lineup_name("(R)Something") is False

    def test_lowercase_prefix_not_rejected(self):
        # Pattern only matches uppercase single letter
        assert _is_valid_lineup_name("(a)Something Else") is True

    def test_two_letter_prefix_not_rejected(self):
        assert _is_valid_lineup_name("(TT)Something") is True


class TestRealWorldExample:
    def test_its_academic_rejected(self):
        assert _is_valid_lineup_name(
            "(T)It's Academic! | A Highly Educational Burlesque and Variety Revue"
        ) is False


class TestLegitimateNamesStillPass:
    @pytest.mark.parametrize("name", [
        "Dave Chappelle",
        "Ali Wong",
        "John Mulaney",
        "Bo Burnham",
        "Amy Schumer",
        "Jo-Anne Smith",
    ])
    def test_legitimate_name_passes(self, name):
        assert _is_valid_lineup_name(name) is True
