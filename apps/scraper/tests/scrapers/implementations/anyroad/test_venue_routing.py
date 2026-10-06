"""Reviewed AnyRoad physical venues, including recurring offsite performances."""

from copy import deepcopy

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.anyroad.scraper import AnyRoadScraper
from laughtrack.scrapers.implementations.anyroad.extractor import extract_anyroad_events


def venue(club_id, name, address):
    return Club(
        id=club_id,
        name=name,
        address=address,
        city="Boston",
        state="MA",
        zip_code="02131",
        timezone="America/New_York",
        website="https://example.com",
        popularity=0,
        phone_number="",
        visible=True,
    )


def configured():
    home = venue(10970, "The Rozzie Square Theater", "18 Corinth Street")
    away = venue(61212, "The Substation", "4228 Washington Street")
    routes = []
    for club, location in [
        (home, "18b Corinth Street, Boston, MA"),
        (away, "The Substation, Washington Street, Roslindale, MA"),
    ]:
        routes.append(
            dict(
                location_info=location,
                club_id=club.id,
                name=club.name,
                address=club.address,
                city=club.city,
                state=club.state,
                postal_code=club.zip_code,
                timezone=club.timezone,
            )
        )
    source = ScrapingSource(
        id=6820,
        club_id=home.id,
        platform="custom",
        scraper_key="anyroad",
        source_url="https://app.anyroad.com/i/plugin/rozziesquaretheater",
        metadata={
            "plugin_id": "rozziesquaretheater",
            "anyroad_venue_routes": dict(
                source_id=6820, plugin_id="rozziesquaretheater", producer_id=73, routes=routes
            ),
        },
    )
    home.active_scraping_source = source
    home.scraping_sources = [source]
    return home, away


def record(location="The Substation, Washington Street, Roslindale, MA"):
    return {
        "id": "102243",
        "attributes": {
            "id": 102243,
            "nameTranslation": "Improv Show",
            "url": "https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/improv-show?lang=en-US",
            "locationInfo": location,
            "unformattedPrice": 25,
            "schedule": {"2027-11-05": {"9:00 AM": 20}},
        },
    }


def test_reviewed_offsite_recurring_events_route_before_conversion():
    home, away = configured()
    scraper = AnyRoadScraper(home)
    events = extract_anyroad_events(
        [record()],
        timezone=home.timezone,
        availability_by_id={"102243": {"2027-11-05": {"8:00pm": 20}, "2027-11-12": {"8:00pm": 0}}},
    )
    # The configured router is shared by extraction and transformation.
    from laughtrack.scrapers.implementations.anyroad.transformer import AnyRoadTransformer

    transformer = AnyRoadTransformer(home)
    if hasattr(scraper, "venue_router"):
        scraper.venue_router.destinations = {home.id: home, away.id: away}
        transformer.venue_router = scraper.venue_router
    shows = [transformer.transform_to_show(event) for event in events]
    assert [show.club_id for show in shows] == [61212, 61212]
    assert all(show.production_company_id == 73 and show.scraped_by_organizer_id == 73 for show in shows)
    assert all(show.room == record()["attributes"]["locationInfo"] for show in shows)
    assert shows[0].tickets[0].price == 25
    assert shows[1].tickets[0].sold_out


def detail(raw, *, location=None, experience_id=None, dates=None):
    import html
    import json

    attrs = raw["attributes"]
    about = dict(id=experience_id or raw["id"], place=attrs["locationInfo"] if location is None else location)
    return (
        '<div data-react-class="Views.Plugins.Tours.Page.About" data-react-props="'
        + html.escape(json.dumps(about), quote=True)
        + '"></div>'
        + '<div data-react-class="Views.Plugins.Tours.Page.Glance" data-react-props="'
        + html.escape(json.dumps({"tour_timezone": "America/New_York"}), quote=True)
        + '"></div>'
        + json.dumps(
            {"tour_availability": {"dates": dates if dates is not None else {"2027-11-05": {"8:00pm": 20}}}},
            separators=(",", ":"),
        )
    )


def setup_pipeline(monkeypatch, raw=None, detail_changes=None):
    home, away = configured()
    raw = raw or record()
    from laughtrack.core.entities.club.handler import ClubHandler

    monkeypatch.setattr(ClubHandler, "get_physical_clubs_by_ids", lambda self, ids: [home, away])
    scraper = AnyRoadScraper(home)

    async def fetch_json(url):
        return {"experiences": {"data": [raw] if "page=1" in url else []}}

    async def fetch_html(url):
        return detail(raw, **(detail_changes or {}))

    monkeypatch.setattr(scraper, "fetch_json", fetch_json)
    monkeypatch.setattr(scraper, "fetch_html", fetch_html)
    return scraper


