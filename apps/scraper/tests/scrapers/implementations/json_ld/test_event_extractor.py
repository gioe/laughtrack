import json
import logging
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


def test_extract_typed_field_values_reads_collection_page_list_item_urls():
    collection_page = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "url": "https://venue.example.com/events/first"},
                {"@type": "ListItem", "url": "/events/second"},
            ],
        },
    }

    urls = EventExtractor.extract_typed_field_values(
        _wrap_ldjson(collection_page),
        object_type="CollectionPage",
        field_path="mainEntity.itemListElement[].url",
    )

    assert urls == {
        "https://venue.example.com/events/first",
        "/events/second",
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


def test_same_as_override_supplies_url_for_urlless_detail_event():
    # City/government arts calendars (e.g. pompanobeacharts.org) emit
    # detail-page Event JSON-LD with name/startDate/location but no `url`.
    # JsonLdEvent.from_json_ld requires url, so without same_as_override the
    # block is dropped. When the detail URL is known (set_same_as_to_detail_url),
    # it is injected as the event url so the event parses.
    event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Live at the Hive: Florida's Funniest Comedians",
        "startDate": "2099-06-26T00:00-05:00",
        "endDate": "2099-08-15T00:00-05:00",
        "location": {"@type": "Place", "name": "The Hive Black Box Theater"},
        # intentionally no "url"
    }

    detail_url = "https://www.pompanobeacharts.org/events/live-at-the-hive"

    # Without the override, the url-less block is dropped.
    assert EventExtractor.extract_events(_wrap_ldjson(event)) == []

    # With the detail URL known, it is injected as the event url.
    events = EventExtractor.extract_events(
        _wrap_ldjson(event),
        same_as_override=detail_url,
    )
    assert len(events) == 1
    assert events[0].url == detail_url
    assert events[0].same_as == detail_url
    assert events[0].location.name == "The Hive Black Box Theater"


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


def test_extract_events_aggregate_offer_sold_out_flag_propagates_to_ticket():
    from laughtrack.utilities.domain.show.enhancement import ShowEnhancement

    obj = {
        "@type": "ComedyEvent",
        "name": "Sold Out Aggregate Offer",
        "startDate": "2026-07-10T20:00:00-04:00",
        "url": "https://www.uptownpvd.com/events/sold-out",
        "location": {"@type": "Place", "name": "Uptown Theater"},
        "offers": {
            "@type": "AggregateOffer",
            "url": "https://www.uptownpvd.com/events/sold-out",
            "lowPrice": 64,
            "highPrice": 109,
            "priceCurrency": "USD",
            "availability": "https://schema.org/SoldOut",
        },
    }
    events = EventExtractor.extract_events(_wrap_ldjson(obj))
    tickets = ShowEnhancement.enhance_tickets_from_event(events[0])
    assert len(tickets) == 1
    assert tickets[0].sold_out is True
    assert tickets[0].price == 64.0


def test_extract_events_reads_schema_org_microdata_event_attrs():
    html = """
    <html><body>
      <article itemscope itemtype="http://schema.org/Event">
        <meta itemprop="startDate" content="2026-06-27T01:00:00">
        <meta itemprop="endDate" content="2026-06-27T03:00:00">
        <a itemprop="url" href="/event/late-night-comedy-42/register">
          <span itemprop="name">Late Night Comedy</span>
        </a>
        <div itemprop="description">A stand-up showcase in Oak Park.</div>
        <div itemprop="location" itemscope itemtype="http://schema.org/Place">
          <span itemprop="name">Comedy Plex Comedy Club</span>
          <div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">
            <span itemprop="streetAddress">1128 Lake St Lower Level</span>
            <span itemprop="addressLocality">Oak Park</span>
            <span itemprop="addressRegion">IL</span>
            <span itemprop="postalCode">60301</span>
            <span itemprop="addressCountry">US</span>
          </div>
        </div>
        <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
          <a itemprop="url" href="/event/late-night-comedy-42/register">Register</a>
          <meta itemprop="price" content="25.00">
          <meta itemprop="priceCurrency" content="USD">
          <link itemprop="availability" href="https://schema.org/InStock">
        </div>
      </article>
    </body></html>
    """

    events = EventExtractor.extract_events(
        html,
        same_as_override="https://www.comedyplex.com/event/late-night-comedy-42/register",
    )

    assert len(events) == 1
    event = events[0]
    assert event.name == "Late Night Comedy"
    assert event.same_as == "https://www.comedyplex.com/event/late-night-comedy-42/register"
    assert event.start_date.isoformat() == "2026-06-27T01:00:00"
    assert event.location.name == "Comedy Plex Comedy Club"
    assert event.location.address.street_address == "1128 Lake St Lower Level"
    assert event.offers[0].price == "25.00"
    assert event.offers[0].price_currency == "USD"


