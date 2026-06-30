"""Pipeline smoke tests for Venetian entertainment AEM scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.venetian_entertainment.extractor import (
    VenetianEntertainmentExtractor,
)
from laughtrack.scrapers.implementations.venues.venetian_entertainment.scraper import (
    VenetianEntertainmentScraper,
)

SOURCE_URL = "https://www.venetianlasvegas.com/entertainment.html"
GRAPHQL_URL = (
    "https://www.venetianlasvegas.com/graphql/execute.json/"
    "venetian/allEntertainment%3Btoday%3D2026-06-29"
)


def _club(
    *,
    club_id: int = 4826,
    name: str = "Palazzo Theatre at The Venetian Resort",
    venue_category: str = "the-palazzo-theatre",
) -> Club:
    club = Club(
        id=club_id,
        name=name,
        address="3355 S Las Vegas Blvd",
        website="https://www.venetianlasvegas.com/entertainment.html",
        popularity=0,
        zip_code="89109",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
        city="Las Vegas",
        state="NV",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="venetian_entertainment",
        source_url=SOURCE_URL,
        metadata={"venue_category": venue_category},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _payload() -> dict:
    return {
        "data": {
            "entertainmentList": {
                "items": [
                    {
                        "__typename": "EntertainmentModel",
                        "_path": "/content/dam/vlv/content-fragments/events/entertainment/mark-normand",
                        "title": "Mark Normand",
                        "shortDescription": "A stand-up comedy performance.",
                        "categories": [
                            "venetianlasvegas-com:events/type/comedy",
                            "venetianlasvegas-com:events/type/shows",
                            "venetianlasvegas-com:events/location/the-palazzo-theatre",
                        ],
                        "dates": ["2026-12-04"],
                        "times": "7:30 PM",
                        "primaryText": "Buy Tickets",
                        "primaryLinkUrl": (
                            "https://www.ticketmaster.com/mark-normand-tickets/"
                            "artist/1793032?venueId=189346"
                        ),
                        "secondaryLink": {
                            "_path": "/content/venetian/us/en/entertainment/mark-normand"
                        },
                    },
                    {
                        "__typename": "EntertainmentModel",
                        "_path": "/content/dam/vlv/content-fragments/events/entertainment/ralph-barbosa",
                        "title": "Ralph Barbosa",
                        "shortDescription": "Comedy at The Venetian Theatre.",
                        "categories": [
                            "venetianlasvegas-com:events/type/comedy",
                            "venetianlasvegas-com:events/location/the-venetian-theatre",
                        ],
                        "dates": ["2026-08-28", "2026-08-29"],
                        "times": "8:00 PM",
                        "primaryText": "Buy Tickets",
                        "primaryLinkUrl": (
                            "https://www.ticketmaster.com/ralph-barbosa-tickets/"
                            "artist/2723483?venueId=189345"
                        ),
                        "secondaryLink": {
                            "_path": "/content/venetian/us/en/entertainment/ralph-barbosa"
                        },
                    },
                    {
                        "__typename": "EntertainmentModel",
                        "_path": "/content/dam/vlv/content-fragments/events/entertainment/clay-walker",
                        "title": "Clay Walker",
                        "shortDescription": "Country music.",
                        "categories": [
                            "venetianlasvegas-com:events/type/music",
                            "venetianlasvegas-com:events/location/the-venetian-theatre",
                        ],
                        "dates": ["2026-12-05"],
                        "times": "8:30 PM",
                        "primaryText": "Buy Tickets",
                        "primaryLinkUrl": "https://www.ticketmaster.com/clay-walker-tickets/artist/775012",
                    },
                    {
                        "__typename": "EntertainmentModel",
                        "_path": "/content/dam/vlv/content-fragments/events/entertainment/mrs-doubtfire",
                        "title": "Mrs. Doubtfire",
                        "shortDescription": "Touring musical comedy.",
                        "categories": [
                            "venetianlasvegas-com:events/type/comedy",
                            "venetianlasvegas-com:events/location/the-venetian-theatre",
                        ],
                        "dates": ["2026-07-22"],
                        "times": "Varies",
                        "primaryText": "Buy Tickets",
                        "primaryLinkUrl": (
                            "https://www.ticketmaster.com/mrs-doubtfire-touring-tickets/"
                            "artist/3007777?venueId=189345"
                        ),
                    },
                ]
            }
        }
    }


def test_extract_events_filters_to_comedy_for_configured_venue_category():
    events = VenetianEntertainmentExtractor.extract_events(
        _payload(),
        venue_category="the-palazzo-theatre",
    )

    assert len(events) == 1
    assert events[0].name == "Mark Normand"
    assert events[0].start_date == "2026-12-04 19:30:00"
    assert events[0].show_page_url == "https://www.venetianlasvegas.com/entertainment/mark-normand.html"
    assert events[0].ticket_url == "https://www.ticketmaster.com/mark-normand-tickets/artist/1793032?venueId=189346"


def test_extract_events_expands_multiple_dates_for_venetian_theatre():
    events = VenetianEntertainmentExtractor.extract_events(
        _payload(),
        venue_category="the-venetian-theatre",
    )

    assert [event.name for event in events] == ["Ralph Barbosa", "Ralph Barbosa"]
    assert [event.start_date for event in events] == [
        "2026-08-28 20:00:00",
        "2026-08-29 20:00:00",
    ]


@pytest.mark.asyncio
async def test_get_data_fetches_persisted_graphql_query_with_today(monkeypatch):
    scraper = VenetianEntertainmentScraper(_club())
    fetched = []

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        assert kwargs == {}
        fetched.append(url)
        return _payload()

    monkeypatch.setattr(VenetianEntertainmentScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.venues.venetian_entertainment.scraper.date",
        type("FrozenDate", (), {"today": staticmethod(lambda: __import__("datetime").date(2026, 6, 29))}),
    )

    result = await scraper.get_data(SOURCE_URL)

    assert result is not None
    assert fetched == [GRAPHQL_URL]
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Mark Normand"


def test_venetian_event_transforms_to_show_with_fallback_ticket():
    event = VenetianEntertainmentExtractor.extract_events(
        _payload(),
        venue_category="the-palazzo-theatre",
    )[0]

    show = event.to_show(_club(), enhanced=False)

    assert show is not None
    assert show.name == "Mark Normand"
    assert show.date.isoformat() == "2026-12-04T19:30:00-08:00"
    assert show.show_page_url == "https://www.venetianlasvegas.com/entertainment/mark-normand.html"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == (
        "https://www.ticketmaster.com/mark-normand-tickets/artist/1793032?venueId=189346"
    )
    assert show.tickets[0].price is None


def test_scraper_class_has_correct_key():
    assert VenetianEntertainmentScraper.key == "venetian_entertainment"
