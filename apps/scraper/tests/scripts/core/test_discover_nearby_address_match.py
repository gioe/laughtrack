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


def venue(
    name,
    address,
    place_id="PID_NEW",
    lat=34.1466,
    lng=-118.1307,
    primary_type="comedy_club",
):
    return types.SimpleNamespace(
        name=name,
        address=address,
        place_id=place_id,
        lat=lat,
        lng=lng,
        primary_type=primary_type,
    )


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


def _addr_row(club_id, name, lat, lng, state, club_type="club", visible=True, status="active"):
    """Build an addr_index entry matching _load_existing_clubs' shape:
    (id, name, lat, lng, club_type, visible, status, state)."""
    return (club_id, name, lat, lng, club_type, visible, status, state)


def test_address_state_parses_comma_formatted_address():
    assert dn._address_state("17105 N Outer 40 Rd, Chesterfield, MO 63005, USA") == "mo"
    assert dn._address_state("24 N Mentor Ave, Pasadena, CA 91106, USA") == "ca"
    # Too few segments to be confident -> None (disables the fallback).
    assert dn._address_state("17105 North Outer 40 Road") is None
    assert dn._address_state("Chesterfield, MO") is None
    assert dn._address_state("") is None
    assert dn._address_state(None) is None


def test_stale_coord_address_match_catches_same_state_metro_dup():
    # TASK-3322 regression: "The Factory" — existing club 4945 has a stale stored
    # geocode (38.6565,-90.4542) ~6 mi from the candidate's real Chesterfield
    # rooftop, so the tight proximity gate rejected the exact "17105 outer" key
    # match and it was kept as "new" (at risk of a duplicate club shell). Same
    # state + within the wider metro bound now catches it as a dup.
    addr_index = {"17105 outer": [_addr_row(4945, "The Factory", 38.6565, -90.4542, "mo")]}
    v = venue(
        "The Factory",
        "17105 N Outer 40 Rd, Chesterfield, MO 63005, USA",
        place_id="PID_FACTORY",
        lat=38.658,
        lng=-90.564,
    )
    status, club_id, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[], name_match_miles=2.0, addr_index=addr_index
    )
    assert (status, club_id) == ("likely", 4945)


def test_stale_coord_fallback_rejects_same_state_distant_city():
    # Same key + same state but ~70 mi apart (beyond the metro bound) -> a
    # genuinely different city sharing a common street number, not a stale dup.
    addr_index = {"100 main": [_addr_row(11, "Main St MO", 38.6, -90.4, "mo")]}
    v = venue("Other Main", "100 Main St, FarTown, MO 65000, USA", lat=38.0, lng=-91.5)
    status, _, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[], name_match_miles=2.0, addr_index=addr_index
    )
    assert status == "new"


def test_stale_coord_fallback_rejects_cross_state_same_key():
    # Same key, coords disagree, and the states differ -> not a dup even though
    # the street key collides.
    addr_index = {"100 main": [_addr_row(12, "Main St CA", 34.20, -118.20, "ca")]}
    v = venue("Some Venue", "100 Main St, Elsewhere, NY 10000, USA", lat=40.0, lng=-74.0)
    status, _, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[], name_match_miles=2.0, addr_index=addr_index
    )
    assert status == "new"


def test_stale_coord_fallback_skipped_when_state_unknown():
    # An addr_index row without a state tail (legacy/hand-built) must not qualify
    # for the fallback — coords disagree past the tight bound -> stays "new".
    addr_index = {"100 main": [(9, "Main St Theater", 34.20, -118.20)]}
    v = venue("Some Venue", "100 Main St, Elsewhere, CA 90000, USA", lat=34.10, lng=-118.10)
    status, _, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[], name_match_miles=2.0, addr_index=addr_index
    )
    assert status == "new"


def test_place_id_match_takes_precedence_as_known():
    v = venue("Whatever", "24 N Mentor Ave", place_id="PID_KNOWN")
    result = dn._classify(
        v, None, by_place_id={"PID_KNOWN": (167, "Ice House Comedy Club", "club", True, "active")},
        name_rows=[], name_match_miles=2.0, addr_index={},
    )
    assert (result.status, result.club_id, result.category_state) == ("known", 167, "club")


def test_hidden_active_known_place_id_preserves_category_state():
    v = venue("Hidden Music Room", "101 Music Ave", place_id="PID_HIDDEN")
    result = dn._classify(
        v,
        None,
        by_place_id={"PID_HIDDEN": (901, "Hidden Music Room", "non_comedy", False, "active")},
        name_rows=[],
        name_match_miles=2.0,
        addr_index={},
    )

    assert (result.status, result.club_id) == ("known", 901)
    assert result.category_state == "hidden_active:non_comedy"