def test_extract_events_uses_detail_url_for_microdata_without_url_prop():
    html = """
    <html><body>
      <div itemscope itemtype="http://schema.org/Event">
        <h1 itemprop="name">Andrew Rudick</h1>
        <meta itemprop="startDate" content="2026-08-22T01:00:00">
        <div itemprop="location" itemscope itemtype="https://schema.org/Place">
          <div itemprop="name">Comedy Plex</div>
          <div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">
            <span itemprop="streetAddress">1128 Lake St<br>Lower Level<br>Oak Park IL 60301<br>United States</span>
          </div>
        </div>
      </div>
    </body></html>
    """

    events = EventExtractor.extract_events(
        html,
        same_as_override="https://www.comedyplex.com/event/andrew-rudick-864/register",
    )

    assert len(events) == 1
    assert events[0].name == "Andrew Rudick"
    assert events[0].url == "https://www.comedyplex.com/event/andrew-rudick-864/register"
    assert events[0].same_as == "https://www.comedyplex.com/event/andrew-rudick-864/register"


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


# ---------------------------------------------------------------------------
# extract_min_offer_price — lowest per-tier price across Event offers
# ---------------------------------------------------------------------------


def _priced_event(offers):
    return {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Priced Show",
        "url": "https://example.com/e/priced-show",
        "startDate": "2026-06-13T20:00:00-05:00",
        "offers": offers,
    }


def test_extract_min_offer_price_single_offer_dict():
    """OpenDate shape: a single Offer dict with a string price."""
    html = _wrap_ldjson(_priced_event(
        {"@type": "Offer", "url": "https://example.com/e/x", "price": "25.0", "priceCurrency": "USD"}
    ))
    assert EventExtractor.extract_min_offer_price(html) == 25.0


def test_extract_min_offer_price_offers_list_takes_lowest_positive():
    """ShowClix/Leap shape: per-tier Offer list — lowest positive tier wins."""
    html = _wrap_ldjson(_priced_event([
        {"@type": "Offer", "price": "35.00", "priceCurrency": "USD"},
        {"@type": "Offer", "price": "20.00", "priceCurrency": "USD"},
        {"@type": "Offer", "price": "0.00", "priceCurrency": "USD"},
    ]))
    assert EventExtractor.extract_min_offer_price(html) == 20.0


def test_extract_min_offer_price_aggregate_offer_low_price():
    """ThunderTix shape: AggregateOffer lowPrice via the Offer model fallback."""
    html = _wrap_ldjson(_priced_event(
        {"@type": "AggregateOffer", "lowPrice": "15.0", "highPrice": "40.0", "priceCurrency": "USD"}
    ))
    assert EventExtractor.extract_min_offer_price(html) == 15.0


def test_extract_min_offer_price_all_zero_offers_means_free():
    """Explicit all-zero offers (RSVP-only open mics) parse as proven-free 0.0."""
    html = _wrap_ldjson(_priced_event(
        {"@type": "Offer", "url": "https://example.com/e/x", "price": "0.0", "priceCurrency": "USD"}
    ))
    assert EventExtractor.extract_min_offer_price(html) == 0.0


def test_extract_min_offer_price_none_without_offers():
    """Pages without parseable offers yield None (price unknown, not 0)."""
    assert EventExtractor.extract_min_offer_price("<html><body>no ld</body></html>") is None
    html = _wrap_ldjson(_priced_event({"@type": "Offer", "price": "", "priceCurrency": "USD"}))
    assert EventExtractor.extract_min_offer_price(html) is None


def test_extract_min_offer_price_survives_events_missing_model_required_fields():
    """Price extraction must not depend on the JsonLdEvent factory's required fields.

    Live SimpleTix pages emit a top-level array of per-showtime Events with no
    `url` anywhere; live ThunderTix detail pages omit `startDate`. Both would
    be dropped by JsonLdEvent.from_json_ld, but their offers must still yield
    a price (TASK-2848).
    """
    # SimpleTix shape: array of Events, no url, AggregateOffer lowPrice.
    simpletix = _wrap_ldjson([
        {
            "@type": "Event",
            "name": "ImprovCity Show - Tickets",
            "startDate": "2099-01-02T19:30:00+00:00",
            "offers": [{"@type": "AggregateOffer", "priceCurrency": "USD", "lowPrice": 5.72, "highPrice": 20.03}],
        }
    ])
    assert EventExtractor.extract_min_offer_price(simpletix) == 5.72

    # ThunderTix detail-page shape: Event with no startDate.
    thundertix = _wrap_ldjson({
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Jury Duty",
        "offers": {
            "@type": "AggregateOffer",
            "url": "https://theannoyance.thundertix.com/events/1",
            "priceCurrency": "USD",
            "lowPrice": "15.0",
            "highPrice": "15.0",
        },
    })
    assert EventExtractor.extract_min_offer_price(thundertix) == 15.0


