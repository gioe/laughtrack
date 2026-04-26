import pytest

from laughtrack.core.entities.event.broadway import BroadwayEvent
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.ticket.model import Ticket


def make_club() -> Club:
    _c = Club(id=1, name='Broadway Comedy Club', address='318 W 53rd St, New York, NY 10019', website='https://www.broadwaycomedyclub.com', popularity=10, zip_code='10019', phone_number='(212) 757-2323', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.broadwaycomedyclub.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_from_dict_and_to_show_success():
    # Given the sample JSON payload for a BroadwayEvent
    data = {
        "id": "18155",
        "eventDate": "08/30/2025 9:30 pm",
        "additionalInformation": "",
        "mainArtist": ["Gigi Klein", "Jared Waters", "Vannessa Jackson", "Aaron Berg"],
        "additionalArtists": [],
        "venue": "Broadway Comedy Club",
        "image": "https://dcljq95dq4enn.cloudfront.net/wp-content/uploads/2022/09/purple-stage.jpg",
        "isTesseraProduct": True,
        "externalLink": "https://www.broadwaycomedyclub.com/events/18155",
        "externalLinkButtonText": "Buy Tickets",
        "doors": "",
        "buyNowButtonText": "",
        "tags": [],
        "ages": "21+",
    }

    # When we build the entity and convert to Show
    event = BroadwayEvent.from_dict(data)
    club = make_club()
    show = event.to_show(club, enhanced=False)

    # Then we have a valid Show with expected fields
    assert show is not None
    assert show.name == "Gigi Klein"  # main artist first entry becomes show name
    assert show.club_id == club.id
    assert show.room == data["venue"]
    assert show.show_page_url == data["externalLink"]

    # Datetime parsing (America/New_York) and lineup length
    assert show.date.tzinfo is not None
    assert len(show.lineup) == len(data["mainArtist"])  # additionalArtists empty in sample


def test_to_show_fallback_ticket_from_external_link():
    data = {
        "id": "18155",
        "eventDate": "08/30/2025 7:00 pm",
        "additionalInformation": "",
        "mainArtist": ["Headliner A"],
        "additionalArtists": [],
        "venue": "Broadway Comedy Club",
        "image": "",
        "isTesseraProduct": False,
        "externalLink": "https://www.broadwaycomedyclub.com/events/18155",
        "externalLinkButtonText": "",
        "doors": "",
        "buyNowButtonText": "",
        "tags": [],
        "ages": "",
    }

    event = BroadwayEvent.from_dict(data)
    show = event.to_show(make_club(), enhanced=False)

    assert show is not None
    assert len(show.tickets) == 1
    t = show.tickets[0]
    assert isinstance(t, Ticket)
    assert t.purchase_url == data["externalLink"]
    assert t.type == "General Admission"
    assert t.price == 0.0


def test_to_show_uses_tessera_ticket_data_when_present():
    data = {
        "id": "18156",
        "eventDate": "08/31/2025 8:00 pm",
        "additionalInformation": "",
        "mainArtist": ["Headliner B"],
        "additionalArtists": [],
        "venue": "Broadway Comedy Club",
        "image": "",
        "isTesseraProduct": True,
        "externalLink": "",
        "externalLinkButtonText": "",
        "doors": "",
        "buyNowButtonText": "",
        "tags": [],
        "ages": "",
    }

    event = BroadwayEvent.from_dict(data)

    class DummyTicketData:
        def to_ticket(self):
            return Ticket(price=25.0, purchase_url="https://tickets.example/18156", type="General Admission")

    event._ticket_data = DummyTicketData()
    show = event.to_show(make_club(), enhanced=False)

    assert show is not None
    assert len(show.tickets) == 1
    t = show.tickets[0]
    assert t.price == 25.0
    assert t.purchase_url == "https://tickets.example/18156"


def test_to_show_builds_description_with_parts():
    data = {
        "id": "18157",
        "eventDate": "09/01/2025 9:00 pm",
        "additionalInformation": "A special showcase",
        "mainArtist": ["Showcase Crew"],
        "additionalArtists": [],
        "venue": "Broadway Comedy Club",
        "image": "",
        "isTesseraProduct": False,
        "externalLink": "https://www.broadwaycomedyclub.com/events/18157",
        "externalLinkButtonText": "",
        "doors": "8:30 PM",
        "buyNowButtonText": "",
        "tags": [],
        "ages": "21+",
    }

    event = BroadwayEvent.from_dict(data)
    show = event.to_show(make_club(), enhanced=False)

    assert show is not None
    assert "A special showcase" in (show.description or "")
    assert "Doors: 8:30 PM" in (show.description or "")
    assert "Ages: 21+" in (show.description or "")

