from datetime import datetime

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.lesher_center import LesherCenterEvent
from laughtrack.scrapers.implementations.venues.lesher_center.transformer import (
    LesherCenterTransformer,
)


def _club() -> Club:
    club = Club(
        id=11099,
        name="Lesher Center for the Arts",
        address="1601 Civic Dr",
        website="https://www.lesherartscenter.org/",
        popularity=0,
        zip_code="94596",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )
    club.active_scraping_source = ScrapingSource(
        id=6868,
        club_id=11099,
        platform="custom",
        scraper_key="lesher_center",
        source_url="https://app.spektrix-link.com/clients/lesherartscenter/eventsView.json",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_transformer_creates_comedy_show_with_spektrix_purchase_url():
    event = LesherCenterEvent(
        title="Best of San Francisco Stand-Up Comedy (SEP 2026)",
        date_time=datetime(2026, 9, 19, 20, 15),
        event_id="82201ALMMGMRMBVSDRJDMGQHDVSMGGKDG",
        web_event_id="FMM-32627",
        genre="Comedy and Improv",
        presenter="Force Majeure Media LLC",
        description="Bay Area stand-up comedy.",
        sold_out=False,
    )

    show = LesherCenterTransformer(_club()).transform_to_show(event)

    assert show is not None
    assert show.name == "Best of San Francisco Stand-Up Comedy (SEP 2026)"
    assert show.club_id == 11099
    assert show.date.isoformat() == "2026-09-19T20:15:00-07:00"
    assert show.show_page_url == (
        "https://purchase.lesherartscenter.org/EventAvailability?" "EventId=82201ALMMGMRMBVSDRJDMGQHDVSMGGKDG"
    )
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == show.show_page_url
    assert show.tickets[0].sold_out is False
    assert "Comedy and Improv" in show.description
