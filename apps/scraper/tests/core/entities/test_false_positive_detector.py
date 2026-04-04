"""
Unit tests for laughtrack.core.entities.comedian.false_positive_detector.

Covers all detection criteria:
  1. Exact placeholder names
  2. Placeholder substrings (open mic / open-mic)
  3. Structural keywords (showcase, variety, improv, etc.)
  4. Decoration pattern (***)
  5. Pipe character in name
  6. Name length > 60
  7. Short name (length < 4)
  8. Real comedian names pass through (no false positive)
"""

import sys

from _entities_test_helpers import _load_module


_detector_mod = _load_module(
    "src/laughtrack/core/entities/comedian/false_positive_detector.py",
    "laughtrack.core.entities.comedian.false_positive_detector",
)
detect_false_positive = _detector_mod.detect_false_positive
PLACEHOLDER_NAMES = _detector_mod.PLACEHOLDER_NAMES
PLACEHOLDER_SUBSTRINGS = _detector_mod.PLACEHOLDER_SUBSTRINGS
STRUCTURAL_KEYWORDS = _detector_mod.STRUCTURAL_KEYWORDS


# ---------------------------------------------------------------------------
# Real comedian names — must NOT be flagged
# ---------------------------------------------------------------------------

class TestRealComedianNamesPassThrough:
    def test_common_two_word_name(self):
        assert detect_false_positive("Dave Chappelle") is None

    def test_common_first_name_only_long_enough(self):
        assert detect_false_positive("Wanda") is None

    def test_name_with_hyphen(self):
        assert detect_false_positive("Jo-Anne Smith") is None

    def test_name_with_apostrophe(self):
        assert detect_false_positive("O'Brien") is None

    def test_four_char_name(self):
        """Exactly 4 characters should pass (min is < 4)."""
        assert detect_false_positive("Coco") is None

    def test_sixty_char_name(self):
        """Exactly 60 characters should pass (max is > 60)."""
        name = "A" * 60
        assert detect_false_positive(name) is None

    def test_name_containing_show_as_substring_of_word(self):
        """'showcase' triggers but 'shown' does not contain a structural keyword."""
        assert detect_false_positive("Shown Mendes") is None


# ---------------------------------------------------------------------------
# Criterion 1: Placeholder exact names
# ---------------------------------------------------------------------------

class TestPlaceholderExactNames:
    def test_tba_exact(self):
        assert detect_false_positive("TBA") is not None

    def test_tba_lowercase(self):
        assert detect_false_positive("tba") is not None

    def test_tbd_exact(self):
        assert detect_false_positive("TBD") is not None

    def test_special_guest(self):
        assert detect_false_positive("Special Guest") is not None

    def test_special_guest_lowercase(self):
        assert detect_false_positive("special guest") is not None

    def test_headliner(self):
        assert detect_false_positive("Headliner") is not None

    def test_mc(self):
        assert detect_false_positive("MC") is not None

    def test_mc_lowercase(self):
        assert detect_false_positive("mc") is not None

    def test_guest(self):
        assert detect_false_positive("Guest") is not None

    def test_host(self):
        assert detect_false_positive("Host") is not None

    def test_emcee(self):
        assert detect_false_positive("Emcee") is not None

    def test_reason_contains_placeholder_name(self):
        reason = detect_false_positive("TBA")
        assert reason is not None
        assert "placeholder_name" in reason

    def test_whitespace_stripped_before_check(self):
        assert detect_false_positive("  TBA  ") is not None

    def test_all_placeholder_names_detected(self):
        """Every entry in PLACEHOLDER_NAMES must be detected."""
        for name in PLACEHOLDER_NAMES:
            result = detect_false_positive(name)
            assert result is not None, f"Expected '{name}' to be a false positive"


# ---------------------------------------------------------------------------
# Criterion 2: Placeholder substrings (open mic / open-mic)
# ---------------------------------------------------------------------------

