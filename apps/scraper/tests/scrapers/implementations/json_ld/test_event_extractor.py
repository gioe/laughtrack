import json
from datetime import timezone

import pytest

from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


def _wrap_ldjson(obj):
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


def test_extract_events_handles_context_and_lowercase_type_and_offers_url_fallback():
    club = {
        "@context": "http://schema.org",
        "@type": "ComedyClub",
        "name": "Arlington Improv",
        "url": "https://improvtx.com/arlington/",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "309 Curtis Mathes Way #147",
            "addressLocality": "Arlington",
            "postalCode": "76018",
            "addressRegion": "TX",
            "addressCountry": "US",
        },
    }
    e1 = {
        "@context": "http://schema.org",
        "@type": "event",  # lower-case
        "name": "Michael Colyar",
        "startDate": "2025-09-18T19:30:00-05:00",
        "location": {
            "@type": "Place",
            "name": "Arlington Improv",
            "address": {
                "streetAddress": "309 Curtis Mathes Way #147",
                "addressLocality": "Arlington",
                "addressRegion": "TX",
                "postalCode": "76018",
                "addressCountry": "US",
            },
        },
        "offers": {
            "@type": "offer",
            "url": "https://www.ticketweb.com/event/michael-colyar-arlington-improv-tickets/13706534?pl=arlingtonimprov",
            "price": "31.40",
            "priceCurrency": "USD",
            "availability": "http://schema.org/InStock",
            "validFrom": "2025-02-10T15:05:00-06:00",
        },
        "performer": [{"name": "Michael Colyar"}],
    }

    html = _wrap_ldjson(club) + _wrap_ldjson([e1])

    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    ev = events[0]
    assert ev.name == "Michael Colyar"
    # url should fall back from offers
    assert ev.url.startswith("https://www.ticketweb.com/event/")
    # start_date parsed with tzinfo
    assert ev.start_date.tzinfo is not None and ev.start_date.tzinfo != timezone.utc or ev.start_date.utcoffset() is not None
    # location name preserved
    assert ev.location.name == "Arlington Improv"
    # offers normalized to list
    assert len(ev.offers) == 1
    assert ev.offers[0].price == "31.40" and ev.offers[0].price_currency == "USD"
    # performers parsed
    assert ev.performers and ev.performers[0].name == "Michael Colyar"


def test_extract_events_handles_graph_and_list_type_and_dedup():
    graph_event = {
        "@type": ["Event", "ComedyEvent"],
        "name": "Graph Show",
        "startDate": "2025-11-01T20:00:00-05:00",
        "url": "https://tickets.example.com/graph-show",
        "location": {"name": "Graph Venue", "address": "123 Anywhere"},
        "offers": [{
            "url": "https://tickets.example.com/graph-show",
            "price": "20",
            "priceCurrency": "USD",
            "availability": "http://schema.org/InStock"
        }],
        "performer": {"name": "Graph Comic"},
    }
    non_event = {"@type": "Organization", "name": "Not an event"}

    ld = {"@context": "https://schema.org", "@graph": [graph_event, non_event, graph_event]}

    html = _wrap_ldjson(ld)

    events = EventExtractor.extract_events(html)
    # dedup should remove duplicate event in graph
    assert len(events) == 1
    ev = events[0]
    assert ev.name == "Graph Show"
    assert ev.url == "https://tickets.example.com/graph-show"
    assert ev.location.name == "Graph Venue"


def test_extract_event_field_values_reads_same_as_from_graph_events():
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Event",
                "name": "First",
                "startDate": "2099-01-01T20:00:00-05:00",
                "url": "https://tickets.example.com/first",
                "sameAs": "https://venue.example.com/comic/first",
                "location": {"name": "Venue", "address": "1 Main"},
            },
            {
                "@type": "ComedyEvent",
                "name": "Second",
                "startDate": "2099-01-02T20:00:00-05:00",
                "url": "https://tickets.example.com/second",
                "sameAs": [
                    "https://venue.example.com/comic/second",
                    "https://venue.example.com/comic/first",
                ],
                "location": {"name": "Venue", "address": "1 Main"},
            },
            {"@type": "Organization", "sameAs": "https://ignore.example.com"},
        ],
    }

    urls = EventExtractor.extract_event_field_values(_wrap_ldjson(graph), "sameAs")

    assert urls == {
        "https://venue.example.com/comic/first",
        "https://venue.example.com/comic/second",
    }


