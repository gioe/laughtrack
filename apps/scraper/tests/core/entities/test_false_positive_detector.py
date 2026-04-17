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
  8. Starts with a quote (straight or smart)
  9. Starts with a digit
 10. Starts with an '@'

Plus cross-cutting checks that real comedian names pass through.
"""

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

    def test_fest_abbreviation(self):
        assert detect_false_positive("Desi Comedy Fest") is not None

    def test_hypnosis(self):
        assert detect_false_positive("An unbelievable comedy hypnosis event like no other!") is not None

    def test_wrestling(self):
        assert detect_false_positive("Championship Wrestling") is not None

    def test_hosted_by(self):
        assert detect_false_positive("Body Count hosted by Tessa Belle") is not None

    def test_auditions(self):
        assert detect_false_positive("Sabina Meschke present TRIPLET AUDITIONS") is not None

    def test_lounge(self):
        assert detect_false_positive("Ladies Laugh Lounge") is not None

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
        reason = detect_false_positive("***Super Stars***")
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


# ---------------------------------------------------------------------------
# New structural keywords — venue types, show formats, promotional patterns
# ---------------------------------------------------------------------------

class TestVenueTypeKeywords:
    def test_brewery(self):
        assert detect_false_positive("Cricket Hill Brewery") is not None

    def test_winery(self):
        assert detect_false_positive("Grace Winery") is not None

    def test_vineyard(self):
        assert detect_false_positive("Paradocx Vineyard") is not None

    def test_distillery(self):
        assert detect_false_positive("Pine Tavern Distillery") is not None

    def test_tavern(self):
        assert detect_false_positive("Poppy's Tavern") is not None


class TestShowFormatKeywords:
    def test_comedy_competition(self):
        assert detect_false_positive("Roosters New Talent Comedy Competition") is not None

    def test_comedy_camp(self):
        assert detect_false_positive("Spring Comedy Camp") is not None

    def test_comedy_academy(self):
        assert detect_false_positive("Cap City Comedy Academy") is not None

    def test_roast_battle(self):
        assert detect_false_positive("Battle of the Sexes: A roast battle") is not None

    def test_game_show(self):
        assert detect_false_positive("Friendly Feud Game Show") is not None

    def test_gameshow(self):
        assert detect_false_positive("Get It?! Gameshow") is not None

    def test_drag_show(self):
        assert detect_false_positive("Drag Show Live") is not None

    def test_drag_queen_bingo_caught_by_bingo(self):
        assert detect_false_positive("Drag Queen Bingo!") is not None

    def test_bob_the_drag_queen_passes(self):
        """Real comedian — RuPaul's Drag Race winner."""
        assert detect_false_positive("Bob the Drag Queen") is None

    def test_all_stars(self):
        assert detect_false_positive("Austin All Stars") is not None

    def test_allstars(self):
        assert detect_false_positive("Comedy Allstars") is not None

    def test_piano_show(self):
        assert detect_false_positive("Dueling Piano Show") is not None

    def test_bingo(self):
        assert detect_false_positive("Bingorama") is not None

    def test_karaoke(self):
        assert detect_false_positive("Live Band Karaoke") is not None

    def test_open_jam(self):
        assert detect_false_positive("Sunday Open Jam") is not None

    def test_day_party(self):
        assert detect_false_positive("Last Saturdaze Day Party") is not None

    def test_private_event(self):
        assert detect_false_positive("Closed for Private Event") is not None

    def test_closed_for(self):
        assert detect_false_positive("Closed for Easter") is not None

    def test_talent_show(self):
        assert detect_false_positive("Emerging Talent Show") is not None

    def test_semi_finals(self):
        assert detect_false_positive("SoCal's Funniest Comic - Semi-Finals") is not None

    def test_prelim_round(self):
        assert detect_false_positive("Comedy Competition - Prelim Round 4") is not None

    def test_live_in_naples(self):
        assert detect_false_positive("Comedian Chris D'Elia Live in Naples, Florida!") is not None

    def test_special_event(self):
        assert detect_false_positive("ANTHONY RODIA - SPECIAL EVENT - 4/3 - 4/4") is not None

    def test_special_event_with_date(self):
        assert detect_false_positive("DAVE ATTELL - SPECIAL EVENT  - SATURDAY, JULY 11TH @ 7:00PM") is not None


class TestNewPlaceholderNames:
    def test_talent(self):
        assert detect_false_positive("Talent") is not None

    def test_test_talent(self):
        assert detect_false_positive("Test Talent") is not None

    def test_unknown_artist(self):
        assert detect_false_positive("Unknown Artist") is not None

    def test_free_show(self):
        assert detect_false_positive("Free Show") is not None

    def test_fourth_of_july(self):
        assert detect_false_positive("Fourth of July") is not None

    def test_half(self):
        assert detect_false_positive("Half") is not None


