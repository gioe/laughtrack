"""
Pipeline smoke tests for NinkashiScraper and NinkashiEvent.

Covers:
- NinkashiEvent.from_dict() parsing
- NinkashiEvent.to_show() transformation
- NinkashiClient.fetch_events() pagination and error handling
- NinkashiScraper.collect_scraping_targets()
- NinkashiScraper.get_data() with mocked client
- Full transformation pipeline (PageData → Show objects)
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ninkashi import NinkashiEvent, NinkashiTicket
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.ninkashi.scraper import NinkashiScraper
from laughtrack.scrapers.implementations.api.ninkashi.data import NinkashiPageData
from laughtrack.scrapers.implementations.api.ninkashi.extractor import NinkashiExtractor


URL_SITE = "tickets.cttcomedy.com"


def _club() -> Club:
    return Club(
        id=99,
        name="Cheaper Than Therapy",
        address="533 Sutter St",
        website="https://cttcomedy.com",
        scraping_url=URL_SITE,
        popularity=0,
        zip_code="94102",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _raw_event(
    event_id=1001,
    title="Tuesday Night Comedy",
    starts_at="2026-04-07T19:45:00.000-07:00",
    time_zone="America/Los_Angeles",
    tickets=None,
) -> dict:
    if tickets is None:
        tickets = [
            {"name": "General Admission", "price": "15.00", "sold_out": False, "remaining_tickets": 50}
        ]
    return {
        "id": event_id,
        "title": title,
        "starts_at": starts_at,
        "ends_at": "2026-04-07T21:00:00.000-07:00",
        "time_zone": time_zone,
        "tickets_attributes": tickets,
        "venue_name": "Shelton Theater",
        "address_1": "533 Sutter St",
        "city": "San Francisco",
        "state": "CA",
    }


def _make_event(
    event_id=1001,
    title="Tuesday Night Comedy",
    starts_at="2026-04-07T19:45:00.000-07:00",
    time_zone="America/Los_Angeles",
    tickets=None,
) -> NinkashiEvent:
    if tickets is None:
        tickets = [
            NinkashiTicket(price=15.0, sold_out=False, name="General Admission", remaining_tickets=50)
        ]
    return NinkashiEvent(
        id=event_id,
        title=title,
        starts_at=starts_at,
        time_zone=time_zone,
        url_site=URL_SITE,
        tickets_attributes=tickets,
    )


# ---------------------------------------------------------------------------
# NinkashiEvent.from_dict() tests
# ---------------------------------------------------------------------------


def test_from_dict_parses_required_fields():
    """from_dict() correctly parses id, title, starts_at, time_zone."""
    event = NinkashiEvent.from_dict(_raw_event(), URL_SITE)

    assert event.id == 1001
    assert event.title == "Tuesday Night Comedy"
    assert event.starts_at == "2026-04-07T19:45:00.000-07:00"
    assert event.time_zone == "America/Los_Angeles"
    assert event.url_site == URL_SITE


def test_from_dict_parses_ticket_attributes():
    """from_dict() converts tickets_attributes into NinkashiTicket objects."""
    event = NinkashiEvent.from_dict(_raw_event(), URL_SITE)

    assert len(event.tickets_attributes) == 1
    ticket = event.tickets_attributes[0]
    assert ticket.name == "General Admission"
    assert ticket.price == 15.0
    assert ticket.sold_out is False
    assert ticket.remaining_tickets == 50


def test_from_dict_handles_missing_tickets():
    """from_dict() returns empty ticket list when tickets_attributes is absent."""
    raw = _raw_event()
    del raw["tickets_attributes"]
    event = NinkashiEvent.from_dict(raw, URL_SITE)

    assert event.tickets_attributes == []


def test_from_dict_handles_none_tickets():
    """from_dict() returns empty ticket list when tickets_attributes is None."""
    raw = {**_raw_event(), "tickets_attributes": None}
    event = NinkashiEvent.from_dict(raw, URL_SITE)

    assert event.tickets_attributes == []


# ---------------------------------------------------------------------------
# NinkashiEvent.to_show() tests
# ---------------------------------------------------------------------------


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the event title as the name."""
    event = _make_event(title="Sammy Obeid Live")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Sammy Obeid Live"


