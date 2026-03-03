import pytest

from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper
from laughtrack.core.entities.club.model import Club


@pytest.fixture
def club() -> Club:
    return Club(
        id=1,
        name="Test Venue",
        address="",
        website="https://example.com",
        scraping_url="example.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        eventbrite_id="VENUE123",
    )


@pytest.mark.asyncio
async def test_collect_targets_returns_venue_id(club):
    s = EventbriteScraper(club)
    targets = await s.collect_scraping_targets()
    assert targets == ["VENUE123"]


@pytest.mark.asyncio
async def test_collect_targets_empty_when_missing_id(club):
    club.eventbrite_id = None
    with pytest.raises(ValueError):
        EventbriteScraper(club)


class _FakeClient:
    def __init__(self, events):
        self._events = events
        self.called = False
    async def fetch_all_events(self):
        self.called = True
        return list(self._events)


@pytest.mark.asyncio
async def test_get_data_wraps_events_and_handles_empty(monkeypatch, club):
    s = EventbriteScraper(club)

    # Inject fake client
    fake = _FakeClient(events=[
        # use a simple duck-typed object with attributes EventbriteEvent expects
        type("E", (), {"name":"Show","event_url":"https://e/1","start_date":"2025-01-01T20:00:00Z"})()
    ])
    s.eventbrite_client = fake  # type: ignore[assignment]

    # Patch extractor to just echo into page data
    from laughtrack.scrapers.implementations.api.eventbrite import extractor as extractor_mod
    from laughtrack.scrapers.implementations.api.eventbrite.page_data import EventbriteVenueData

    def fake_to_page_data(items):
        # Return container as scraper expects
        return EventbriteVenueData(event_list=items)

    monkeypatch.setattr(extractor_mod.EventbriteExtractor, "to_page_data", staticmethod(fake_to_page_data))

    data = await s.get_data("VENUE123")
    assert data and len(data.event_list) == 1

    # Now return empty list
    s.eventbrite_client = _FakeClient(events=[])  # type: ignore[assignment]
    data2 = await s.get_data("VENUE123")
    assert data2 is None


@pytest.mark.asyncio
async def test_get_data_logs_and_returns_none_on_exception(monkeypatch, club):
    s = EventbriteScraper(club)

    class Boom:
        async def fetch_all_events(self):
            raise RuntimeError("boom")
    s.eventbrite_client = Boom()  # type: ignore[assignment]

    data = await s.get_data("VENUE123")
    assert data is None
