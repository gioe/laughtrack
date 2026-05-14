"""Pipeline tests for the generic City Winery API scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.city_winery import CityWineryEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.city_winery.data import CityWineryPageData
from laughtrack.scrapers.implementations.api.city_winery.scraper import CityWineryScraper


def _club() -> Club:
    club = Club(
        id=2420,
        name="City Winery - New York City",
        address="25 11th Ave",
        website="https://citywinery.com/pages/events/new-york-city",
        popularity=0,
        zip_code="10011",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="city_winery",
        source_url="https://citywinery.com/pages/events/new-york-city",
        metadata={"location": "New York City", "genre": "Comedy"},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _raw_event(
    *,
    event_id: str = "evt-1",
    slug: str = "dl-hughley-edxoly",
    name: str = "D.L. Hughley",
    start: str = "2026-08-07T23:00:00.000Z",
    sale_status: str = "onSale",
    availability_indicator: str = "green",
    starting_price=48,
) -> dict:
    return {
        "_id": event_id,
        "url": slug,
        "name": name,
        "image": "https://s3.example.test/dl-hughley.jpg",
        "start": start,
        "end": "2026-08-08T01:30:00.000Z",
        "locationName": "Main Stage, City Winery NYC",
        "locationStreet": "25 11th Ave",
        "locationCity": "New York, NY",
        "locationPostal": "10011",
        "locationCountry": "US",
        "currency": "USD",
        "timezone": "America/New_York",
        "seoSettings": {
            "tags": ["Main Stage", "Comedy"],
            "description": "City Winery NYC presents D.L. Hughley live.",
        },
        "startingPrice": starting_price,
        "saleStatus": sale_status,
        "availabilityIndicator": availability_indicator,
        "attributes": {
            "location": "New York City",
            "stage": "Main Stage",
            "primary_genre": "Comedy",
        },
        "groups": [{"name": "Tickets", "tickets": ["ticket-1"]}],
    }


def test_event_to_show_maps_city_winery_fields():
    event = CityWineryEvent.from_dict(_raw_event())

    assert event is not None
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "D.L. Hughley"
    assert show.show_page_url == "https://tickets.citywinery.com/event/dl-hughley-edxoly"
    assert show.description == "City Winery NYC presents D.L. Hughley live."
    assert show.room == "Main Stage"
    assert show.date.year == 2026
    assert show.date.month == 8
    assert show.date.day == 7
    assert show.date.hour == 19
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 48.0
    assert show.tickets[0].purchase_url == show.show_page_url
    assert show.tickets[0].type == "General Admission (USD)"
    assert show.tickets[0].sold_out is False
    assert "Comedy" in show.supplied_tags


def test_event_to_show_marks_sold_out_from_status_and_availability():
    status_event = CityWineryEvent.from_dict(
        _raw_event(event_id="evt-2", slug="updating-toqz59", sale_status="soldOut")
    )
    availability_event = CityWineryEvent.from_dict(
        _raw_event(event_id="evt-3", slug="tony-rock-jrhm6a", availability_indicator="red")
    )

    assert status_event is not None
    assert availability_event is not None
    assert status_event.to_show(_club()).tickets[0].sold_out is True
    assert availability_event.to_show(_club()).tickets[0].sold_out is True


def test_event_handles_missing_optional_fields():
    raw = _raw_event(starting_price=None)
    raw.pop("seoSettings")
    raw.pop("image")
    raw.pop("attributes")

    event = CityWineryEvent.from_dict(raw)
    assert event is not None

    show = event.to_show(_club())
    assert show is not None
    assert show.description == ""
    assert show.room == "Main Stage, City Winery NYC"
    assert show.tickets[0].price == 0.0


def test_transformation_pipeline_produces_shows():
    event = CityWineryEvent.from_dict(_raw_event(name="Tony Rock", slug="tony-rock-2r6agq"))
    assert event is not None

    scraper = CityWineryScraper(_club())
    shows = scraper.transformation_pipeline.transform(CityWineryPageData(event_list=[event]))

    assert len(shows) == 1
    assert isinstance(shows[0], Show)
    assert shows[0].name == "Tony Rock"


@pytest.mark.asyncio
async def test_get_data_paginates_by_total_events_not_page_length():
    scraper = CityWineryScraper(_club())
    calls: list[int] = []
    pages = {
        0: {
            "data": {
                "total_events": 46,
                "event_data": [
                    _raw_event(event_id=f"first-{i}", slug=f"first-{i}") for i in range(20)
                ],
            }
        },
        16: {
            "data": {
                "total_events": 46,
                "event_data": [
                    _raw_event(event_id=f"second-{i}", slug=f"second-{i}") for i in range(16)
                ],
            }
        },
        32: {
            "data": {
                "total_events": 46,
                "event_data": [
                    _raw_event(event_id=f"third-{i}", slug=f"third-{i}") for i in range(10)
                ],
            }
        },
    }

    async def fake_fetch_events_page(*, location: str, skip: int):
        assert location == "New York City"
        calls.append(skip)
        return pages.get(skip)

    scraper._fetch_events_page = fake_fetch_events_page

    data = await scraper.get_data("New York City")

    assert data is not None
    assert calls == [0, 16, 32]
    assert len(data.event_list) == 46


@pytest.mark.asyncio
async def test_get_data_stops_cleanly_on_404_after_results():
    scraper = CityWineryScraper(_club())
    calls: list[int] = []

    async def fake_fetch_events_page(*, location: str, skip: int):
        calls.append(skip)
        if skip == 0:
            return {"data": {"total_events": 99, "event_data": [_raw_event()]}}
        return None

    scraper._fetch_events_page = fake_fetch_events_page

    data = await scraper.get_data("New York City")

    assert data is not None
    assert calls == [0, 16]
    assert len(data.event_list) == 1


def test_dl_hughley_multi_show_dates_remain_distinct():
    events = [
        CityWineryEvent.from_dict(
            _raw_event(event_id="dl-1", slug="dl-hughley-edxoly", start="2026-08-07T23:00:00.000Z")
        ),
        CityWineryEvent.from_dict(
            _raw_event(event_id="dl-2", slug="dl-hughley-sat", start="2026-08-08T23:00:00.000Z")
        ),
        CityWineryEvent.from_dict(
            _raw_event(event_id="dl-3", slug="dl-hughley-sun", start="2026-08-09T23:00:00.000Z")
        ),
    ]

    shows = [event.to_show(_club()) for event in events if event is not None]

    assert [show.date.date().isoformat() for show in shows if show is not None] == [
        "2026-08-07",
        "2026-08-08",
        "2026-08-09",
    ]
