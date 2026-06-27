"""Tests for the generic Crowdwork/Fourthwall scraper."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.crowdwork.scraper import (
    CrowdworkPageData,
    GenericCrowdworkScraper,
)
from laughtrack.app.scraper_resolver import ScraperResolver


def _club(metadata: dict | None = None, timezone: str = "America/Chicago") -> Club:
    club = Club(
        id=999,
        name="Crowdwork Venue",
        address="",
        website="https://example.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone=timezone,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="crowdwork",
        scraper_key="crowdwork",
        source_url="https://crowdwork.com/api/v2/example/shows",
        metadata=metadata or {},
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
    scraper = GenericCrowdworkScraper(_club())

    assert scraper.key == "crowdwork"
    assert ScraperResolver().get("crowdwork") is GenericCrowdworkScraper
    assert len(scraper.transformation_pipeline.transformers) == 1


async def test_generic_crowdwork_normalises_rails_timezone_from_metadata(monkeypatch):
    scraper = GenericCrowdworkScraper(_club(metadata={"rails_to_iana": True}))

    async def fake_fetch_json(url):
        return {"status": 200, "type": "success", "data": [_show("Venue Show")]}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://example.com/io")

    assert isinstance(result, CrowdworkPageData)
    assert result.event_list[0].timezone == "America/Chicago"


async def test_generic_crowdwork_uses_metadata_default_timezone(monkeypatch):
    scraper = GenericCrowdworkScraper(_club(metadata={"default_timezone": "America/New_York"}))

    async def fake_fetch_json(url):
        show = _show("Default TZ Show", timezone="")
        show.pop("timezone")
        return {"status": 200, "type": "success", "data": [show]}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://example.com/phit")

    assert result is not None
    assert result.event_list[0].timezone == "America/New_York"


async def test_exclude_title_patterns_drops_classes(monkeypatch):
    """exclude_title_patterns drops class/workshop items, keeps public shows.

    Models Very Good Improv (TASK-3330), whose Crowdwork /all feed mixes course
    registrations with its public open jam.
    """
    scraper = GenericCrowdworkScraper(_club(metadata={"exclude_title_patterns": ["improv 1", "improv 2", "workshop"]}))

    async def fake_fetch_json(url):
        return {
            "status": 200,
            "type": "success",
            "data": [
                _show("VGI Improv 201 Spring 2026 - Mon 6:30-9:30pm"),
                _show("VGI Improv 101 Spring 2026 - Mon 7-9pm"),
                _show("Love the way you play - summer workshop series"),
                _show("Very Good Improv Jam!"),
                _show("Very Good Improv - Spring 2026 - Student Showcase!"),
            ],
        }

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://crowdwork.com/api/v2/verygoodimprov/all")
    assert isinstance(result, CrowdworkPageData)
    names = sorted({e.name for e in result.event_list})
    assert names == [
        "Very Good Improv - Spring 2026 - Student Showcase!",
        "Very Good Improv Jam!",
    ]


async def test_include_title_patterns_keeps_only_matches(monkeypatch):
    """include_title_patterns keeps only items whose title matches an allowlisted substring."""
    scraper = GenericCrowdworkScraper(_club(metadata={"include_title_patterns": ["jam", "showcase"]}))

    async def fake_fetch_json(url):
        return {
            "status": 200,
            "type": "success",
            "data": [
                _show("Improv 101 Class"),
                _show("Friday Night Jam"),
                _show("Spring Student Showcase"),
            ],
        }

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://example.com/all")
    assert isinstance(result, CrowdworkPageData)
    assert sorted({e.name for e in result.event_list}) == ["Friday Night Jam", "Spring Student Showcase"]


async def test_no_title_filter_keeps_everything(monkeypatch):
    """With no filter metadata, every item is kept (existing /shows venues unaffected)."""
    scraper = GenericCrowdworkScraper(_club())

    async def fake_fetch_json(url):
        return {"status": 200, "type": "success", "data": [_show("Improv 101 Class"), _show("Open Jam")]}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://example.com/shows")
    assert isinstance(result, CrowdworkPageData)
    assert sorted({e.name for e in result.event_list}) == ["Improv 101 Class", "Open Jam"]
