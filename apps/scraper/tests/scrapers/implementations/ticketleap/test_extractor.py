"""Tests for TicketLeap listing-page event ID extraction."""

from laughtrack.scrapers.implementations.ticketleap.extractor import (
    build_event_detail_url,
    extract_event_ids,
)


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


def test_extract_event_ids_coerces_string_ids_and_skips_non_numeric():
    payload = (
        '{"event":"orglisting_page_view",'
        '"event_ids":["100", 200, null, "not-a-number", 300]}'
    )
    ids = extract_event_ids(_listing_html(payload))
    assert ids == [100, 200, 300]


def test_build_event_detail_url_uses_canonical_path():
    assert (
        build_event_detail_url(2053571)
        == "https://events.ticketleap.com/event/2053571"
    )
