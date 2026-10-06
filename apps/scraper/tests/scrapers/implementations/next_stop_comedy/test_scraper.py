from __future__ import annotations

import json

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.next_stop_comedy.extractor import (
    extract_event_urls,
    extract_json_ld_events,
)
from laughtrack.scrapers.implementations.next_stop_comedy.scraper import (
    NextStopComedyScraper,
)

_EVENT_HTML = """
<html><body>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ComedyEvent",
  "name": "Trillium - Canton",
  "description": "Next Stop Comedy brings the best comedians.",
  "url": "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09",
  "startDate": "2026-07-09T19:00:00-04:00",
  "location": {
    "@type": "Place",
    "name": "Trillium - Canton",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "100 Royall Street, Canton, MA 02021",
      "addressLocality": "Canton",
      "addressRegion": "MA",
      "postalCode": "02021",
      "addressCountry": "US"
    }
  },
  "performer": [
    {"@type": "Person", "name": "Zach Valencia"},
    {"@type": "Person", "name": "Dan Boulger"}
  ],
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": 27,
    "priceCurrency": "USD",
    "url": "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09",
    "availability": "https://schema.org/InStock"
  }
}
</script>
</body></html>
"""


@pytest.fixture
def promoter_proxy() -> Club:
    club = Club(
        id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID,
        name="Next Stop Comedy",
        address="",
        website="https://www.nextstopcomedy.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
        is_synthetic=True,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        platform="custom",
        scraper_key="next_stop_comedy",
        source_url="https://www.nextstopcomedy.com/events",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _venue_club(venue: dict) -> Club:
    return Club(
        id=4242,
        name=venue["name"],
        address=venue.get("address", ""),
        website="",
        popularity=0,
        zip_code=venue.get("zip_code", ""),
        phone_number="",
        visible=True,
        timezone=venue.get("timezone") or "America/New_York",
    )


def test_extract_event_urls_from_initial_html_and_api_payload():
    html = """
    <a href="/events/trillium-canton-2026-07-09">Show</a>
    <a href="https://www.nextstopcomedy.com/events/lake-norman-brewery-2026-07-09">Show</a>
    <a href="/classes/not-a-show">Class</a>
    """
    api_events = [
        {"slug": "recon-brewing-butler-2026-07-16"},
        {"slug": "trillium-canton-2026-07-09"},
    ]

    urls = extract_event_urls(html, api_events)

    assert urls == [
        "https://www.nextstopcomedy.com/events/lake-norman-brewery-2026-07-09",
        "https://www.nextstopcomedy.com/events/recon-brewing-butler-2026-07-16",
        "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09",
    ]


def test_extract_json_ld_event_to_show_with_lineup_and_ticket():
    events = extract_json_ld_events(_EVENT_HTML)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Trillium - Canton"
    assert event.venue_name == "Trillium - Canton"
    assert event.venue_address == "100 Royall Street, Canton, MA 02021, US"
    assert event.venue_zip == "02021"

    show = event.to_show(_venue_club(event.venue_payload()))

    assert show.club_id == 4242
    assert show.show_page_url == "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09"
    assert [comedian.name for comedian in show.lineup] == ["Zach Valencia", "Dan Boulger"]
    assert show.tickets[0].price == 27
    assert show.tickets[0].purchase_url == show.show_page_url


@pytest.mark.asyncio
async def test_scrape_walks_load_more_and_routes_to_discovered_venues(monkeypatch, promoter_proxy):
    scraper = NextStopComedyScraper(promoter_proxy)
    fetched = []

    async def fake_fetch(url):
        fetched.append(url)
        if url == "https://www.nextstopcomedy.com/events":
            return '<a href="/events/trillium-canton-2026-07-09">Show</a>'
        if url == "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09":
            return _EVENT_HTML
        raise AssertionError(f"unexpected fetch {url}")

    async def fake_fetch_json(url):
        if url.endswith("offset=48"):
            return {
                "events": [{"slug": "trillium-canton-2026-07-09"}],
                "hasMore": False,
                "nextOffset": 72,
            }
        raise AssertionError(f"unexpected json fetch {url}")

    monkeypatch.setattr(scraper, "_fetch_page", fake_fetch)
    monkeypatch.setattr(scraper, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", _venue_club)

    shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].club_id == 4242
    assert [comedian.name for comedian in shows[0].lineup] == ["Zach Valencia", "Dan Boulger"]
    assert "https://www.nextstopcomedy.com/events" in fetched


@pytest.mark.parametrize(
    "address,expected",
    [
        (
            {
                "streetAddress": "100 Royall Street",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": "US",
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "100 Royall Street, Canton, MA 02021",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": {"@type": "Country", "name": "US"},
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "100 Royall Street, Canton, MA 02021, US",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": "US",
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "100 Royall Street, Canton",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": "US",
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "1 Boston Road",
                "addressLocality": "Boston",
                "addressRegion": "MA",
                "addressCountry": "US",
            },
            "1 Boston Road, Boston, MA, US",
        ),
        (
            {
                "streetAddress": " 100 Royall Street ",
                "addressLocality": "",
                "addressRegion": None,
                "addressCountry": {},
            },
            "100 Royall Street",
        ),
        (
            {
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": {"name": "US"},
            },
            "Canton, MA 02021, US",
        ),
    ],
)
def test_extract_preserves_structured_address_evidence(address, expected):
    node = json.loads(_EVENT_HTML.split('<script type="application/ld+json">')[1].split("</script>")[0])
    node["location"]["address"] = address
    html = '<script type="application/ld+json">' + json.dumps(node) + "</script>"
    event = extract_json_ld_events(html)[0]
    assert event.venue_address == expected
    assert event.venue_payload()["address"] == expected


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "America/New_York"),
        ({"eventDate": "2026-07-09T23:00:00Z"}, "America/New_York"),
        ({"eventDate": "2026-07-10T23:00:00Z"}, None),
        ({"eventSlug": "other-event"}, None),
        ({"currentEventId": "other-id"}, None),
        ({"venueTimezone": "invalid/timezone"}, None),
        ({"eventId": None, "currentEventId": None}, None),
    ],
)
def test_timezone_uses_only_matching_main_event_props(changes, expected):
    props = {
        "eventSlug": "trillium-canton-2026-07-09",
        "eventId": "current-id",
        "currentEventId": "current-id",
        "venueTimezone": "America/New_York",
        "nearbyShows": [{"slug": "other-event", "venueTimezone": "America/Los_Angeles"}],
    }
    props.update(changes)
    flight = "1:" + json.dumps(["$", "component", None, props]) + "\n"
    html = _EVENT_HTML + "<script>self.__next_f.push(" + json.dumps([1, flight]) + ")</script>"
    event = extract_json_ld_events(html)[0]
    assert event.venue_timezone == expected
    assert event.venue_payload()["timezone"] == expected
    assert event.start_date.isoformat() == "2026-07-09T19:00:00-04:00"


