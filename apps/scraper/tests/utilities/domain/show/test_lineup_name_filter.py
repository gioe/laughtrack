"""Unit tests for _is_valid_lineup_name() and create_lineup_from_performers() filtering."""

import pytest

from laughtrack.utilities.domain.show.factory import (
    _is_valid_lineup_name,
    is_dj_set_show,
    ShowFactoryUtils,
)


# ---------------------------------------------------------------------------
# _is_valid_lineup_name
# ---------------------------------------------------------------------------

class TestIsValidLineupName:
    def test_valid_full_name(self):
        assert _is_valid_lineup_name("John Doe") is True

    def test_valid_single_name(self):
        assert _is_valid_lineup_name("Bo Burnham") is True

    def test_valid_name_with_hyphen(self):
        assert _is_valid_lineup_name("Jo-Anne Smith") is True

    # --- blocklist (exact, case-insensitive) ---

    @pytest.mark.parametrize("name", [
        "TBA",
        "tba",
        "Tba",
        "To Be Announced",
        "to be announced",
        "TO BE ANNOUNCED",
        "TBD",
        "Special Guest",
        "special guest",
        "Special Guests",
        "Surprise Guest",
        "surprise guests",
        "Surprise",
        "SURPRISE",
        "Headliner TBD",
        "Various",
        "various artists",
        "Comedian",
        "comedian",
        "Comedians",
        "Comic",
        "Comics",
        "Host",
        "Emcee",
        "MC",
        "Opener",
        "Openers",
        "Opening Act",
        "To Be Determined",
    ])
    def test_blocklist_name_rejected(self, name):
        assert _is_valid_lineup_name(name) is False

    # --- too short ---

    def test_single_char_rejected(self):
        assert _is_valid_lineup_name("A") is False

    def test_empty_string_rejected(self):
        assert _is_valid_lineup_name("") is False

    def test_whitespace_only_rejected(self):
        assert _is_valid_lineup_name("   ") is False

    def test_two_chars_with_alpha_accepted(self):
        assert _is_valid_lineup_name("Bo") is True

    # --- entirely non-alphabetic ---

    def test_digits_only_rejected(self):
        assert _is_valid_lineup_name("1234") is False

    def test_symbols_only_rejected(self):
        assert _is_valid_lineup_name("---") is False

    def test_mixed_alphanum_accepted(self):
        # has at least one alpha char
        assert _is_valid_lineup_name("MC 900 Ft Jesus") is True

    # --- leading/trailing whitespace is stripped before checks ---

    def test_blocklist_with_surrounding_spaces(self):
        assert _is_valid_lineup_name("  TBA  ") is False

    def test_valid_name_with_surrounding_spaces(self):
        assert _is_valid_lineup_name("  Amy Schumer  ") is True

    def test_none_rejected(self):
        assert _is_valid_lineup_name(None) is False

    # --- exact-match semantics: partial blocklist words in longer names pass ---

    def test_compound_containing_blocked_word_passes(self):
        # "The Comedian" contains "comedian" but is not an exact match
        assert _is_valid_lineup_name("The Comedian") is True

    def test_compound_containing_tba_passes(self):
        # "Headliner: TBA" is not an exact match for any blocklist entry
        assert _is_valid_lineup_name("Headliner: TBA") is True

    def test_trivia_keyword_rejected(self):
        assert _is_valid_lineup_name('"Everything" Trivia w/ Greg!') is False

    def test_trivia_standalone_rejected(self):
        assert _is_valid_lineup_name("Trivia Night") is False


# ---------------------------------------------------------------------------
# create_lineup_from_performers — integration
# ---------------------------------------------------------------------------

class TestCreateLineupFromPerformers:
    def test_valid_string_performers(self):
        lineup = ShowFactoryUtils.create_lineup_from_performers(["John Doe", "Jane Smith"])
        assert [c.name for c in lineup] == ["John Doe", "Jane Smith"]

    def test_placeholder_strings_filtered(self):
        lineup = ShowFactoryUtils.create_lineup_from_performers(["TBA", "Special Guest", "John Doe"])
        assert len(lineup) == 1
        assert lineup[0].name == "John Doe"

    def test_all_placeholders_returns_empty(self):
        lineup = ShowFactoryUtils.create_lineup_from_performers(["TBA", "Surprise", "Various"])
        assert lineup == []

    def test_empty_input_returns_empty(self):
        assert ShowFactoryUtils.create_lineup_from_performers([]) == []

    def test_object_with_name_attr_filtered(self):
        class FakePerformer:
            def __init__(self, name):
                self.name = name

        lineup = ShowFactoryUtils.create_lineup_from_performers([
            FakePerformer("TBA"),
            FakePerformer("Bo Burnham"),
        ])
        assert len(lineup) == 1
        assert lineup[0].name == "Bo Burnham"

    def test_dict_performer_filtered(self):
        performers = [{"name": "Special Guest"}, {"name": "Dave Chappelle"}]
        lineup = ShowFactoryUtils.create_lineup_from_performers(performers)
        assert len(lineup) == 1
        assert lineup[0].name == "Dave Chappelle"

    def test_names_are_stripped(self):
        lineup = ShowFactoryUtils.create_lineup_from_performers(["  Amy Schumer  "])
        assert lineup[0].name == "Amy Schumer"

    def test_non_alphabetic_string_filtered(self):
        lineup = ShowFactoryUtils.create_lineup_from_performers(["---", "John Mulaney"])
        assert len(lineup) == 1
        assert lineup[0].name == "John Mulaney"


# ---------------------------------------------------------------------------
# _is_valid_lineup_name — "more" blocklist entry
# ---------------------------------------------------------------------------

class TestMoreBlocklisted:
    def test_more_rejected(self):
        assert _is_valid_lineup_name("more") is False

    def test_more_case_insensitive(self):
        assert _is_valid_lineup_name("More") is False

    def test_more_filtered_from_performers(self):
        lineup = ShowFactoryUtils.create_lineup_from_performers(["John Mulaney", "more"])
        assert len(lineup) == 1
        assert lineup[0].name == "John Mulaney"


# ---------------------------------------------------------------------------
# is_dj_set_show
# ---------------------------------------------------------------------------

class TestIsDjSetShow:
    @pytest.mark.parametrize("name", [
        "Triplet Threat with DJ Mariko: Lady Gaga, Charli XCX, Chappell Roan & more",
        "DJ Night at the Club",
        "Friday with DJ Steve",
        "dj set featuring various artists",
        "DJ",
    ])
    def test_dj_set_detected(self, name):
        assert is_dj_set_show(name) is True

    @pytest.mark.parametrize("name", [
        "John Mulaney Live",
        "Comedy Night with Special Guests",
        "Dave Chappelle: For What It's Worth",
        "The Daily Show Live",
        None,
        "",
    ])
    def test_non_dj_show_passes(self, name):
        assert is_dj_set_show(name) is False

    def test_adjacent_letters_not_matched(self):
        # "DJango" should not trigger — not a word boundary
        assert is_dj_set_show("DJango Unchained Comedy Show") is False
