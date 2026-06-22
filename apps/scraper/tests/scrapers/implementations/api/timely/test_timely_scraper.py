"""Tests for the generic Timely calendar scraper."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
import pytest

from laughtrack.scrapers.implementations.api.timely.extractor import TimelyExtractor
from laughtrack.scrapers.implementations.api.timely.scraper import TimelyScraper


def _club(metadata=None):
    if metadata is None:
        metadata = {"timely_calendar_id": 54755528}
    source = ScrapingSource(
        platform="custom",
        scraper_key="timely",
        source_url="https://events.timely.fun/fwq8raf8/agenda",
        metadata=metadata,
    )
    club = Club(
        id=1,
        name="Jacque's Cabaret",
        address="79 Broadway",
        website="https://www.jacquescabaret.com/v3/",
        zip_code="02116",
        phone_number="",
        popularity=0,
        visible=True,
        timezone="America/New_York",
        city="Boston",
        state="MA",
        scraping_sources=[source],
        active_scraping_source=source,
    )
    return club


def _api_response():
    return {
        "data": {
            "has_next": True,
            "items": {
                "2026-06-26": [
                    {
                        "id": 78058385,
                        "calendar_id": 54755528,
                        "title": "Dollhouse",
                        "custom_url": "dollhouse",
                        "instance": "20260626220000",
                        "start_datetime": "2026-06-26 22:00:00",
                        "timezone": "America/New_York",
                        "description_short": "<p>Join us for our all trans revue!</p>",
                        "cost_external_url": None,
                        "tickets_min_price": "$20",
                        "ticket_type": "entry_fee",
                        "taxonomies": {
                            "taxonomy_venue": [{"title": "Jacque's Cabaret"}],
                        },
                    }
                ],
                "2026-06-27": [
                    {
                        "id": 78111111,
                        "title": "Karaoke",
                        "custom_url": "karaoke-5",
                        "instance": "20260627210000",
                        "start_datetime": "2026-06-27 21:00:00",
                        "timezone": "America/New_York",
                        "description_short": "No Cover",
                        "tickets_min_price": None,
                        "ticket_type": "no_ticket",
                    }
                ],
            },
        }
    }


def test_extract_events_flattens_grouped_timely_response():
    events = TimelyExtractor.extract_events(
        _api_response(),
        calendar_url="https://events.timely.fun/fwq8raf8/agenda",
    )

    assert [event.title for event in events] == ["Dollhouse", "Karaoke"]
    assert TimelyExtractor.has_next_page(_api_response()) is True


def test_event_to_show_uses_timely_event_url_and_positive_price():
    event = TimelyExtractor.extract_events(
        _api_response(),
        calendar_url="https://events.timely.fun/fwq8raf8/agenda",
    )[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Dollhouse"
    assert show.show_page_url == "https://events.timely.fun/fwq8raf8/agenda/event/dollhouse/20260626220000"
    assert show.room == "Jacque's Cabaret"
    assert show.tickets[0].price == 20.0
    assert show.description == "Join us for our all trans revue!"


def test_event_to_show_does_not_treat_no_ticket_zero_as_proven_free():
    event = TimelyExtractor.extract_events(
        _api_response(),
        calendar_url="https://events.timely.fun/fwq8raf8/agenda",
    )[1]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Karaoke"
    assert show.tickets[0].price is None


@pytest.mark.asyncio
async def test_scraper_builds_browser_api_url_and_headers(monkeypatch):
    monkeypatch.setattr(TimelyScraper, "_local_midnight_timestamp", staticmethod(lambda _tz: 1782100800))
    scraper = TimelyScraper(_club())

    targets = await scraper.collect_scraping_targets()
    url = scraper._events_url(calendar_id="54755528", page=2)
    headers = scraper._headers()

    assert targets == [
        "https://events.timely.fun/api/calendars/54755528/events?"
        "group_by_date=1&timezone=America%2FNew_York&view=agenda&"
        "start_date_utc=1782100800&per_page=100&page=1"
    ]
    assert url == (
        "https://events.timely.fun/api/calendars/54755528/events?"
        "group_by_date=1&timezone=America%2FNew_York&view=agenda&"
        "start_date_utc=1782100800&per_page=100&page=2"
    )
    assert headers["x-api-key"] == "c6e5e0363b5925b28552de8805464c66f25ba0ce"
    assert headers["Referer"] == "https://events.timely.fun/fwq8raf8/agenda"


@pytest.mark.asyncio
async def test_missing_calendar_id_returns_no_targets():
    scraper = TimelyScraper(_club(metadata={}))

    assert scraper._calendar_id() is None
    assert await scraper.collect_scraping_targets() == []
