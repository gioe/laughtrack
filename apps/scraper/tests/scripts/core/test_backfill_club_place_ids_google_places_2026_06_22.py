"""Unit tests for the TASK-3174 google_place_id backfill script.

Exercises the pure functions (eligibility, query build, high-confidence
validation) directly — no HTTP, no DB — mirroring the sibling
test_backfill_club_location_records_google_places_2026_06_20 pattern.
"""

from scripts.core import backfill_club_place_ids_google_places_2026_06_22 as mod


def _row(**kwargs):
    base = dict(
        id=1,
        name="The Comedy Cellar",
        address="117 MacDougal St",
        city="New York",
        state="NY",
        zip_code="10012",
        country="US",
        website="https://comedycellar.com",
        status="active",
        visible=True,
        club_type="club",
        google_place_id=None,
    )
    base.update(kwargs)
    return mod.ClubRow(**base)


def _result(**kwargs):
    base = dict(
        source="text_search",
        place_id="ChIJabc123",
        display_name="The Comedy Cellar",
        formatted_address="117 MacDougal St, New York, NY 10012, USA",
        city="New York",
        state_code="NY",
        lat=40.73,
        lng=-74.0,
        website="https://comedycellar.com",
        primary_type="comedy_club",
    )
    base.update(kwargs)
    return mod.PlaceResult(**base)


# --- eligibility ---------------------------------------------------------

def test_eligibility_accepts_active_visible_club():
    ok, _ = mod._eligibility(_row())
    assert ok is True


def test_eligibility_excludes_hidden_inactive_or_producer():
    assert mod._eligibility(_row(visible=False))[0] is False
    assert mod._eligibility(_row(status="closed"))[0] is False
    assert mod._eligibility(_row(club_type="producer"))[0] is False
    assert mod._eligibility(_row(name="Acme Roving Producer"))[0] is False


# --- query build ---------------------------------------------------------

def test_build_query_uses_name_and_address_parts():
    q = mod._build_query(_row())
    assert q == "The Comedy Cellar 117 MacDougal St New York NY 10012"


def test_build_query_falls_back_to_website_when_no_address():
    q = mod._build_query(_row(address=None, city=None, state=None, zip_code=None))
    assert "comedycellar.com" in q


# --- validation (high-confidence gate) -----------------------------------

def test_validate_accepts_state_zip_and_name_match():
    ok, reason = mod._validate(_row(), _result())
    assert ok is True
    assert "high-confidence" in reason


def test_validate_accepts_street_number_anchor_without_zip():
    # zip absent from formatted address but the street number matches.
    r = _result(formatted_address="117 MacDougal St, New York, NY, USA")
    ok, _ = mod._validate(_row(), r)
    assert ok is True


def test_validate_rejects_state_mismatch():
    ok, reason = mod._validate(_row(state="NY"), _result(state_code="CA", formatted_address="1 Main St, Los Angeles, CA 90001, USA"))
    assert ok is False
    assert "state mismatch" in reason


def test_validate_rejects_zip_mismatch():
    ok, reason = mod._validate(_row(zip_code="10012"), _result(formatted_address="500 W 1st St, New York, NY 10025, USA"))
    assert ok is False
    assert "zip mismatch" in reason


def test_validate_rejects_no_address_anchor():
    # No zip and no matching street number -> no strong anchor -> reject.
    r = _result(formatted_address="Somewhere, New York, NY, USA")
    ok, reason = mod._validate(_row(zip_code=None, address="The Cellar"), r)
    assert ok is False
    assert "anchor" in reason


def test_validate_rejects_no_name_overlap():
    # Same address anchor (zip) but a totally different venue name.
    r = _result(display_name="Joe's Pizza", formatted_address="117 MacDougal St, New York, NY 10012, USA")
    ok, reason = mod._validate(_row(name="The Comedy Cellar"), r)
    assert ok is False
    assert "name-token overlap" in reason


def test_validate_rejects_missing_formatted_address():
    ok, reason = mod._validate(_row(), _result(formatted_address=None))
    assert ok is False
    assert "formatted address" in reason
