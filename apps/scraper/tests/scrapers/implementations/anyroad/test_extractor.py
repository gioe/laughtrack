"""Unit tests for the AnyRoad experiences extractor."""

from __future__ import annotations

from laughtrack.scrapers.implementations.anyroad.extractor import (
    extract_anyroad_events,
    extract_tour_availability,
)


def _detail_html(dates_json: str) -> str:
    return (
        '<html><body><div data-react-props=\'{"x":1}\'>'
        '{"a":{},"tour_availability":{"isLoading":false,"cached":{},'
        f'"dates":{dates_json}}},"after":1}}</div></body></html>'
    )


def test_extract_tour_availability_parses_dates_block():
    html = _detail_html('{"2026-06-27":{" 6:00pm":23},"2026-07-11":{" 8:30pm":0}}')
    assert extract_tour_availability(html) == {
        "2026-06-27": {" 6:00pm": 23},
        "2026-07-11": {" 8:30pm": 0},
    }


def test_extract_tour_availability_ignores_decoy_dates_in_cached():
    # A non-empty `cached` object preceding `dates` carries its own nested
    # `dates` key; the parser must read the tour_availability object's own
    # `dates`, not the first textual match.
    html = (
        '<html><body>{"a":{},"tour_availability":{"isLoading":false,'
        '"cached":{"stale":{"dates":{"1999-01-01":{" 9:00am":0}}}},'
        '"dates":{"2026-06-27":{" 6:00pm":23}}},"after":1}</body></html>'
    )
    assert extract_tour_availability(html) == {"2026-06-27": {" 6:00pm": 23}}


def test_extract_tour_availability_absent_returns_none():
    assert extract_tour_availability("<html>no availability here</html>") is None
    assert extract_tour_availability(None) is None
    assert extract_tour_availability("") is None
    # tour_availability present but with no dates field → None.
    assert extract_tour_availability('x"tour_availability":{"isLoading":false}y') is None


def test_availability_overrides_placeholder_schedule_with_real_times():
    records = [
        _record(
            exp_id=79259,
            name="ComedySportz",
            schedule={"2026-06-27": {"9:00 AM": 1}},  # list placeholder
        )
    ]
    events = extract_anyroad_events(
        records,
        timezone="America/New_York",
        availability_by_id={"79259": {"2026-06-27": {" 6:00pm": 23}, "2026-07-18": {" 6:00pm": 0}}},
    )
    # Real detail times replace the placeholder, and the detail calendar (2 dates)
    # supersedes the 1-date list schedule.
    assert len(events) == 2
    iso = sorted(e.start_date.isoformat() for e in events)
    assert iso == ["2026-06-27T18:00:00-04:00", "2026-07-18T18:00:00-04:00"]
    sold_out = next(e for e in events if e.start_date.date().isoformat() == "2026-07-18")
    assert sold_out.offers[0].availability == "SoldOut"  # count 0


def test_falls_back_to_placeholder_schedule_when_no_availability():
    records = [
        _record(exp_id=1, name="Improv Jam", schedule={"2026-07-04": {"9:00 AM": 2}})
    ]
    events = extract_anyroad_events(records, timezone="America/New_York", availability_by_id={})
    assert len(events) == 1
    assert events[0].start_date.isoformat() == "2026-07-04T09:00:00-04:00"


def _record(
    *,
    exp_id: int,
    name: str,
    schedule: dict,
    description: str = "",
    price: float | None = 15.0,
    zero_priced: bool = False,
    location: str = "18b Corinth Street, Boston, MA",
    url: str | None = None,
) -> dict:
    return {
        "id": str(exp_id),
        "type": "tours",
        "attributes": {
            "id": exp_id,
            "nameTranslation": name,
            "descriptionTranslation": description,
            "unformattedPrice": price,
            "zeroPriced": zero_priced,
            "locationInfo": location,
            "picture": "//app.anyroad.com/rails/active_storage/x.jpg",
            "url": url or f"https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/exp-{exp_id}",
            "schedule": schedule,
        },
    }


def test_fans_out_one_event_per_schedule_slot():
    records = [
        _record(
            exp_id=79259,
            name="ComedySportz®",
            schedule={
                "2026-06-27": {"9:00 AM": 1},
                "2026-07-11": {"9:00 AM": 1},
            },
        )
    ]
    events = extract_anyroad_events(records, timezone="America/New_York")
    assert len(events) == 2
    assert {e.start_date.date().isoformat() for e in events} == {"2026-06-27", "2026-07-11"}
    e = events[0]
    assert e.name == "ComedySportz®"
    assert e.start_date.tzinfo is not None
    assert e.url.endswith("/tours/exp-79259")
    assert e.offers[0].price == "15.00"
    assert e.offers[0].price_currency == "USD"
    assert e.offers[0].availability == "InStock"
    # locationInfo flows into the Place name (-> Show.room) and the street line
    assert e.location.name == "18b Corinth Street, Boston, MA"
    assert e.location.address.street_address == "18b Corinth Street, Boston, MA"
    # image upgraded to https
    assert e.image == "https://app.anyroad.com/rails/active_storage/x.jpg"


def test_parses_local_time_in_venue_timezone():
    records = [_record(exp_id=1, name="Late Show", schedule={"2026-07-04": {"8:30 PM": 2}})]
    events = extract_anyroad_events(records, timezone="America/New_York")
    assert len(events) == 1
    # 8:30 PM local, EDT in July
    assert events[0].start_date.isoformat() == "2026-07-04T20:30:00-04:00"


def test_zero_availability_marks_sold_out():
    records = [_record(exp_id=2, name="Sold Out Jam", schedule={"2026-07-04": {"9:00 AM": 0}})]
    events = extract_anyroad_events(records, timezone="America/New_York")
    assert events[0].offers[0].availability == "SoldOut"


def test_zero_priced_flag_yields_free_offer():
    records = [
        _record(
            exp_id=3,
            name="The Free Drop-In",
            schedule={"2026-07-04": {"9:00 AM": 5}},
            zero_priced=True,
            price=0.0,
        )
    ]
    events = extract_anyroad_events(records, timezone="America/New_York")
    assert events[0].offers[0].price == "0.00"


def test_comedy_filter_drops_non_comedy_experiences():
    records = [
        _record(exp_id=10, name="Riot Improv Mainstage", schedule={"2026-07-04": {"9:00 AM": 1}}),
        _record(
            exp_id=11,
            name="Watercolor Painting Class",
            description="Bring a canvas and learn landscapes.",
            schedule={"2026-07-05": {"9:00 AM": 1}},
        ),
    ]
    # Without the filter, both experiences are kept.
    assert len(extract_anyroad_events(records, timezone="America/New_York")) == 2
    # With the filter, only the comedy ("improv") experience survives.
    filtered = extract_anyroad_events(records, timezone="America/New_York", comedy_filter=True)
    assert len(filtered) == 1
    assert filtered[0].name == "Riot Improv Mainstage"


def test_ignores_records_without_name_url_or_schedule():
    records = [
        {"id": "1", "type": "tours", "attributes": {"nameTranslation": "", "url": "x", "schedule": {"2026-07-04": {"9:00 AM": 1}}}},
        {"id": "2", "type": "tours", "attributes": {"nameTranslation": "No Schedule", "url": "y", "schedule": {}}},
        {"id": "3", "type": "tours"},  # no attributes
        "not-a-dict",
    ]
    assert extract_anyroad_events(records, timezone="America/New_York") == []