class TestPlaceholderSubstrings:
    def test_open_mic_exact(self):
        assert detect_false_positive("open mic") is not None

    def test_open_mic_in_longer_name(self):
        assert detect_false_positive("KRACKPOTS Open Mic Night") is not None

    def test_open_mic_hyphenated(self):
        assert detect_false_positive("open-mic") is not None

    def test_open_mic_hyphenated_in_longer_name(self):
        assert detect_false_positive("Wednesday Open-Mic Show") is not None

    def test_reason_contains_placeholder_substring(self):
        reason = detect_false_positive("Tuesday Open Mic")
        assert reason is not None
        assert "placeholder_substring" in reason

    def test_all_substrings_detected(self):
        for sub in PLACEHOLDER_SUBSTRINGS:
            result = detect_false_positive(f"Comedy {sub} night")
            assert result is not None, f"Expected name containing '{sub}' to be a false positive"


# ---------------------------------------------------------------------------
# Criterion 3: Structural keywords
# ---------------------------------------------------------------------------

class TestStructuralKeywords:
    def test_showcase(self):
        assert detect_false_positive("Comedy Showcase") is not None

    def test_variety(self):
        assert detect_false_positive("Variety Night") is not None

    def test_improv(self):
        assert detect_false_positive("Improv Show") is not None

    def test_trivia(self):
        assert detect_false_positive("Comedy Trivia") is not None

    def test_graduation(self):
        assert detect_false_positive("Graduation Show") is not None

    def test_theater(self):
        assert detect_false_positive("Comedy Theater") is not None

    def test_theatre(self):
        assert detect_false_positive("Upright Citizens Theatre") is not None

    def test_burlesque(self):
        assert detect_false_positive("Burlesque Night") is not None

    def test_festival(self):
        assert detect_false_positive("Comedy Festival") is not None

    def test_reason_contains_structural_keyword(self):
        reason = detect_false_positive("Comedy Showcase")
        assert reason is not None
        assert "structural_keyword" in reason

    def test_all_structural_keywords_detected(self):
        for kw in STRUCTURAL_KEYWORDS:
            result = detect_false_positive(f"NYC {kw}")
            assert result is not None, f"Expected name containing '{kw}' to be a false positive"


# ---------------------------------------------------------------------------
# Criterion 4: Decoration pattern (***)
# ---------------------------------------------------------------------------

class TestDecorationPattern:
    def test_triple_star_exact(self):
        assert detect_false_positive("***") is not None

    def test_triple_star_in_longer_name(self):
        assert detect_false_positive("*** Special Event ***") is not None

    def test_reason_contains_decoration_pattern(self):
        reason = detect_false_positive("***Comedy Night***")
        assert reason is not None
        assert "decoration_pattern" in reason

    def test_double_star_not_flagged(self):
        """Only '***' (triple) is a decoration pattern — not '**'."""
        assert detect_false_positive("Jane**Doe") is None


# ---------------------------------------------------------------------------
# Criterion 5: Pipe character
# ---------------------------------------------------------------------------

class TestPipeCharacter:
    def test_pipe_exact(self):
        assert detect_false_positive("Comedy | Improv") is not None

    def test_pipe_alone(self):
        assert detect_false_positive("|") is not None

    def test_reason_contains_pipe_in_name(self):
        reason = detect_false_positive("Jane | Doe")
        assert reason is not None
        assert "pipe_in_name" in reason


# ---------------------------------------------------------------------------
# Criterion 6: Length > 60
# ---------------------------------------------------------------------------

class TestLengthGt60:
    def test_sixty_one_chars_flagged(self):
        name = "A" * 61
        assert detect_false_positive(name) is not None

    def test_sixty_chars_pass(self):
        name = "A" * 60
        assert detect_false_positive(name) is None

    def test_reason_contains_length_gt_60(self):
        reason = detect_false_positive("A" * 61)
        assert reason is not None
        assert "length_gt_60" in reason


# ---------------------------------------------------------------------------
# Criterion 7: Short name (length < 4)
# ---------------------------------------------------------------------------

class TestShortName:
    def test_three_char_name_flagged(self):
        assert detect_false_positive("TBA") is not None  # also a placeholder

    def test_three_char_non_placeholder_flagged(self):
        """A 3-char name that isn't a placeholder should still be flagged as short."""
        assert detect_false_positive("Xyz") is not None

    def test_two_char_name_flagged(self):
        assert detect_false_positive("Al") is not None

    def test_single_char_flagged(self):
        assert detect_false_positive("A") is not None

    def test_empty_string_flagged(self):
        assert detect_false_positive("") is not None

    def test_reason_contains_short_name(self):
        reason = detect_false_positive("Al")
        assert reason is not None
        assert "short_name" in reason
