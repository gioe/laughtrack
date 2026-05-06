"""Tests for TicketLeap listing-page event ID extraction."""

from pathlib import Path

from laughtrack.scrapers.implementations.ticketleap.extractor import (
    build_event_detail_url,
    extract_event_ids,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _listing_html(payload_json: str) -> str:
    # Realistic shape: inline <script> containing the dataLayer.push call.
    return f"""
    <html><head></head><body>
      <script>
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({payload_json});
      </script>
    </body></html>
    """


def test_extract_event_ids_returns_full_ordered_list():
    payload = (
        '{"event":"orglisting_page_view",'
        '"listing_slug":"funny",'
        '"event_ids":[2053571,2091519,2080411,2094800,2053540,2055152,2102204],'
        '"display_type":"grid"}'
    )
    ids = extract_event_ids(_listing_html(payload))
    assert ids == [2053571, 2091519, 2080411, 2094800, 2053540, 2055152, 2102204]


def test_extract_event_ids_deduplicates_across_payloads():
    first = '{"event":"orglisting_page_view","event_ids":[1,2,3]}'
    second = '{"event":"orglisting_impression","event_ids":[3,4,5]}'
    html = _listing_html(first) + _listing_html(second)
    ids = extract_event_ids(html)
    assert ids == [1, 2, 3, 4, 5]


def test_extract_event_ids_ignores_payloads_without_event_ids():
    payload = '{"event":"consent_update","consent_state":"granted"}'
    assert extract_event_ids(_listing_html(payload)) == []


def test_extract_event_ids_skips_malformed_json():
    # Stray dataLayer.push with broken JSON should not crash extraction; valid
    # payload elsewhere on the page should still be returned.
    bad = '{"event":"broken", "event_ids": [NaN]}'
    good = '{"event":"orglisting_page_view","event_ids":[42]}'
    html = _listing_html(bad) + _listing_html(good)
    ids = extract_event_ids(html)
    assert ids == [42]


def test_extract_event_ids_handles_empty_html():
    assert extract_event_ids("") == []
    assert extract_event_ids("<html></html>") == []


def test_extract_event_ids_handles_literal_brace_paren_inside_string():
    # A JSON string value containing '})' must not truncate the payload. This
    # is exactly the failure mode raw_decode protects against that a non-greedy
    # `.*?\)` regex does not.
    payload = (
        '{"event":"orglisting_page_view",'
        '"event_name":"Laugh })Trap })",'
        '"event_ids":[999, 1000]}'
    )
    ids = extract_event_ids(_listing_html(payload))
    assert ids == [999, 1000]


def test_extract_event_ids_handles_whitespace_between_paren_and_brace():
    # Reformatted HTML where `push(` and `{` are separated by whitespace must
    # still parse — raw_decode itself does not skip leading whitespace.
    html = (
        '<script>window.dataLayer.push(\n    '
        '{"event":"orglisting_page_view","event_ids":[7, 8]}\n  )</script>'
    )
    ids = extract_event_ids(html)
    assert ids == [7, 8]


def test_extract_event_ids_coerces_string_ids_and_skips_non_numeric():
    payload = (
        '{"event":"orglisting_page_view",'
        '"event_ids":["100", 200, null, "not-a-number", 300]}'
    )
    ids = extract_event_ids(_listing_html(payload))
    assert ids == [100, 200, 300]


def test_extract_event_ids_handles_singular_event_id_in_datalayer_push():
    # Some TicketLeap pages have emitted per-event dataLayer.push payloads
    # carrying a singular `event_id` int instead of a batched `event_ids`
    # array. Both forms must extract.
    first = '{"event":"event_view","event_id":2053571}'
    second = '{"event":"event_view","event_id":2053540}'
    html = _listing_html(first) + _listing_html(second)
    ids = extract_event_ids(html)
    assert ids == [2053571, 2053540]


def test_extract_event_ids_handles_appwrapper_default_events_array():
    # Current (2026-05) TicketLeap listing form: events are nested in the
    # AppWrapper.default(...) initialization arguments rather than dataLayer.
    html = """
    <script>
      AppWrapper.default(
        document.getElementById('listing'),
        {"serverTimezoneName":"America/New_York","slug":"funny"},
        {"sellerId":"119485","shortName":"funny"},
        [
          {"type":"listing","resource":"Listing","event_id":2053571,"primary_event_id":2053571},
          {"type":"listing","resource":"Listing","event_id":2053540,"primary_event_id":2053540},
          {"type":"listing","resource":"Listing","event_id":2055152,"primary_event_id":2055152},
          {"type":"listing","resource":"Listing","event_id":2102204,"primary_event_id":2102204}
        ]
      );
    </script>
    """
    ids = extract_event_ids(html)
    assert ids == [2053571, 2053540, 2055152, 2102204]


def test_extract_event_ids_live_funny_listing_fixture():
    # Captured 2026-05 from https://events.ticketleap.com/events/funny via
    # the scraper's HttpClient (curl-cffi). Locks in the four currently-active
    # Mesquite St. Comedy Club events that pre-fix returned [].
    fixture = _FIXTURE_DIR / "funny_listing_2026_05.html"
    html = fixture.read_text()
    ids = extract_event_ids(html)
    assert ids == [2053571, 2053540, 2055152, 2102204]


def test_build_event_detail_url_uses_canonical_path():
    assert (
        build_event_detail_url(2053571)
        == "https://events.ticketleap.com/event/2053571"
    )