@pytest.mark.parametrize(
    "location,expected",
    [
        ("18b Corinth Street, Boston, MA", 10970),
        ("The Substation, Washington Street, Roslindale, MA", 61212),
        ("", 10970),
    ],
)
def test_real_pipeline_home_offsite_and_uncertain_blank(monkeypatch, location, expected):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    scraper = setup_pipeline(monkeypatch, record(location))
    first = scraper.scrape_with_result()
    second = scraper.scrape_with_result()
    assert len(first.shows) == len(second.shows) == 1
    assert first.shows[0].club_id == expected
    assert first.shows[0].date == second.shows[0].date
    assert first.shows[0].room == second.shows[0].room == (location or None)
    assert first.is_synthetic and first.production_company_id == 73
    if not location:
        assert first.error and not ScrapingResultProcessor._is_clean_for_reconciliation(first)
    else:
        assert not first.error


@pytest.mark.parametrize(
    "change",
    [
        {"location": "Different Venue, Elsewhere"},
        {"experience_id": "999"},
    ],
)
def test_detail_identity_conflicts_hold_and_block_cleanup(monkeypatch, change):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    scraper = setup_pipeline(monkeypatch, detail_changes=change)
    result = scraper.scrape_with_result()
    assert not result.shows
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)


def test_explicit_unknown_location_is_held(monkeypatch):
    scraper = setup_pipeline(monkeypatch, record("The Substation"))
    result = scraper.scrape_with_result()
    assert not result.shows and result.error


def test_empty_authoritative_detail_does_not_resurrect_placeholder(monkeypatch):
    scraper = setup_pipeline(monkeypatch, detail_changes={"dates": {}})
    assert not scraper.scrape_with_result().shows


@pytest.mark.parametrize("field,value", [("address", "Wrong Street"), ("visible", False), ("status", "closed")])
def test_changed_or_unavailable_destination_is_held(monkeypatch, field, value):
    scraper = setup_pipeline(monkeypatch)
    from laughtrack.core.entities.club.handler import ClubHandler

    home, away = configured()
    setattr(away, field, value)
    monkeypatch.setattr(ClubHandler, "get_physical_clubs_by_ids", lambda self, ids: [home, away])
    result = scraper.scrape_with_result()
    assert not result.shows and result.error


def test_conflicting_routes_and_source_identity_fail_closed(monkeypatch):
    scraper = setup_pipeline(monkeypatch)
    config = scraper.club.source_metadata["anyroad_venue_routes"]
    config["routes"].append(deepcopy(config["routes"][0]))
    assert not scraper.scrape_with_result().shows
    config["routes"].pop()
    config["source_id"] = 1
    result = scraper.scrape_with_result()
    assert not result.shows and result.error


def test_partial_pagination_retains_verified_shows_but_blocks_cleanup(monkeypatch):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    scraper = setup_pipeline(monkeypatch)

    async def fetch_json(url):
        return {"experiences": {"data": [record()]}} if "page=1" in url else None

    monkeypatch.setattr(scraper, "fetch_json", fetch_json)
    result = scraper.scrape_with_result()
    assert len(result.shows) == 1
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)


def test_unconfigured_source_preserves_legacy_conversion_and_input():
    from laughtrack.scrapers.implementations.anyroad.transformer import AnyRoadTransformer

    home, away = configured()
    home.active_scraping_source.metadata.pop("anyroad_venue_routes")
    raw = record()
    before = deepcopy(raw)
    events = extract_anyroad_events([raw], timezone=home.timezone)
    transformer = AnyRoadTransformer(home)
    assert transformer.transform_to_show(events[0]).club_id == home.id
    assert raw == before


@pytest.mark.parametrize(
    "url",
    [
        "https://other.example/i/plugin/rozziesquaretheater/tours/a",
        "https://app.anyroad.com/i/plugin/other/tours/a",
        "http://app.anyroad.com/i/plugin/rozziesquaretheater/tours/a",
    ],
)
def test_wrong_booking_identity_never_fetches_details(monkeypatch, url):
    raw = record()
    raw["attributes"]["url"] = url
    scraper = setup_pipeline(monkeypatch, raw)
    from unittest.mock import AsyncMock

    scraper.fetch_html = AsyncMock()
    result = scraper.scrape_with_result()
    assert not result.shows and result.error
    scraper.fetch_html.assert_not_called()


