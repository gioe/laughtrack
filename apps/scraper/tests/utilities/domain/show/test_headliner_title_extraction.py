"""Tests for narrow headliner extraction from show titles."""

import pytest

from laughtrack.utilities.domain.show.headliner import extract_explicit_headliner_from_title


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Matt Misci LIVE at Nicks 7/18", "Matt Misci"),
        ("Tim Bateman - Appearing at Clint's Comedy Club - August 7th and 8th", "Tim Bateman"),
        ("Chris Renois @ Shamrock Comedy Club", "Chris Renois"),
        ("Comedy Legend David Naster Returns to Clint's Comedy Club for One Night Only", "David Naster"),
        ("Zach Zimmermann Comedy", "Zach Zimmermann"),
        ("Garage Sale - Korey David Comedy Special", "Korey David"),
        ("JOEY VILLAGOMEZ Comedy Special", "Joey Villagomez"),
    ],
)
def test_extracts_explicit_headliner_shapes(title, expected):
    assert extract_explicit_headliner_from_title(title) == expected


@pytest.mark.parametrize(
    "title",
    [
        "Friday Night Comedy",
        "Live Stand-Up Comedy",
        "Laugh Track City - improv comedy show",
        "DRUNK ROMEO & JULIET",
        "A DRUNK CHRISTMAS CAROL",
        "ComedySportz",
        "Williamson Branch",
        "Christian Royce",
        "The Comedy Lottery (8:30PM)",
        "SPECIAL EVENT An Idiots Guide To Wine at Nick's 7/11",
        "Jukebox Heroes LIVE!",
        "The Malpass Brothers LIVE",
        "Playing with Matches Live Gameshow!",
        "RED ROOM COMEDY",
        "Saturday Early Show",
        "",
        None,
    ],
)
def test_rejects_generic_production_and_exact_name_titles(title):
    assert extract_explicit_headliner_from_title(title) is None
