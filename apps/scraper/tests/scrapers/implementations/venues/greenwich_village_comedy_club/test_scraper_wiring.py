"""Greenwich Village Comedy Club scraper wiring tests."""

import time_machine

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.clients.tessera.instances.greenwich_village import (
    GreenwichVillageTesseraClient,
)
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.data import (
    BroadwayEventData,
)
from laughtrack.scrapers.implementations.venues.greenwich_village_comedy_club.scraper import (
    GreenwichVillageComedyClubScraper,
)


SCRAPING_URL = "https://www.greenwichvillagecomedyclub.com/shows/"


def _club() -> Club:
    club = Club(
        id=3605,
        name="Greenwich Village Comedy Club",
        address="99 MacDougal St, New York, NY 10012",
        website="https://www.greenwichvillagecomedyclub.com",
        popularity=0,
        zip_code="10012",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="greenwich_village_comedy_club",
        source_url=SCRAPING_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_greenwich_tessera_client_uses_greenwich_endpoints():
    client = GreenwichVillageTesseraClient(_club())

    assert client.base_domain == "greenwichvillagecomedyclub.com"
    assert client.api_base_url == "https://tickets.greenwichvillagecomedyclub.com/api/v1/products"
    assert client.origin_url == "https://www.greenwichvillagecomedyclub.com"


def test_greenwich_scraper_registers_dedicated_key_and_client():
    scraper = GreenwichVillageComedyClubScraper(_club())

    assert scraper.key == "greenwich_village_comedy_club"
    assert isinstance(scraper.tessera_client, GreenwichVillageTesseraClient)
    assert scraper._tickets._client is scraper.tessera_client


@time_machine.travel("2026-07-06T12:00:00Z", tick=False)
async def test_get_data_maps_wordpress_show_api_payload(monkeypatch):
    scraper = GreenwichVillageComedyClubScraper(_club())

    payload = [
        {
            "id": 16822,
            "link": "https://www.greenwichvillagecomedyclub.com/shows/the-comedy-lab/",
            "title": {"rendered": "2026-07-19 The Comedy Lab (4:00 pm)"},
            "acf": {
                "date_and_time_of_show": "07/19/2026 4:00 pm",
                "room": "Main Room",
                "hide_show": False,
                "show_description": "<p>Work-it-out room.</p>",
                "show_template": {"post_title": "The Comedy Lab"},
                "headliner": [
                    {"post_title": "Comic One"},
                    {"post_title": "Comic Two"},
                ],
                "additional_artists": "Guest Comic",
            },
        },
        {
            "id": 16823,
            "link": "https://www.greenwichvillagecomedyclub.com/shows/hidden/",
            "acf": {
                "date_and_time_of_show": "07/20/2026 4:00 pm",
                "hide_show": True,
            },
        },
        {
            "id": 16824,
            "link": "https://www.greenwichvillagecomedyclub.com/shows/past/",
            "acf": {
                "date_and_time_of_show": "07/01/2026 4:00 pm",
                "hide_show": False,
                "show_template": {"post_title": "Past Show"},
            },
        },
    ]

    calls = []

    async def fake_fetch_json(url: str):
        calls.append(url)
        return payload if "page=1" in url else []

    async def fake_enrich(events):
        return events

    async def fake_refresh_session_id():
        return True

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper, "_enrich_events_with_tickets", fake_enrich)
    monkeypatch.setattr(scraper.tessera_client, "refresh_session_id", fake_refresh_session_id)

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, BroadwayEventData)
    assert calls == [
        "https://www.greenwichvillagecomedyclub.com/wp-json/wp/v2/shows?per_page=100&page=1",
    ]
    assert len(result.event_list) == 1

    event = result.event_list[0]
    assert event.id == "16822"
    assert event.eventDate == "07/19/2026 4:00 pm"
    assert event.title == "The Comedy Lab"
    assert event.room == "Main Room"
    assert event.mainArtist == ["Comic One", "Comic Two"]
    assert event.additionalArtists == ["Guest Comic"]
    assert event.isTesseraProduct is True
    assert event.show_page_url == "https://www.greenwichvillagecomedyclub.com/shows/the-comedy-lab/"
