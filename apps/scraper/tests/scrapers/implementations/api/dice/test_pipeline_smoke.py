import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.dice import DiceEvent
from laughtrack.scrapers.implementations.api.dice.data import DicePageData
from laughtrack.scrapers.implementations.api.dice.scraper import DiceScraper


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "color_club_events.json"


def _club(metadata: dict | None = None) -> Club:
    club = Club(
        id=999,
        name="Color Club",
        address="4146 N Elston Ave, Chicago, IL 60618",
        website="https://www.colorclub.events",
        popularity=0,
        zip_code="60618",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="dice",
        scraper_key="dice",
        source_url="https://www.colorclub.events/calendar",
        metadata=metadata
        or {
            "dice_api_key": "test-api-key",
            "dice_partner_id": "d285d692",
            "dice_venue_id": "14681",
            "dice_venue_name": "Color Club",
            "dice_tags": "type:comedy",
        },
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_dice_event_converts_ticketed_and_linkout_events_to_shows():
    payload = _payload()
    club = _club()

    events = [DiceEvent.from_api_response(item) for item in payload["data"]]
    shows = [event.to_show(club) for event in events]

    assert [show.name for show in shows] == [
        "Kate Renegade, Toddo, Life in Public",
        "Lesbian Market",
    ]
    assert [show.date.tzinfo is not None for show in shows] == [True, True]
    assert shows[0].show_page_url == "https://link.dice.fm/hec6178f0e0f"
    assert shows[0].tickets[0].price == 15.00
    assert shows[0].tickets[0].sold_out is False
    assert shows[1].show_page_url.startswith("https://www.eventbrite.com/e/")
    assert shows[1].tickets[0].price == 0


@pytest.mark.asyncio
async def test_dice_scraper_uses_metadata_filters_and_aggregates_next_page(monkeypatch):
    club = _club()
    scraper = DiceScraper(club)
    calls: list[str] = []
    payload = _payload()
    next_event = {
        **payload["data"][0],
        "id": "next-page-event",
        "name": "Second Page Event",
        "date": "2026-06-22T01:00:00Z",
    }

    async def fake_fetch_json(url: str, **kwargs):
        calls.append(url)
        if "page[number]=2" in url:
            return {"data": [next_event], "links": {}}
        return payload

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    targets = await scraper.collect_scraping_targets()
    page = await scraper.get_data(targets[0])

    assert "filter%5Bvenue_ids%5D%5B%5D=14681" in targets[0]
    assert "filter%5Btags%5D%5B%5D=type%3Acomedy" in targets[0]
    assert "types=linkout%2Cevent" in targets[0]
    assert isinstance(page, DicePageData)
    assert [event.name for event in page.event_list] == [
        "Kate Renegade, Toddo, Life in Public",
        "Lesbian Market",
        "Second Page Event",
    ]
    assert page.next_url is None
    assert calls[0] == targets[0]
    assert calls[1].startswith("https://partners-endpoint.dice.fm/api/v2/events?")
    assert "page[number]=2" in calls[1]