def test_extract_events_can_override_same_as_for_detail_page_events():
    event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Detail Showtime",
        "startDate": "2099-01-01T20:00:00-05:00",
        "url": "https://ticketweb.com/detail-showtime",
        "location": {"name": "Venue", "address": "1 Main"},
    }

    events = EventExtractor.extract_events(
        _wrap_ldjson(event),
        same_as_override="https://venue.example.com/comic/detail",
    )

    assert len(events) == 1
    assert events[0].url == "https://ticketweb.com/detail-showtime"
    assert events[0].same_as == "https://venue.example.com/comic/detail"


def test_extract_events_handles_offers_list_and_top_level_url():
    obj = {
        "@type": "Event",
        "name": "Top URL",
        "url": "https://tickets.example.com/top",
        "startDate": "2025-10-10T19:00:00-05:00",
        "location": {"name": "Top Venue", "address": {"streetAddress": "1 Main"}},
        "offers": [
            {"url": "https://tickets.example.com/top", "price": "10", "priceCurrency": "USD", "availability": "http://schema.org/InStock"},
            {"url": "https://tickets.example.com/top2", "price": "12", "priceCurrency": "USD", "availability": "http://schema.org/InStock"},
        ],
        "performer": [{"name": "A"}, {"name": "B"}],
    }
    html = _wrap_ldjson(obj)
    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    ev = events[0]
    assert ev.url == "https://tickets.example.com/top"
    assert len(ev.offers) == 2
    assert ev.performers is not None
    assert [p.name for p in ev.performers] == ["A", "B"]


def test_extract_events_handles_address_as_string_and_location_name_fallback():
    obj = {
        "@type": "Event",
        "name": "Name Fallback",
        "startDate": "2025-12-24T21:00:00-05:00",
        "location": {"address": "No name street only"},
        "offers": {"url": "https://tickets.example.com/fallback", "price": "0", "priceCurrency": "USD", "availability": "http://schema.org/InStock"},
    }
    html = _wrap_ldjson(obj)
    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    ev = events[0]
    # since location.name missing, fallback to event name
    assert ev.location.name == "Name Fallback"


def test_extract_events_skips_invalid_missing_url_and_offers():
    invalid = {"@type": "Event", "name": "Bad", "startDate": "2025-01-01T20:00:00-05:00"}
    html = _wrap_ldjson([invalid])
    events = EventExtractor.extract_events(html)
    assert events == []


def test_extract_events_aggregate_offer_uses_low_price():
    """AggregateOffer with lowPrice/highPrice exposes lowPrice as the offer price.

    Without this, ShowEnhancement.enhance_tickets_from_event drops the offer for
    empty `price` and the show persists with zero tickets — see Uptown Theater
    (uptownpvd.com) where every event page emits a single AggregateOffer.
    """
    obj = {
        "@type": "ComedyEvent",
        "name": "Aggregate Offer Show",
        "startDate": "2026-07-25T19:30:00-04:00",
        "url": "https://example.com/events/aggregate",
        "location": {"@type": "Place", "name": "Aggregate Venue"},
        "offers": {
            "@type": "AggregateOffer",
            "url": "https://example.com/events/aggregate",
            "lowPrice": 59,
            "highPrice": 94,
            "priceCurrency": "USD",
            "offerCount": 6,
            "availability": "https://schema.org/InStock",
        },
    }
    html = _wrap_ldjson(obj)
    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    assert len(events[0].offers) == 1
    assert events[0].offers[0].price == "59"
    assert events[0].offers[0].price_currency == "USD"


def test_extract_events_aggregate_offer_falls_back_to_high_price():
    """When AggregateOffer omits lowPrice, fall back to highPrice."""
    obj = {
        "@type": "Event",
        "name": "High Price Only",
        "startDate": "2026-08-01T20:00:00-04:00",
        "url": "https://example.com/events/high-only",
        "location": {"@type": "Place", "name": "Venue"},
        "offers": {
            "@type": "AggregateOffer",
            "url": "https://example.com/events/high-only",
            "highPrice": "75.00",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
        },
    }
    html = _wrap_ldjson(obj)
    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    assert events[0].offers[0].price == "75.00"


def test_extract_events_aggregate_offer_with_explicit_price_preserved():
    """An AggregateOffer that explicitly declares `price` keeps that value (no override)."""
    obj = {
        "@type": "Event",
        "name": "Explicit Price",
        "startDate": "2026-09-10T19:00:00-04:00",
        "url": "https://example.com/events/explicit",
        "location": {"@type": "Place", "name": "Venue"},
        "offers": {
            "@type": "AggregateOffer",
            "url": "https://example.com/events/explicit",
            "price": "42.00",
            "lowPrice": 30,
            "highPrice": 60,
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
        },
    }
    html = _wrap_ldjson(obj)
    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    assert events[0].offers[0].price == "42.00"
