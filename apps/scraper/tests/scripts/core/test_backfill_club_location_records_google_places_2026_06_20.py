"""Tests for TASK-3027 Google Places club-location cleanup helpers."""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for p in (str(_src_path), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.archive import backfill_club_location_records_google_places_2026_06_20 as mod  # noqa: E402


def _row(**kwargs) -> mod.ClubCandidate:
    base = dict(
        id=1,
        name="Example Club",
        address="",
        city=None,
        state=None,
        country=None,
        website="",
        visible=True,
        status="active",
        club_type="club",
        google_place_id=None,
        latitude=None,
        longitude=None,
        shows_count=0,
        scraping_sources_count=0,
        enabled_sources_count=0,
        production_company_mappings=0,
        favorites_count=0,
    )
    base.update(kwargs)
    return mod.ClubCandidate(**base)


def test_incomplete_address_detects_blank_and_city_state_only_values():
    assert mod.is_incomplete_address("")
    assert mod.is_incomplete_address("   ")
    assert mod.is_incomplete_address("Denver, CO")
    assert mod.is_incomplete_address("One MGM Way")


def test_incomplete_address_accepts_street_level_values():
    assert not mod.is_incomplete_address("117 MacDougal St, New York, NY 10012")
    assert not mod.is_incomplete_address("One MGM Way, Springfield, MA 01103")


def test_build_search_query_uses_name_and_location_context_before_website():
    row = _row(
        name="Dr. Grins Comedy Club",
        city="Grand Rapids",
        state="MI",
        website="https://www.thebob.com/drgrins/",
    )

    assert mod.build_search_query(row) == "Dr. Grins Comedy Club Grand Rapids MI"


def test_text_search_match_requires_state_when_candidate_has_state():
    row = _row(name="Comedy Works Downtown", city="Denver", state="CO")
    result = mod.PlaceResolution(
        source=mod.SOURCE_TEXT_SEARCH,
        place_id="ChIJwrong",
        display_name="Comedy Works Downtown",
        formatted_address="117 MacDougal St, New York, NY 10012, USA",
        city="New York",
        state_code="NY",
        lat=40.0,
        lng=-73.0,
        website=None,
        primary_type="comedy_club",
    )

    trusted = mod.validate_resolution(row, result)

    assert not trusted.accepted
    assert "state mismatch" in trusted.reason


def test_text_search_match_rejects_weak_generic_identity_without_location_context():
    row = _row(name="Comedy Shows Near Me", city=None, state=None)
    result = mod.PlaceResolution(
        source=mod.SOURCE_TEXT_SEARCH,
        place_id="ChIJcellar",
        display_name="Comedy Cellar",
        formatted_address="117 MacDougal St, New York, NY 10012, USA",
        city="New York",
        state_code="NY",
        lat=40.0,
        lng=-73.0,
        website="https://www.comedycellar.com",
        primary_type="comedy_club",
    )

    trusted = mod.validate_resolution(row, result)

    assert not trusted.accepted
    assert "weak name match" in trusted.reason


def test_place_id_resolution_is_accepted_when_details_include_address_and_coordinates():
    row = _row(name="Helium Comedy Club - Indianapolis", google_place_id="ChIJown")
    result = mod.PlaceResolution(
        source=mod.SOURCE_PLACE_ID,
        place_id="ChIJown",
        display_name=None,
        formatted_address="10 W Georgia St, Indianapolis, IN 46225, USA",
        city="Indianapolis",
        state_code="IN",
        lat=39.0,
        lng=-86.0,
        website=None,
        primary_type=None,
    )

    trusted = mod.validate_resolution(row, result)

    assert trusted.accepted


def test_sql_literal_escapes_quotes_and_nulls():
    assert mod.sql_literal(None) == "NULL"
    assert mod.sql_literal("Governor's Comedy") == "'Governor''s Comedy'"
