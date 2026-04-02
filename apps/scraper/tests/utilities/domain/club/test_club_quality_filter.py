"""Tests for the club quality filter (junk-venue rejection)."""

import pytest
from unittest.mock import patch

import laughtrack.utilities.domain.club.quality_filter as _filter_mod
from laughtrack.utilities.domain.club.quality_filter import is_junk_venue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_RULES = {
    "name_prefix_deny": ["Event #", "Test ", "Demo "],
    "website_deny_exact": ["#", ""],
    "website_hostname_deny": {
        "exact": ["testcenter.seatengine.com", "developmenttestsite.seatengine.com"],
        "glob": ["demo-*.seatengine.com"],
    },
}


@pytest.fixture(autouse=True)
def patch_rules():
    """Pin _RULES to the canonical test ruleset so file I/O is irrelevant."""
    with patch.object(_filter_mod, "_RULES", _GOOD_RULES):
        yield


# ---------------------------------------------------------------------------
# Name-prefix rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "Demo - Austin Comedy House",
        "Event #123",
        "Test Venue",
        "Demo Comedy Club",
    ],
)
def test_name_prefix_rejection(name):
    assert is_junk_venue(name, "https://legit.com") is True


def test_name_prefix_partial_match_is_not_rejected():
    # "Comedy Demo - Showcase" does NOT start with a denied prefix
    assert is_junk_venue("Comedy Demo - Showcase", "https://legit.com") is False


# ---------------------------------------------------------------------------
# Website exact-value rejection
# ---------------------------------------------------------------------------


def test_website_hash_rejected():
    assert is_junk_venue("Good Club", "#") is True


def test_website_empty_string_rejected():
    assert is_junk_venue("Good Club", "") is True


def test_website_whitespace_only_rejected():
    # Whitespace-only normalises to empty string
    assert is_junk_venue("Good Club", "   ") is True


# ---------------------------------------------------------------------------
# Website hostname rejection
# ---------------------------------------------------------------------------


def test_exact_hostname_testcenter_rejected():
    assert is_junk_venue("Good Club", "https://testcenter.seatengine.com/venue/1") is True


def test_exact_hostname_developmenttestsite_rejected():
    assert is_junk_venue("Good Club", "https://developmenttestsite.seatengine.com") is True


def test_glob_hostname_demo_prefix_rejected():
    assert is_junk_venue("Good Club", "https://demo-acme.seatengine.com/shows") is True


def test_glob_hostname_another_demo_rejected():
    assert is_junk_venue("Good Club", "https://demo-12345.seatengine.com") is True


# ---------------------------------------------------------------------------
# Legitimate venues pass through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,website",
    [
        ("McGuire's Comedy Club", "https://mcguires.seatengine.com"),
        ("Laugh Factory", "https://www.laughfactory.com"),
        ("The Comedy Store", "https://thecomedystore.com"),
        ("Event Horizon Improv", "https://eventhorizon.com"),  # name doesn't start with "Event #"
        ("Testing Grounds Comedy", "https://legit.com"),       # doesn't start with "Test "
    ],
)
def test_legitimate_venue_passes(name, website):
    assert is_junk_venue(name, website) is False


# ---------------------------------------------------------------------------
# Warning is logged on rejection
# ---------------------------------------------------------------------------


def test_rejection_emits_warning():
    """Rejected venue calls Logger.warn with the club name and matched rule."""
    with patch.object(_filter_mod.Logger, "warn") as mock_warn:
        result = is_junk_venue("Demo - My Venue", "https://legit.com")
    assert result is True
    mock_warn.assert_called_once()
    call_msg = mock_warn.call_args[0][0]
    assert "Demo - My Venue" in call_msg
    assert "Demo " in call_msg  # matched prefix reported in message