def test_to_show_parses_iso_datetime_in_venue_timezone():
    """to_show() correctly parses the ISO offset datetime into the venue timezone."""
    # 2026-04-07T19:45:00-07:00 is 19:45 PDT
    event = _make_event(starts_at="2026-04-07T19:45:00.000-07:00", time_zone="America/Los_Angeles")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 7
    assert show.date.hour == 19
    assert show.date.minute == 45


def test_to_show_constructs_ticket_url_from_url_site_and_id():
    """to_show() builds the ticket URL as https://{url_site}/events/{id}."""
    event = _make_event(event_id=1234)
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == f"https://{URL_SITE}/events/1234"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == f"https://{URL_SITE}/events/1234"


def test_to_show_maps_ticket_tiers():
    """to_show() converts each NinkashiTicket tier into a Ticket on the Show."""
    tickets = [
        NinkashiTicket(price=15.0, sold_out=False, name="General Admission", remaining_tickets=50),
        NinkashiTicket(price=25.0, sold_out=True, name="VIP", remaining_tickets=0),
    ]
    event = _make_event(tickets=tickets)
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 2
    types = {t.type for t in show.tickets}
    assert "General Admission" in types
    assert "VIP" in types
    vip = next(t for t in show.tickets if t.type == "VIP")
    assert vip.sold_out is True
    assert vip.price == 25.0


def test_to_show_uses_fallback_ticket_when_no_tiers():
    """to_show() creates a single fallback ticket when tickets_attributes is empty."""
    event = _make_event(tickets=[])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].type == "General Admission"


def test_to_show_returns_none_for_missing_title():
    """to_show() returns None when title is empty."""
    event = _make_event(title="")
    show = event.to_show(_club())

    assert show is None


def test_to_show_returns_none_for_invalid_starts_at():
    """to_show() returns None when starts_at cannot be parsed."""
    event = _make_event(starts_at="not-a-date")
    show = event.to_show(_club())

    assert show is None


def test_to_show_uses_url_override():
    """to_show() uses the url argument as show_page_url when provided."""
    event = _make_event()
    show = event.to_show(_club(), url="https://example.com/custom")

    assert show is not None
    assert show.show_page_url == "https://example.com/custom"


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_url_site():
    """collect_scraping_targets() returns the scraping_url from the club."""
    scraper = NinkashiScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert targets == [URL_SITE]


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_empty_when_no_scraping_url():
    """collect_scraping_targets() returns [] when club.scraping_url is empty."""
    club = _club()
    club.scraping_url = ""
    scraper = NinkashiScraper(club)
    targets = await scraper.collect_scraping_targets()

    assert targets == []


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() wraps fetched events in NinkashiPageData."""
    scraper = NinkashiScraper(_club())
    fake_events = [_make_event(event_id=1), _make_event(event_id=2, title="Show B")]

    async def fake_fetch_events(self, url_site):
        return fake_events

    monkeypatch.setattr(
        "laughtrack.core.clients.ninkashi.client.NinkashiClient.fetch_events",
        fake_fetch_events,
    )

    result = await scraper.get_data(URL_SITE)

    assert isinstance(result, NinkashiPageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the client returns an empty list."""
    scraper = NinkashiScraper(_club())

    async def fake_fetch_events(self, url_site):
        return []

    monkeypatch.setattr(
        "laughtrack.core.clients.ninkashi.client.NinkashiClient.fetch_events",
        fake_fetch_events,
    )

    result = await scraper.get_data(URL_SITE)

    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_client_exception(monkeypatch):
    """get_data() returns None and does not raise when the client throws."""
    scraper = NinkashiScraper(_club())

    async def fake_fetch_events(self, url_site):
        raise RuntimeError("network error")

    monkeypatch.setattr(
        "laughtrack.core.clients.ninkashi.client.NinkashiClient.fetch_events",
        fake_fetch_events,
    )

    result = await scraper.get_data(URL_SITE)

    assert result is None


# ---------------------------------------------------------------------------
# Transformation pipeline smoke test
# ---------------------------------------------------------------------------


def test_transformation_pipeline_produces_shows():
    """Full pipeline: NinkashiPageData → transformation_pipeline → Show objects."""
    club = _club()
    scraper = NinkashiScraper(club)
    events = [_make_event(event_id=1), _make_event(event_id=2, title="Show B")]
    page_data = NinkashiPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check can_transform() and that NinkashiEventTransformer is registered "
        "with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)
