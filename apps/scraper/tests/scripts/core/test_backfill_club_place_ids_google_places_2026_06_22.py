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


def test_validate_generic_name_requires_zip_anchor():
    # A club whose name collapses to no strong tokens ("The Comedy Club") has no
    # name signal, so a street-number-only anchor (zip absent in result) must NOT
    # be accepted...
    generic = _row(name="The Comedy Club", address="200 Main St", zip_code="10012")
    no_zip = _result(display_name="Acme Bank", formatted_address="200 Main St, New York, NY, USA")
    ok, reason = mod._validate(generic, no_zip)
    assert ok is False
    assert "generic name without zip anchor" in reason
    # ...but a matching zip anchor is enough to accept it.
    with_zip = _result(display_name="Acme Bank", formatted_address="200 Main St, New York, NY 10012, USA")
    ok2, _ = mod._validate(generic, with_zip)
    assert ok2 is True


def test_street_number_is_leading_only():
    # A leading house number is captured; a zip/suite digit run is not.
    assert mod._street_number("117 MacDougal St") == "117"
    assert mod._street_number("Suite 200, Broadway") is None
    assert mod._street_number("MacDougal St, NY 10012") is None


def test_result_zip_prefers_zip_after_state_not_leading_street_number():
    # The Milwaukee Improv artifact: a leading 5-digit street number must not be
    # mistaken for the zip (TASK-3175).
    assert mod._result_zip("20110 W Bluemound Rd, Brookfield, WI 53045, USA") == "53045"
    assert mod._result_zip("123 S Walnut St, Bloomington, IN 47408, USA") == "47408"
    assert mod._result_zip("Some Place, New York, NY 10012-1234, USA") == "10012"
    # Fallback to the last 5-digit run when there is no state+zip pattern.
    assert mod._result_zip("Somewhere 90210") == "90210"
    assert mod._result_zip("No digits here") is None


def test_validate_accepts_leading_5digit_street_number_with_matching_zip():
    # A venue whose Google address starts with a 5-digit house number but whose
    # real zip equals the stored zip must be ACCEPTED, not false-rejected.
    row = _row(name="Milwaukee Improv", address="20110 W Bluemound Rd", state="WI", zip_code="53045")
    result = _result(
        display_name="Milwaukee Improv",
        formatted_address="20110 W Bluemound Rd, Brookfield, WI 53045, USA",
        state_code="WI",
    )
    ok, reason = mod._validate(row, result)
    assert ok is True, reason
