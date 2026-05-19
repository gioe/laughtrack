from datetime import datetime

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.fox_tucson_theatre import FoxTucsonTheatreEvent
from laughtrack.scrapers.implementations.venues.fox_tucson_theatre.transformer import (
    FoxTucsonTheatreTransformer,
)


def _club() -> Club:
    club = Club(
        id=2573,
        name="Fox Tucson Theatre",
        address="17 W Congress St",
        website="https://foxtucson.com",
        popularity=0,
        zip_code="85701",
        phone_number="",
        visible=True,
        timezone="America/Phoenix",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=2573,
        platform="custom",
        scraper_key="fox_tucson_theatre",
        source_url="https://foxtucson.com/events/",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_transformer_creates_show_with_ticket_price_and_spektrix_url():
    event = FoxTucsonTheatreEvent(
        title="Leslie Jones: I'm Hot Tour",
        date_time=datetime(2026, 9, 18, 19, 30),
        show_page_url="https://foxtucson.com/event/leslie-jones/",
        ticket_url="https://foxtucson.com/event/leslie-jones/tickets",
        price_text="$24-$76 all in",
        spektrix_event_url=(
            "https://tickets.foxtucson.com/foxtucsontheatre/website/"
            "EventDetails.aspx?WebEventId=leslie-jones&resize=true"
        ),
        spektrix_instance_ids=["165401"],
    )

    show = FoxTucsonTheatreTransformer(_club()).transform_to_show(event)

    assert show is not None
    assert show.name == "Leslie Jones: I'm Hot Tour"
    assert show.club_id == 2573
    assert show.date.tzinfo is not None
    assert show.show_page_url == "https://foxtucson.com/event/leslie-jones"
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 24.0
    assert show.tickets[0].purchase_url == event.spektrix_event_url
    assert "165401" in show.description