@pytest.mark.parametrize("kind", ["repeated", "capped", "conflicting"])
def test_unproven_pagination_is_incomplete(monkeypatch, kind):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
    from laughtrack.scrapers.implementations.anyroad import scraper as scraper_module

    scraper = setup_pipeline(monkeypatch)

    async def fetch_json(url):
        raw = record()
        if kind == "conflicting" and "page=2" in url:
            raw["attributes"]["locationInfo"] = "18b Corinth Street, Boston, MA"
        return {"experiences": {"data": [raw]}}

    scraper.fetch_json = fetch_json
    if kind == "capped":
        monkeypatch.setattr(scraper_module, "_MAX_PAGES", 1)
    result = scraper.scrape_with_result()
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)
    if kind == "conflicting":
        assert not result.shows


def test_missing_destination_fails_closed(monkeypatch):
    from laughtrack.core.entities.club.handler import ClubHandler

    scraper = setup_pipeline(monkeypatch)
    monkeypatch.setattr(ClubHandler, "get_physical_clubs_by_ids", lambda self, ids: [])
    result = scraper.scrape_with_result()
    assert not result.shows and result.error


from tests.core.entities.show.test_source_performance_identity import (
    database as persistence_database_fixture,
    handler_for,
)

persistence_database = persistence_database_fixture


@pytest.mark.parametrize("batch_size", [1, 100])
def test_routed_refresh_preserves_show_ticket_and_saved_references(persistence_database, monkeypatch, batch_size):
    from psycopg2.extras import RealDictCursor
    from laughtrack.core.entities.show.handler import ShowHandler

    scraper = setup_pipeline(monkeypatch)
    handler = handler_for(persistence_database)
    # Exercise real room normalization and cross-batch identity, not the fixture stubs.
    handler._suppress_room_matching_club_name = ShowHandler._suppress_room_matching_club_name.__get__(handler)
    handler._collapse_cross_batch_duplicates = ShowHandler._collapse_cross_batch_duplicates.__get__(handler)

    def execute(query, params=None, return_results=False):
        with persistence_database.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall() if return_results else None

    handler.execute_with_cursor = execute
    with persistence_database.cursor() as cursor:
        cursor.execute("CREATE TABLE clubs(id integer PRIMARY KEY, name text)")
        cursor.execute("INSERT INTO clubs VALUES (61212,'The Substation')")
    shows = scraper.scrape_with_result().shows
    result = handler.insert_shows(shows, batch_size=batch_size, scraper_key="anyroad")
    assert result.errors == result.db_errors == result.validation_errors == 0
    show_id = shows[0].id
    with persistence_database.cursor() as cursor:
        cursor.execute("INSERT INTO saved_shows VALUES ('routed-user',%s)", (show_id,))
        cursor.execute("INSERT INTO ticket_purchase_click_events VALUES (1,%s)", (show_id,))
        cursor.execute("SELECT id,purchase_url FROM tickets WHERE show_id=%s", (show_id,))
        original_tickets = cursor.fetchall()
    repeated = scraper.scrape_with_result().shows
    result = handler.insert_shows(repeated, batch_size=batch_size, scraper_key="anyroad")
    assert result.updates == 1 and repeated[0].id == show_id
    with persistence_database.cursor() as cursor:
        cursor.execute("SELECT id,purchase_url FROM tickets WHERE show_id=%s", (show_id,))
        assert cursor.fetchall() == original_tickets
        cursor.execute("SELECT show_id FROM saved_shows WHERE profile_id='routed-user'")
        assert cursor.fetchone() == (show_id,)
        cursor.execute("SELECT show_id FROM ticket_purchase_click_events WHERE id=1")
        assert cursor.fetchone() == (show_id,)
        cursor.execute(
            "SELECT club_id,production_company_id,scraped_by_organizer_id,room FROM shows WHERE id=%s", (show_id,)
        )
        assert cursor.fetchone() == (61212, 73, 73, record()["attributes"]["locationInfo"])


@pytest.mark.parametrize(
    "bad_dates",
    [
        {"2027-11-05": {"not a time": 20}},
        {"2027-11-05": ["8:00pm"]},
        {"2027-11-05": {"8:00pm": {"remaining": 20}}},
        {"2027-11-05": {"8:00pm": 20}, "not a date": {"8:00pm": 20}},
        {"2027-11-05": {"8:00pm": -1}},
    ],
)
def test_malformed_detail_calendar_holds_experience_without_midnight_or_cleanup(monkeypatch, bad_dates):
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    scraper = setup_pipeline(monkeypatch, detail_changes={"dates": bad_dates})
    result = scraper.scrape_with_result()
    assert not result.shows
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)
