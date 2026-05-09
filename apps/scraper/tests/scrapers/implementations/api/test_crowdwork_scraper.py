"""Tests for the generic Crowdwork/Fourthwall scraper."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.crowdwork.scraper import (
    CrowdworkPageData,
    GenericCrowdworkScraper,
)
from laughtrack.scrapers.implementations.venues.io_theater.data import IOTheaterPageData
from laughtrack.scrapers.implementations.venues.io_theater.scraper import IOTheaterScraper
from laughtrack.scrapers.implementations.venues.logan_square_improv.scraper import (
    LoganSquareImprovScraper,
)
from laughtrack.scrapers.implementations.venues.philly_improv_theater.scraper import (
    PhillyImprovTheaterScraper,
)
from laughtrack.scrapers.implementations.venues.rails_comedy.scraper import RailsComedyScraper
from laughtrack.scrapers.implementations.venues.the_backline.scraper import TheBacklineScraper


def _club(scraper_key: str = "crowdwork") -> Club:
    club = Club(
        id=999,
        name="Crowdwork Venue",
        address="",
        website="https://example.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="crowdwork",
        scraper_key=scraper_key,
        source_url="https://crowdwork.com/api/v2/example/shows",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _show(name: str, timezone: str = "Central Time (US & Canada)") -> dict:
    return {
        "name": name,
        "url": f"https://www.crowdwork.com/e/{name.lower().replace(' ', '-')}",
        "timezone": timezone,
        "dates": ["2026-06-01T20:00:00.000-05:00"],
        "cost": {"formatted": "$12"},
        "description": {"body": f"<p>{name}</p>"},
        "badges": {"spots": None},
    }


async def test_generic_crowdwork_handles_list_and_dict_payloads(monkeypatch):
    scraper = GenericCrowdworkScraper(_club())
    responses = [
        {"status": 200, "type": "success", "data": [_show("List Show")]},
        {"status": 200, "type": "success", "data": {"dict-show": _show("Dict Show")}},
    ]

    async def fake_fetch_json(url):
        return responses.pop(0)

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    list_result = await scraper.get_data("https://example.com/list")
    dict_result = await scraper.get_data("https://example.com/dict")

    assert isinstance(list_result, CrowdworkPageData)
    assert isinstance(dict_result, CrowdworkPageData)
    assert [event.name for event in list_result.event_list] == ["List Show"]
    assert [event.name for event in dict_result.event_list] == ["Dict Show"]


def test_crowdwork_venue_keys_resolve_to_generic_scraper():
    expected = {
        "philly_improv_theater": PhillyImprovTheaterScraper,
        "rails_comedy": RailsComedyScraper,
        "the_backline": TheBacklineScraper,
        "io_theater": IOTheaterScraper,
        "logan_square_improv": LoganSquareImprovScraper,
    }

    for scraper_key, scraper_cls in expected.items():
        scraper = scraper_cls(_club(scraper_key))
        assert issubclass(scraper_cls, GenericCrowdworkScraper)
        assert scraper.key == scraper_key
        assert len(scraper.transformation_pipeline.transformers) == 1


async def test_crowdwork_subclasses_keep_venue_page_data(monkeypatch):
    scraper = IOTheaterScraper(_club("io_theater"))

    async def fake_fetch_json(url):
        return {"status": 200, "type": "success", "data": [_show("Venue Show")]}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://example.com/io")

    assert isinstance(result, IOTheaterPageData)
    assert result.event_list[0].timezone == "America/Chicago"