@pytest.mark.parametrize("cancelled", [False, True])
def test_cancelled_page_without_main_props_does_not_use_nearby_timezone(cancelled):
    flight = (
        "1:"
        + json.dumps({"nearbyShows": [{"slug": "trillium-canton-2026-07-09", "venueTimezone": "America/Los_Angeles"}]})
        + "\n"
    )
    html = _EVENT_HTML.replace(
        '"@type": "ComedyEvent",', '"@type": "ComedyEvent", "eventStatus": "https://schema.org/EventCancelled",'
    ) if cancelled else _EVENT_HTML
    html += "<script>self.__next_f.push(" + json.dumps([1, flight]) + ")</script>"
    if cancelled:
        assert extract_json_ld_events(html) == []
    else:
        assert extract_json_ld_events(html)[0].venue_timezone is None


@pytest.mark.parametrize(
    "status,expected_count",
    [
        ("https://schema.org/EventCancelled", 0),
        ("http://schema.org/EventCancelled", 0),
        ("EventCancelled", 0),
        ("https://schema.org/EventScheduled", 1),
        ("https://schema.org/EventRescheduled", 1),
        (None, 1),
        ("unknown", 1),
        ("https://untrusted.example/EventCancelled", 1),
    ],
)
def test_cancelled_source_events(status, expected_count):
    node = json.loads(_EVENT_HTML.split('<script type="application/ld+json">')[1].split("</script>")[0])
    if status is not None:
        node["eventStatus"] = status
    html = '<script type="application/ld+json">' + json.dumps(node) + "</script>"
    assert len(extract_json_ld_events(html)) == expected_count