class TestRealNamesStillPass:
    """Ensure new rules don't create false negatives on real comedians."""

    def test_ali_tavern_not_flagged(self):
        """'Ali' contains no structural keyword — short name rule catches < 4."""
        assert detect_false_positive("Ali Wong") is None

    def test_nate_bargatze(self):
        assert detect_false_positive("Nate Bargatze") is None

    def test_taylor_tomlinson(self):
        assert detect_false_positive("Taylor Tomlinson") is None

    def test_matt_rife(self):
        assert detect_false_positive("Matt Rife") is None

    def test_shane_gillis(self):
        assert detect_false_positive("Shane Gillis") is None


# ---------------------------------------------------------------------------
# Criterion 8: Starts with quote
# ---------------------------------------------------------------------------

class TestStartsWithQuote:
    def test_leading_double_quote_flagged(self):
        assert detect_false_positive('"Big Irish" Jay Hollingsworth') is not None

    def test_leading_double_quote_reason(self):
        reason = detect_false_positive('"Big Irish" Jay Hollingsworth')
        assert reason == "starts_with_quote"

    def test_leading_single_quote_flagged(self):
        assert detect_false_positive("'The Kid' Johnson") is not None

    def test_leading_smart_double_open_quote_flagged(self):
        assert detect_false_positive("\u201cThat One Mailman\u201d Sean Fogelson") is not None

    def test_leading_smart_single_open_quote_flagged(self):
        assert detect_false_positive("\u2018Ace\u2019 Williams") is not None

    def test_interior_quote_not_flagged(self):
        """Dwayne 'The Rock' Johnson style — quote in middle is fine."""
        assert detect_false_positive("Dwayne \"The Rock\" Johnson") is None

    def test_apostrophe_in_name_still_passes(self):
        """O'Brien has an apostrophe but it is not leading — must not be flagged."""
        assert detect_false_positive("O'Brien") is None


# ---------------------------------------------------------------------------
# Criterion 9: Starts with digit
# ---------------------------------------------------------------------------

class TestStartsWithDigit:
    def test_leading_digit_flagged(self):
        assert detect_false_positive("2 Munchie Minimum") is not None

    def test_leading_digit_reason(self):
        reason = detect_false_positive("20 Ride")
        assert reason == "starts_with_digit"

    def test_three_digit_prefix_flagged(self):
        assert detect_false_positive("404 Blac") is not None

    def test_ordinal_prefix_flagged(self):
        assert detect_false_positive("5th ANNUAL HIGH AND MIGHTY 420 MEGA SESH") is not None

    def test_title_with_digit_and_colon_flagged(self):
        assert detect_false_positive("90 Day Fiance: Sarper Guven") is not None


# ---------------------------------------------------------------------------
# Criterion 10: Starts with @
# ---------------------------------------------------------------------------

class TestStartsWithAtSign:
    def test_at_sign_prefix_flagged(self):
        assert detect_false_positive("@ComedyTrend with John Campanelli") is not None

    def test_at_sign_prefix_reason(self):
        reason = detect_false_positive("@SomeHandle")
        assert reason == "starts_with_at_sign"

    def test_interior_at_not_flagged(self):
        """A '@' inside the name (e.g. email-ish artifact) isn't caught here — other
        rules handle that. This test documents the surface-area of the check."""
        assert detect_false_positive("John @ Comedy Club") is None


# ---------------------------------------------------------------------------
# Regression fixture — the exact false-positive names from TASK-1547
# ---------------------------------------------------------------------------
#
# Only the names matching the new prefix rules (quote / digit / @) are asserted
# here. 'A DREAMSCAPE' and 'A Laugh Supreme' reach the DB via ingestion paths
# where ComedianUtils.normalize_name() title-cases fully-upper input, so the
# detector can't reliably distinguish those from real comedians imported in
# caps (e.g. 'CLARE BOWEN'). Those are handled by direct deny-list cleanup.

TASK_1547_FALSE_POSITIVES = (
    '"Big Irish" Jay Hollingsworth',
    '"That One Mailman" Sean Fogelson',
    "2 Munchie Minimum",
    "20 Ride",
    "404 Blac",
    "5th ANNUAL HIGH AND MIGHTY 420 MEGA SESH",
    "90 Day Fiance: Sarper Guven",
    "@ComedyTrend with John Campanelli",
)


class TestTask1547RegressionFixture:
    """Every prefix-pattern leak from the original bug report must be rejected."""

    def test_all_known_false_positives_detected(self):
        for name in TASK_1547_FALSE_POSITIVES:
            reason = detect_false_positive(name)
            assert reason is not None, (
                f"Expected {name!r} to be flagged as a false positive"
            )
