"""Unit tests for discover-nearby's duplicate classification, focused on the
street-address match arm added so venues already onboarded under a name variant
and/or with a NULL google_place_id aren't re-surfaced as "new".

bin/discover-nearby has no .py extension, so it's loaded via SourceFileLoader.
The tests are hermetic — they build in-memory name_rows / addr_index and never
touch the database.
"""
import importlib.util
import types
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRAPER_ROOT = Path(__file__).resolve().parents[3]
_loader = SourceFileLoader("discover_nearby", str(SCRAPER_ROOT / "bin" / "discover-nearby"))
_spec = importlib.util.spec_from_loader("discover_nearby", _loader)
dn = importlib.util.module_from_spec(_spec)
_loader.exec_module(dn)


def venue(name, address, place_id="PID_NEW", lat=34.1466, lng=-118.1307):
    return types.SimpleNamespace(name=name, address=address, place_id=place_id, lat=lat, lng=lng)


@pytest.mark.parametrize(
    "a, b",
    [
        ("24 N Mentor Ave, Pasadena, CA 91106, USA", "24 N Mentor Ave"),
        ("1215 Baker St Unit C, Costa Mesa, CA 92626, USA", "1215 Baker Street"),
        ("777 San Manuel Blvd S, Highland, CA 92346, USA", "777 San Manuel Blvd."),
        ("45000 Pechanga Pkwy, Temecula, CA 92592, USA", "45000 Pechanga Parkway"),
        ("300 E Ocean Blvd #300, Long Beach, CA 90802, USA", "300 E Ocean BL, Long Beach, CA"),
    ],
)
def test_normalize_address_collapses_format_variants(a, b):
    assert dn._normalize_address(a) == dn._normalize_address(b)


def test_normalize_address_requires_street_number():
    # No leading number -> too weak to match on.
    assert dn._normalize_address("Corona, CA 92883, USA") is None
    assert dn._normalize_address("") is None
    assert dn._normalize_address(None) is None


def test_address_match_catches_name_variant_with_null_placeid_and_coords():
    # Existing club: different name, NULL place_id, NULL coords (the exact gap).
    addr_index = {"24 mentor": [(167, "Ice House Comedy Club", None, None)]}
    v = venue("The Ice House", "24 N Mentor Ave, Pasadena, CA 91106, USA", place_id="PID_X")
    status, club_id, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[], name_match_miles=2.0, addr_index=addr_index
    )
    assert (status, club_id) == ("likely", 167)


def test_address_match_proximity_guard_rejects_same_number_in_another_city():
    # Same street key but the existing club has real coords ~3 mi away -> not a dup.
    addr_index = {"100 main": [(9, "Main St Theater (Other City)", 34.20, -118.20)]}
    v = venue("Some Venue", "100 Main St, Elsewhere, CA 90000, USA", lat=34.10, lng=-118.10)
    status, _, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[], name_match_miles=2.0, addr_index=addr_index
    )
    assert status == "new"


def test_place_id_match_takes_precedence_as_known():
    v = venue("Whatever", "24 N Mentor Ave", place_id="PID_KNOWN")
    status, club_id, _ = dn._classify(
        v, None, by_place_id={"PID_KNOWN": (167, "Ice House Comedy Club")},
        name_rows=[], name_match_miles=2.0, addr_index={},
    )
    assert (status, club_id) == ("known", 167)


def test_truly_new_venue_stays_new():
    v = venue("Brand New Room", "99999 Nowhere Rd, Nowhere, CA 90000, USA", place_id="PID_NEW")
    status, _, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[],
        name_match_miles=2.0, addr_index={"24 mentor": [(167, "Ice House Comedy Club", None, None)]},
    )
    assert status == "new"