@pytest.mark.asyncio
async def test_scrape_holds_conflicting_cancelled_and_scheduled_nodes_before_venue_upsert(monkeypatch, promoter_proxy):
    scraper = NextStopComedyScraper(promoter_proxy)
    node = json.loads(_EVENT_HTML.split('<script type="application/ld+json">')[1].split("</script>")[0])
    cancelled = dict(node, eventStatus="https://schema.org/EventCancelled", name="Cancelled show")
    html = '<script type="application/ld+json">' + json.dumps({"@graph": [cancelled, node]}) + "</script>"
    detail_url = node["url"]
    missing_url = "https://www.nextstopcomedy.com/events/failed-detail"

    async def fetch(url):
        if url.endswith("/events"):
            return f'<a href="{detail_url}">Show</a><a href="{missing_url}">Unavailable</a>'
        return html if url == detail_url else None

    async def api_events():
        return []

    upserts = []

    def upsert(venue):
        upserts.append(venue)
        return _venue_club(venue)

    monkeypatch.setattr(scraper, "_fetch_page", fetch)
    monkeypatch.setattr(scraper, "_collect_api_events", api_events)
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", upsert)
    shows = await scraper.scrape_async()
    assert shows == []
    assert upserts == []


@pytest.mark.parametrize(
    "zones,expected", [(["America/New_York"], "America/New_York"), (["America/New_York", "America/Los_Angeles"], None)]
)
def test_main_timezone_split_flight_chunks_and_conflicting_props(zones, expected):
    props = [
        {"eventSlug": "trillium-canton-2026-07-09", "eventId": "id", "currentEventId": "id", "venueTimezone": zone}
        for zone in zones
    ]
    flight = "1:" + json.dumps(props) + "\n"
    chunks = [flight[: len(flight) // 2], flight[len(flight) // 2 :]]
    html = _EVENT_HTML + "".join(
        "<script>self.__next_f.push(" + json.dumps([1, chunk]) + ")</script>" for chunk in chunks
    )
    assert extract_json_ld_events(html)[0].venue_timezone == expected


@pytest.mark.parametrize(
    "address,expected",
    [
        (
            {
                "streetAddress": "1 Main Street",
                "addressLocality": "Boston",
                "addressRegion": "MA",
                "postalCode": "02116",
                "addressCountry": "US",
            },
            ("Boston", "MA"),
        ),
        (
            {
                "streetAddress": "1 Main Street, Ferndale, Washington 98248",
                "addressLocality": "Ferndale",
                "addressRegion": "WA",
                "postalCode": "98248",
                "addressCountry": "US",
            },
            ("Ferndale", "WA"),
        ),
        (
            {
                "streetAddress": "706 Main St",
                "addressLocality": "Moncton",
                "addressRegion": "NB",
                "postalCode": "E1C 1E4",
                "addressCountry": "CA",
            },
            (None, None),
        ),
        (
            {
                "streetAddress": "1 Main Street",
                "addressLocality": "Perth",
                "addressRegion": "WA",
                "postalCode": "6000",
                "addressCountry": "AU",
            },
            (None, None),
        ),
    ],
)
def test_extracted_address_remains_safe_for_discovered_venue_city_parser(address, expected):
    from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address

    node = json.loads(_EVENT_HTML.split('<script type="application/ld+json">')[1].split("</script>")[0])
    node["location"]["address"] = address
    html = '<script type="application/ld+json">' + json.dumps(node) + "</script>"
    event = extract_json_ld_events(html)[0]
    assert parse_city_state_from_address(event.venue_payload()["address"]) == expected


_REDIRECT_ID = "1df52ed6-a1f9-4f4f-9002-87a6eff110cf"
_OTHER_REDIRECT_ID = "8c332f13-b17e-4bf9-b916-75c2d8b07321"
_REDIRECT_URL = "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09"


def _redirect_html(*, ident=_REDIRECT_ID, changes=None, node_changes=None, split=False):
    node = json.loads(_EVENT_HTML.split('<script type="application/ld+json">')[1].split("</script>")[0])
    node.update(node_changes or {})
    props = dict(eventId=ident, currentEventId=ident, eventSlug=node["url"].rsplit("/", 1)[-1], venueTimezone="America/New_York")
    props.update(changes or {})
    flight = "1:" + json.dumps(["$", "component", None, props]) + "\n"
    chunks = [flight[: len(flight) // 2], flight[len(flight) // 2 :]] if split else [flight]
    return '<script type="application/ld+json">' + json.dumps(node) + '</script>' + ''.join(
        '<script>self.__next_f.push(' + json.dumps([1, chunk]) + ')</script>' for chunk in chunks
    )


@pytest.mark.parametrize("split", [False, True])
def test_redirect_identity_uses_matching_main_uuid(split):
    event = extract_json_ld_events(_redirect_html(split=split))[0]
    assert event.native_event_id == _REDIRECT_ID
    assert event.canonical_event_url == _REDIRECT_URL


@pytest.mark.parametrize("changes", [
    {"eventSlug": "unrelated"}, {"currentEventId": _OTHER_REDIRECT_ID},
    {"eventDate": "2026-07-10T23:00:00Z"}, {"eventDate": "bad"},
    {"eventId": "not-uuid", "currentEventId": "not-uuid"},
])
def test_redirect_invalid_main_identity_cannot_activate(changes):
    assert extract_json_ld_events(_redirect_html(changes=changes))[0].native_event_id is None


def test_redirect_conflicting_main_ids_are_not_arbitrarily_chosen():
    html = _redirect_html() + _redirect_html(ident=_OTHER_REDIRECT_ID)
    assert extract_json_ld_events(html) == []


def test_redirect_nearby_uuid_is_not_main_identity():
    html = _EVENT_HTML + '<script>self.__next_f.push(' + json.dumps([1, '1:' + json.dumps({
        'nearbyShows': [{'eventId': _REDIRECT_ID, 'eventSlug': 'trillium-canton-2026-07-09'}]
    }) + '\n']) + ')</script>'
    assert extract_json_ld_events(html)[0].native_event_id is None


async def _redirect_scraper(monkeypatch, promoter_proxy, pages, rows=None):
    promoter_proxy.production_company_id = 35
    scraper = NextStopComedyScraper(promoter_proxy)
    queries = []
    def query(sql, args, **kwargs):
        queries.append((sql, args))
        return rows if rows is not None else [dict(source_performance_id=f"next_stop_comedy:{_REDIRECT_ID}", show_page_url=_REDIRECT_URL, club_id=4242)]
    async def fetch(url):
        if url.endswith('/events'):
            return ''.join(f'<a href="{key}">Show</a>' for key in pages)
        return pages.get(url)
    async def api():
        return []
    monkeypatch.setattr(scraper._club_handler, 'execute_with_cursor', query)
    monkeypatch.setattr(scraper._club_handler, 'upsert_discovered_venue', _venue_club)
    monkeypatch.setattr(scraper, '_fetch_page', fetch)
    monkeypatch.setattr(scraper, '_collect_api_events', api)
    return scraper, queries


@pytest.mark.asyncio
async def test_redirect_aliases_emit_one_backfilled_identity(monkeypatch, promoter_proxy):
    scraper, queries = await _redirect_scraper(monkeypatch, promoter_proxy, {
        _REDIRECT_URL: _redirect_html(),
        'https://www.nextstopcomedy.com/events/old-alias': _redirect_html(),
    })
    shows = await scraper.scrape_async()
    assert len(shows) == 1
    assert shows[0].source_performance_id == f"next_stop_comedy:{_REDIRECT_ID}"
    assert shows[0].show_page_url == _REDIRECT_URL
    assert len(queries) == 1 and queries[0][1] == (35,)


@pytest.mark.parametrize('second', [
    {'startDate': '2026-07-09T20:00:00-04:00'}, {'name': 'Different venue'},
])
@pytest.mark.asyncio
async def test_redirect_conflicting_current_payloads_hold_all(monkeypatch, promoter_proxy, second):
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {
        _REDIRECT_URL: _redirect_html(),
        'https://www.nextstopcomedy.com/events/old-alias': _redirect_html(node_changes=second),
    })
    assert await scraper.scrape_async() == []


@pytest.mark.parametrize('html', [_EVENT_HTML, _redirect_html(ident=_OTHER_REDIRECT_ID), None])
@pytest.mark.asyncio
async def test_redirect_missing_or_mismatched_proof_never_inserts_legacy_or_cancels(monkeypatch, promoter_proxy, html):
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {_REDIRECT_URL: html})
    assert await scraper.scrape_async() == []


@pytest.mark.asyncio
async def test_redirect_new_slug_and_time_reuse_reviewed_uuid(monkeypatch, promoter_proxy):
    url = 'https://www.nextstopcomedy.com/events/new-slug'
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {
        url: _redirect_html(node_changes={'url': url, 'offers': {'url': url}, 'startDate': '2026-07-10T20:00:00-04:00'}),
    })
    show = (await scraper.scrape_async())[0]
    assert show.source_performance_id == f'next_stop_comedy:{_REDIRECT_ID}'
    assert show.show_page_url == url
    assert show.date.isoformat() == '2026-07-10T20:00:00-04:00'


@pytest.mark.asyncio
async def test_redirect_unreviewed_uuid_stays_legacy(monkeypatch, promoter_proxy):
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {_REDIRECT_URL: _redirect_html()}, rows=[])
    show = (await scraper.scrape_async())[0]
    assert show.source_performance_id is None


