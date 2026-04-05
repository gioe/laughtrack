"""Tests for the multi-comedian name splitter."""

import pytest

from laughtrack.core.entities.comedian.name_splitter import split_combined_name


class TestSplitCombinedName:
    """Test split_combined_name with various multi-comedian patterns."""

    # --- AND pattern: "X & Y", "X and Y" ---

    def test_ampersand_two_names(self):
        assert split_combined_name("Kiki Yeung & Esther Ku") == ["Kiki Yeung", "Esther Ku"]

    def test_and_word_two_names(self):
        assert split_combined_name("Landon Bryant and Mary Ryan Brown") == [
            "Landon Bryant",
            "Mary Ryan Brown",
        ]

    def test_ampersand_three_names_with_comma(self):
        result = split_combined_name("Heather Pasternak, Phil Medina & Jason Schuster")
        assert result == ["Heather Pasternak", "Phil Medina", "Jason Schuster"]

    def test_ampersand_event_title_not_split(self):
        """Event titles with & should NOT be split."""
        assert split_combined_name("Cocktails & Comedy") == ["Cocktails & Comedy"]

    def test_ampersand_drag_brunch_not_split(self):
        assert split_combined_name("Sashay & Slay Drag Brunch") == [
            "Sashay & Slay Drag Brunch"
        ]

    def test_and_event_noise_not_split(self):
        assert split_combined_name("Laughs and Vibes Comedy") == ["Laughs and Vibes Comedy"]

    # --- WITH pattern: "X with Y", "X Featuring Y", etc. ---

    def test_with_two_names(self):
        assert split_combined_name("Brent Terhune with Eli Wilz") == [
            "Brent Terhune",
            "Eli Wilz",
        ]

    def test_with_special_guest(self):
        assert split_combined_name("Joe Gorga with Special Guest Frank Catania") == [
            "Joe Gorga",
            "Frank Catania",
        ]

    def test_featuring_two_names(self):
        assert split_combined_name("AJ Finney Featuring Samara Suomi") == [
            "AJ Finney",
            "Samara Suomi",
        ]

    def test_ft_dot(self):
        assert split_combined_name("Mike Lester ft. Lily Meyer") == [
            "Mike Lester",
            "Lily Meyer",
        ]

    def test_w_slash_two_names(self):
        assert split_combined_name("Jon Bramnick w/ Vinnie Brand") == [
            "Jon Bramnick",
            "Vinnie Brand",
        ]

    def test_with_event_noise_not_split(self):
        """'with' followed by non-name text should not split."""
        assert split_combined_name("Comedy Madness with Michael Quu") == [
            "Comedy Madness with Michael Quu"
        ]

    # --- SLASH pattern: "X / Y" ---

    def test_slash_two_names(self):
        assert split_combined_name("Dave Herrero / Pete Galanis") == [
            "Dave Herrero",
            "Pete Galanis",
        ]

    def test_slash_url_not_split(self):
        assert split_combined_name("http://example.com/path") == [
            "http://example.com/path"
        ]

    # --- No split cases ---

    def test_single_name_unchanged(self):
        assert split_combined_name("Dave Chappelle") == ["Dave Chappelle"]

    def test_name_with_trailing_bang(self):
        result = split_combined_name("Jon Bramnick with Vinnie Brand!")
        assert result == ["Jon Bramnick", "Vinnie Brand"]

    def test_empty_string(self):
        assert split_combined_name("") == [""]

    def test_whitespace_preserved_for_single(self):
        assert split_combined_name("  Dave Chappelle  ") == ["Dave Chappelle"]
