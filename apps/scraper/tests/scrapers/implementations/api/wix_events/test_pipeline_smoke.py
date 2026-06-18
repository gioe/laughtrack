"""Tests for the wix_events extractor comedy_filter (TASK-2952).

Jazz-first / mixed-use Wix venues opt into comedy filtering via the source's
`comedy_filter` metadata flag. The Wix paginated-events API exposes no category
field, so the filter is a title+description comedy-keyword match.
"""

from laughtrack.scrapers.implementations.api.wix_events.extractor import WixEventsExtractor


def _raw_event(event_id, title, description=""):
    return {
        "id": event_id,
        "title": title,
        "description": description,
        "slug": title.lower().replace(" ", "-"),
        "scheduling": {"config": {"startDate": "2026-06-20T20:00:00Z", "timeZoneId": "America/Los_Angeles"}},
        "registration": {},
    }


def _api_response(events):
    return {"events": events, "hasMore": False}


def test_filter_off_keeps_all_events():
    """Without comedy_filter, every event is kept (all-comedy Wix venues)."""
    resp = _api_response([
        _raw_event("1", "Cool Jazz (front room) Comedy (back patio)"),
        _raw_event("2", "Jazz Jam"),
        _raw_event("3", "Latin Vibe"),
    ])
    events = WixEventsExtractor.extract_events(resp)
    assert {e.title for e in events} == {
        "Cool Jazz (front room) Comedy (back patio)",
        "Jazz Jam",
        "Latin Vibe",
    }


def test_filter_drops_jazz_keeps_comedy():
    """With comedy_filter, jazz/music titles are dropped; comedy nights kept (Jazzy Wishbone)."""
    resp = _api_response([
        _raw_event("1", "Cool Jazz (front room) Comedy (back patio)"),
        _raw_event("2", "Jazz Jam"),
        _raw_event("3", "Cool Jazz"),
        _raw_event("4", "Rick Berthod"),
        _raw_event("5", "Latin Vibe"),
    ])
    events = WixEventsExtractor.extract_events(resp, comedy_filter=True)
    assert {e.title for e in events} == {"Cool Jazz (front room) Comedy (back patio)"}


def test_filter_keeps_event_when_description_signals_comedy():
    """A neutral title is kept when the description mentions stand-up comedy."""
    resp = _api_response([
        _raw_event("1", "Saturday Night", description="An evening of stand-up comedy."),
        _raw_event("2", "Saturday Night", description="Smooth jazz quartet."),
    ])
    events = WixEventsExtractor.extract_events(resp, comedy_filter=True)
    assert len(events) == 1
    assert events[0].id == "1"