@pytest.mark.asyncio
async def test_redirect_review_read_failure_aborts_instead_of_downgrading(monkeypatch, promoter_proxy):
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {_REDIRECT_URL: _redirect_html()})
    def failed(*args, **kwargs):
        raise RuntimeError('database unavailable')
    monkeypatch.setattr(scraper._club_handler, 'execute_with_cursor', failed)
    with pytest.raises(RuntimeError, match='database unavailable'):
        await scraper.scrape_async()


@pytest.mark.asyncio
async def test_redirect_reviewed_uuid_cannot_move_to_different_club(monkeypatch, promoter_proxy):
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {_REDIRECT_URL: _redirect_html()}, rows=[
        dict(source_performance_id=f'next_stop_comedy:{_REDIRECT_ID}', show_page_url=_REDIRECT_URL, club_id=999),
    ])
    assert await scraper.scrape_async() == []


@pytest.mark.asyncio
async def test_redirect_distinct_ids_at_same_slot_remain_distinct(monkeypatch, promoter_proxy):
    other_url = 'https://www.nextstopcomedy.com/events/second-performance'
    rows = [dict(source_performance_id=f'next_stop_comedy:{ident}', show_page_url=url, club_id=4242)
            for ident, url in [(_REDIRECT_ID, _REDIRECT_URL), (_OTHER_REDIRECT_ID, other_url)]]
    scraper, _ = await _redirect_scraper(monkeypatch, promoter_proxy, {
        _REDIRECT_URL: _redirect_html(),
        other_url: _redirect_html(ident=_OTHER_REDIRECT_ID, node_changes={'url': other_url, 'offers': {'url': other_url}}),
    }, rows=rows)
    shows = await scraper.scrape_async()
    assert len(shows) == 2
    assert shows[0].date == shows[1].date
    assert {show.source_performance_id for show in shows} == {row['source_performance_id'] for row in rows}


@pytest.mark.parametrize('bad_html', [None, _EVENT_HTML, _redirect_html(ident=_OTHER_REDIRECT_ID),
                                      _redirect_html() + _redirect_html(ident=_OTHER_REDIRECT_ID)])
def test_redirect_partial_hold_prevents_stale_reconciliation(monkeypatch, promoter_proxy, bad_html):
    import asyncio
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics

    async def prepare():
        good_url = 'https://www.nextstopcomedy.com/events/unreviewed-good'
        return await _redirect_scraper(monkeypatch, promoter_proxy, {
            _REDIRECT_URL: bad_html,
            good_url: _redirect_html(ident=_OTHER_REDIRECT_ID, node_changes={'url': good_url, 'offers': {'url': good_url}}),
        })
    scraper, _ = asyncio.run(prepare())
    def scrape():
        current_diagnostics().record_fetch_ok()
        return asyncio.run(scraper.scrape_async())
    monkeypatch.setattr(scraper, 'scrape', scrape)
    result = scraper.scrape_with_result()
    assert len(result.shows) == 1
    assert result.fetches_failed > 0
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)