def test_denied_place_id_preserves_deny_list_evidence():
    v = venue("Music Hall", "101 Music Ave", place_id="PID_DENIED", primary_type="live_music_venue")
    result = dn._classify(
        v,
        None,
        by_place_id={},
        name_rows=[],
        name_match_miles=2.0,
        denied_venues={
            "PID_DENIED": {
                "name": "Music Hall",
                "reason": "music only",
                "google_primary_type": "live_music_venue",
                "evidence": {"calendar": "music"},
            }
        },
        addr_index={},
    )

    assert result.status == "denied"
    assert result.category_state == "denied:live_music_venue"
    assert result.deny_reason == "music only"
    assert result.deny_evidence == {"calendar": "music"}


def _name_row(club_id, club_name, lat, lng, club_type="club", visible=True, status="active"):
    """Build a name_rows entry: (id, name, normalized_name, lat, lng, *meta)."""
    return (club_id, club_name, dn._normalize_name(club_name), lat, lng, club_type, visible, status)


# Foxwoods coords — the Great Cedar Showroom regression case (TASK-3170).
_FOXWOODS = (41.4742, -71.9601)


def test_name_token_subset_catches_longer_stored_variant():
    # Existing club stored under a longer name variant, with a NULL place_id —
    # exactly the Great Cedar Showroom gap (re-proposed as "new" because the
    # discovery name is a strict prefix/subset of the stored name).
    name_rows = [
        _name_row(4642, "Great Cedar Showroom at Foxwoods Resort Casino", *_FOXWOODS),
    ]
    v = venue("Great Cedar Showroom", "350 Trolley Line Blvd, Mashantucket, CT",
              place_id="PID_NEW", lat=_FOXWOODS[0], lng=_FOXWOODS[1])
    result = dn._classify(
        v, None, by_place_id={}, name_rows=name_rows, name_match_miles=2.0, addr_index={}
    )
    assert (result.status, result.club_id) == ("likely", 4642)


def test_name_token_subset_requires_proximity():
    # Same name-subset relationship but the stored club is far away -> not a dup
    # (guards against collapsing same-named venues in different cities).
    name_rows = [_name_row(50, "Great Cedar Showroom at Foxwoods Resort Casino", 34.05, -118.25)]
    v = venue("Great Cedar Showroom", "1 Somewhere St, Los Angeles, CA",
              place_id="PID_NEW", lat=_FOXWOODS[0], lng=_FOXWOODS[1])
    result = dn._classify(
        v, None, by_place_id={}, name_rows=name_rows, name_match_miles=2.0, addr_index={}
    )
    assert result.status == "new"


def test_single_generic_token_overlap_does_not_collapse():
    # A lone shared generic word must NOT collapse distinct venues, even nearby.
    name_rows = [_name_row(60, "Brea Improv Comedy Club", *_FOXWOODS)]
    v = venue("Comedy", "1 Main St, Mashantucket, CT",
              place_id="PID_NEW", lat=_FOXWOODS[0], lng=_FOXWOODS[1])
    result = dn._classify(
        v, None, by_place_id={}, name_rows=name_rows, name_match_miles=2.0, addr_index={}
    )
    assert result.status == "new"


def test_name_token_helpers_drop_stopwords():
    assert dn._name_tokens("Great Cedar Showroom at Foxwoods Resort Casino") == frozenset(
        {"great", "cedar", "showroom", "foxwoods", "resort", "casino"}
    )
    assert dn._is_name_token_subset(
        frozenset({"great", "cedar", "showroom"}),
        frozenset({"great", "cedar", "showroom", "foxwoods", "resort", "casino"}),
    )
    # single-token subset is rejected (>= 2 meaningful tokens required)
    assert not dn._is_name_token_subset(frozenset({"comedy"}), frozenset({"comedy", "club"}))


def test_truly_new_venue_stays_new():
    v = venue("Brand New Room", "99999 Nowhere Rd, Nowhere, CA 90000, USA", place_id="PID_NEW")
    status, _, _ = dn._classify(
        v, None, by_place_id={}, name_rows=[],
        name_match_miles=2.0, addr_index={"24 mentor": [(167, "Ice House Comedy Club", None, None)]},
    )
    assert status == "new"


def test_table_render_includes_category_state(capsys):
    dn._render(
        [
            {
                "status": "known",
                "name": "Hidden Music Room",
                "distance_mi": 1.2,
                "address": "101 Music Ave",
                "website": None,
                "primary_type": "live_music_venue",
                "category_state": "hidden_active:non_comedy",
                "place_id": "PID_HIDDEN",
                "matched_club_id": 901,
                "matched_club_name": "Hidden Music Room",
                "deny_reason": None,
                "deny_google_primary_type": None,
                "deny_evidence": None,
            }
        ],
        "table",
    )

    assert "hidden_active:non_comedy" in capsys.readouterr().out
