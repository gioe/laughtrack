"""Unit tests for is_comedy_event (TASK-2952).

The helper is the positive-allowlist counterpart to the eventbrite Music-category
filter, used by mixed-use venues (music bars, jazz clubs) that opt into comedy
filtering on platforms (Tockify, Wix Events) whose APIs expose no genre field.
"""

import pytest

from laughtrack.utilities.domain.show.factory import is_comedy_event


@pytest.mark.parametrize(
    "text",
    [
        "Bear City Comedy",
        "After Comedy Happy Hour",
        "Cool Jazz (front room) Comedy (back patio)",
        "Stand-Up Showcase",
        "Stand Up Saturday",
        "standup open mic",
        "Open Mic Night",
        "open-mic comedy",
        "Improv Jam",
        "Sketch Revue",
        "Comedian Spotlight",
        "Two Comedians, One Mic",
        "The Roast of Someone",
        "tonight: COMEDY",
    ],
)
def test_matches_comedy_titles(text):
    assert is_comedy_event(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "R&B Night",
        "Karaoke Tuesdays",
        "Club Disintegration (Darkwave)",
        "Jazz Jam",
        "Cool Jazz",
        "Latin Vibe",
        "Live Band Emo Night",
        "Rick Berthod",
        "comically large prop night",  # word-boundary: 'comically' is not 'comic'
        "",
        None,
    ],
)
def test_rejects_non_comedy(text):
    assert is_comedy_event(text) is False


def test_matches_if_any_field_signals_comedy():
    """A neutral title is rescued by a comedy keyword in a later field (tag/description)."""
    assert is_comedy_event("Friday Lineup", "long-beach", "comedy") is True
    assert is_comedy_event("Tonight at Que", "A night of stand-up.") is True


def test_rejects_when_no_field_signals_comedy():
    assert is_comedy_event("Live Bands", "band-night", "live music") is False


def test_no_args_is_false():
    assert is_comedy_event() is False
