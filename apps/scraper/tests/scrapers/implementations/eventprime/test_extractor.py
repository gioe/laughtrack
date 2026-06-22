"""Unit tests for the EventPrime get_events extractor."""

from __future__ import annotations

from laughtrack.scrapers.implementations.eventprime.extractor import (
    extract_eventprime_events,
)


def _event(
    *,
    event_id: int,
    title: str,
    start_date: str,
    tickets: list | None = None,
    status: str = "publish",
    permalink: str | None = None,
    content: str = "",
    venue=None,
) -> dict:
    return {
        "id": event_id,
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "content": content,
        "status": status,
        "permalink": permalink or f"https://flipflopscomedy.com/event/evt-{event_id}/",
        "image_url": f"https://flipflopscomedy.com/img/{event_id}.png",
        "start_date": start_date,
        "end_date": None,
        "timezone": None,
        "venue": venue,
        "tickets": tickets if tickets is not None else [{"name": "GA", "price": 12}],
    }


def _payload(events: list) -> dict:
    return {"status": "success", "count": len(events), "events": events}


def test_maps_upcoming_events_with_offers_and_image():
    payload = _payload([
        _event(
            event_id=916,
            title="Shell Yeah! A Night of Longform Improv",
            start_date="2099-07-15T21:30:00-04:00",
            tickets=[{"name": "VIP Couch", "price": 35}, {"name": "GA", "price": 12}],
            content="<p>Two of Maine&#8217;s best <span>longform</span> improv teams.</p>",
        )
    ])
    events = extract_eventprime_events(payload, timezone="America/New_York")
    assert len(events) == 1
    e = events[0]
    assert e.name == "Shell Yeah! A Night of Longform Improv"
    # tz-aware ISO start_date with offset is preserved verbatim
    assert e.start_date.isoformat() == "2099-07-15T21:30:00-04:00"
    assert e.url == "https://flipflopscomedy.com/event/evt-916/"
    assert e.image == "https://flipflopscomedy.com/img/916.png"
    # content HTML stripped + entities decoded
    assert "longform improv teams" in e.description
    assert "<" not in e.description
    assert [(o.name, o.price) for o in e.offers] == [("VIP Couch", "35.00"), ("GA", "12.00")]


def test_drops_past_events_by_default_and_keeps_with_include_past():
    payload = _payload([
        _event(event_id=1, title="Future Show", start_date="2099-01-01T20:00:00-05:00"),
        _event(event_id=2, title="Old Show", start_date="2020-01-01T20:00:00-05:00"),
    ])
    upcoming = extract_eventprime_events(payload, timezone="America/New_York")
    assert [e.name for e in upcoming] == ["Future Show"]
    both = extract_eventprime_events(payload, timezone="America/New_York", include_past=True)
    assert {e.name for e in both} == {"Future Show", "Old Show"}


def test_naive_start_date_localized_to_venue_timezone():
    payload = _payload([_event(event_id=3, title="Naive", start_date="2099-08-01T19:00:00")])
    events = extract_eventprime_events(payload, timezone="America/New_York")
    # 19:00 local in August == EDT (-04:00)
    assert events[0].start_date.isoformat() == "2099-08-01T19:00:00-04:00"


def test_free_ticket_price_zero():
    payload = _payload([
        _event(event_id=4, title="Open Mic", start_date="2099-09-01T20:00:00-04:00",
               tickets=[{"name": "GA", "price": 0}])
    ])
    events = extract_eventprime_events(payload, timezone="America/New_York")
    assert events[0].offers[0].price == "0.00"


def test_comedy_filter_drops_non_comedy():
    payload = _payload([
        _event(event_id=5, title="Improv Jam", start_date="2099-10-01T20:00:00-04:00"),
        _event(event_id=6, title="Watercolor Painting Class", start_date="2099-10-02T20:00:00-04:00",
               content="Bring a canvas."),
    ])
    assert len(extract_eventprime_events(payload, timezone="America/New_York")) == 2
    filtered = extract_eventprime_events(payload, timezone="America/New_York", comedy_filter=True)
    assert [e.name for e in filtered] == ["Improv Jam"]


def test_ignores_non_publish_and_malformed():
    payload = _payload([
        _event(event_id=7, title="Draft", start_date="2099-11-01T20:00:00-04:00", status="draft"),
        _event(event_id=8, title="", start_date="2099-11-02T20:00:00-04:00"),
        {"id": 9, "title": "No date", "status": "publish", "permalink": "x"},
        "not-a-dict",
    ])
    assert extract_eventprime_events(payload, timezone="America/New_York") == []


def test_non_dict_payload_returns_empty():
    assert extract_eventprime_events(None, timezone="America/New_York") == []
    assert extract_eventprime_events({"events": "nope"}, timezone="America/New_York") == []