def test_extract_min_offer_price_skips_non_dict_offer_entries():
    """Non-dict members of an offers list are skipped, not fatal."""
    html = _wrap_ldjson(_priced_event(
        ["not an offer", {"@type": "Offer", "price": "18.00", "priceCurrency": "USD"}]
    ))
    assert EventExtractor.extract_min_offer_price(html) == 18.0


def test_unparseable_event_is_logged_not_silently_dropped(caplog):
    """An Event block that fails JsonLdEvent validation (here: missing the
    required url field) is skipped, but the skip emits a debug log naming the
    exception and the event's @type/name so a vendor dropping a required field
    is diagnosable from nightly logs instead of looking like 'no JSON-LD'."""
    # No url and no offers.url fallback -> JsonLdEvent.from_json_ld raises ValueError.
    html = _wrap_ldjson({
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Mystery Headliner",
        "startDate": "2099-09-18T19:30:00+00:00",
    })

    with caplog.at_level(logging.DEBUG):
        events = EventExtractor.extract_events(html)

    # The event is still skipped (no usable url), but it is no longer silent.
    assert events == []
    skip_logs = [r for r in caplog.records if "Skipping unparseable JSON-LD event" in r.getMessage()]
    assert skip_logs, "expected a debug log for the dropped JSON-LD event"
    message = skip_logs[0].getMessage()
    assert "Mystery Headliner" in message  # event name
    assert "Event" in message              # event @type
    assert "ValueError" in message         # the failing exception


def _relative_url_event():
    return {
        "@context": "http://schema.org",
        "@type": "Event",
        "name": "Comedy w/Dave Landau + Derek Richards",
        "startDate": "2026-08-21T20:00:00-04:00",
        # mynorthtickets (Traverse City Comedy Club 1058) emits a root-relative url
        "url": "/events/comedy-wdave-landau-derek-richards-8-21-2026",
        "location": {
            "@type": "Place",
            "name": "Traverse City Comedy Club",
            "address": {"streetAddress": "123 Front St", "addressLocality": "Traverse City",
                        "addressRegion": "MI", "postalCode": "49684", "addressCountry": "US"},
        },
        "offers": {"@type": "Offer", "price": "35.15", "priceCurrency": "USD"},
    }


def test_relative_event_url_resolved_against_base_url():
    """TASK-3513: root-relative JSON-LD event urls are made absolute against the
    fetched page so they survive Show URL-format validation instead of being
    silently dropped (Traverse City Comedy Club / mynorthtickets)."""
    html = _wrap_ldjson(_relative_url_event())
    base = "https://mynorthtickets.com/organizations/traverse-city-comedy-club"

    events = EventExtractor.extract_events(html, base_url=base)
    assert len(events) == 1
    assert events[0].url == "https://mynorthtickets.com/events/comedy-wdave-landau-derek-richards-8-21-2026"


def test_relative_offer_url_resolved_against_base_url():
    """A root-relative offers.url is also resolved (used as the ticket purchase_url)."""
    event = _relative_url_event()
    event["offers"] = {"@type": "Offer", "url": "/checkout/abc", "price": "35.15", "priceCurrency": "USD"}
    html = _wrap_ldjson(event)
    base = "https://mynorthtickets.com/organizations/traverse-city-comedy-club"

    events = EventExtractor.extract_events(html, base_url=base)
    assert len(events) == 1
    assert events[0].offers[0].url == "https://mynorthtickets.com/checkout/abc"


def test_absolute_url_unchanged_when_base_url_supplied():
    """base_url is a no-op for already-absolute urls (the common case)."""
    event = _relative_url_event()
    event["url"] = "https://example.com/events/already-absolute"
    html = _wrap_ldjson(event)

    events = EventExtractor.extract_events(html, base_url="https://mynorthtickets.com/x")
    assert len(events) == 1
    assert events[0].url == "https://example.com/events/already-absolute"


def test_relative_url_dropped_when_no_base_url():
    """Without base_url the relative url is left as-is (back-compat: prior behavior)."""
    html = _wrap_ldjson(_relative_url_event())
    events = EventExtractor.extract_events(html)
    assert len(events) == 1
    assert events[0].url == "/events/comedy-wdave-landau-derek-richards-8-21-2026"
