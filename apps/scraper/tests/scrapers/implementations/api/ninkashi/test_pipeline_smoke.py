"""
Pipeline smoke tests for NinkashiScraper and NinkashiEvent.

Covers:
- NinkashiEvent.from_dict() parsing
- NinkashiEvent.to_show() transformation
- NinkashiScraper.collect_scraping_targets()
- NinkashiScraper.get_data() with mocked client
- Full transformation pipeline (PageData → Show objects)

Note: NinkashiClient.fetch_events() pagination is tested separately in the
client tests below (test_fetch_events_paginates, test_fetch_events_stops_on_empty,
test_fetch_events_warns_on_non_list_page2).
"""

import pytest
from datetime import datetime, timedelta, timezone

from laughtrack.core.clients.ninkashi.client import NinkashiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ninkashi import NinkashiEvent, NinkashiTicket
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.ninkashi.scraper import NinkashiScraper
from laughtrack.scrapers.implementations.api.ninkashi.data import NinkashiPageData
from laughtrack.scrapers.implementations.api.ninkashi.extractor import NinkashiExtractor


URL_SITE = "tickets.cttcomedy.com"

# A starts_at value within the 730-day horizon, computed dynamically so tests
# don't fail once a hardcoded date becomes past or crosses the horizon cutoff.
# Client pagination tests that don't care about the horizon use this constant so
# the date-horizon early-stop doesn't interfere with what the test is verifying.
_WITHIN_HORIZON = (
    datetime.now(timezone.utc) + timedelta(days=365)
).strftime("%Y-%m-%d 19:00:00 +0000")

# A starts_at value clearly beyond the 730-day horizon.
_BEYOND_HORIZON = "2099-01-01 19:00:00 +0000"


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
    starts_at="2099-01-01 19:00:00 +0000",
    time_zone="America/Los_Angeles",
    tickets=None,
) -> dict:
    if tickets is None:
        tickets = [
            # Actual Ninkashi API: price is in cents, tier name is in "description"
            {"description": "General Admission", "price": 1500, "sold_out": False, "remaining_tickets": 50}
        ]
    return {
        "id": event_id,
        "title": title,
        # starts_at is nested under event_dates_attributes in the real Ninkashi API
        "event_dates_attributes": [
            {
                "starts_at": starts_at,
                "ends_at": "2026-04-07 21:00:00 -0700",
            }
        ],
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
    starts_at="2026-04-07 19:45:00 -0700",
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
    """from_dict() correctly parses id, title, starts_at from event_dates_attributes, time_zone."""
    event = NinkashiEvent.from_dict(_raw_event(starts_at="2026-06-15 19:45:00 -0700"), URL_SITE)

    assert event.id == 1001
    assert event.title == "Tuesday Night Comedy"
    # starts_at is extracted from event_dates_attributes[0]
    assert event.starts_at == "2026-06-15 19:45:00 -0700"
    assert event.time_zone == "America/Los_Angeles"
    assert event.url_site == URL_SITE


def test_from_dict_parses_ticket_attributes():
    """from_dict() converts tickets_attributes into NinkashiTicket objects.

    Ninkashi API quirks: price is in cents (1500 → $15.00), tier name is in "description".
    """
    event = NinkashiEvent.from_dict(_raw_event(), URL_SITE)

    assert len(event.tickets_attributes) == 1
    ticket = event.tickets_attributes[0]
    assert ticket.name == "General Admission"
    assert ticket.price == 15.0   # 1500 cents → $15.00
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


def test_from_dict_handles_missing_event_dates():
    """from_dict() sets starts_at to '' when event_dates_attributes is absent or empty."""
    raw_absent = {k: v for k, v in _raw_event().items() if k != "event_dates_attributes"}
    event_absent = NinkashiEvent.from_dict(raw_absent, URL_SITE)
    assert event_absent.starts_at == ""

    raw_empty = {**_raw_event(), "event_dates_attributes": []}
    event_empty = NinkashiEvent.from_dict(raw_empty, URL_SITE)
    assert event_empty.starts_at == ""

    # to_show() must return None for both cases (empty starts_at fails parsing)
    assert event_absent.to_show(_club()) is None
    assert event_empty.to_show(_club()) is None


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
    """to_show() correctly parses the Ninkashi datetime string into the venue timezone."""
    # "2026-04-07 19:45:00 -0700" is 19:45 PDT
    event = _make_event(starts_at="2026-04-07 19:45:00 -0700", time_zone="America/Los_Angeles")
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


# ---------------------------------------------------------------------------
# NinkashiClient.fetch_events() unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_events_paginates_until_partial_page(monkeypatch):
    """fetch_events() accumulates events across pages and stops when a page is smaller than the first-page size."""
    client = NinkashiClient(_club())
    per_page = NinkashiClient.PER_PAGE

    # Page 1: full page (per_page events), page 2: partial (2 events) → stop after page 2
    page_1 = [_raw_event(event_id=i, title=f"Show {i}", starts_at=_WITHIN_HORIZON) for i in range(per_page)]
    page_2 = [_raw_event(event_id=per_page, starts_at=_WITHIN_HORIZON), _raw_event(event_id=per_page + 1, starts_at=_WITHIN_HORIZON)]
    pages = [page_1, page_2]
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return pages[idx] if idx < len(pages) else []

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    assert len(events) == per_page + 2
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_fetch_events_stops_on_empty_page(monkeypatch):
    """fetch_events() stops pagination when an empty list is returned."""
    client = NinkashiClient(_club())
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        call_count[0] += 1
        return []

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    assert events == []
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_fetch_events_warns_on_non_list_mid_pagination(monkeypatch):
    """fetch_events() logs a warning and returns partial results when page 2 returns a non-list."""
    client = NinkashiClient(_club())
    per_page = NinkashiClient.PER_PAGE

    page_1 = [_raw_event(event_id=i, starts_at=_WITHIN_HORIZON) for i in range(per_page)]
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return page_1
        return {"error": "rate limit exceeded"}  # non-list on page 2

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    # Should return the events from page 1 and stop
    assert len(events) == per_page
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_fetch_events_uses_actual_page_size_not_per_page(monkeypatch):
    """fetch_events() stops when a page is smaller than the actual first-page response size.

    Regression test: the Ninkashi API for Cheaper Than Therapy returns 105 events per page,
    not 100 (PER_PAGE). The old code compared len(response) < PER_PAGE (105 < 100 = False),
    causing infinite pagination. The fix records page_size from the first response.
    """
    client = NinkashiClient(_club())
    actual_api_page_size = 105  # API returns more than PER_PAGE=100

    # Page 1: 105 events (full API page), page 2: 3 events (partial) → stop after page 2
    page_1 = [_raw_event(event_id=i, title=f"Show {i}", starts_at=_WITHIN_HORIZON) for i in range(actual_api_page_size)]
    page_2 = [_raw_event(event_id=actual_api_page_size + i, starts_at=_WITHIN_HORIZON) for i in range(3)]
    pages = [page_1, page_2]
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return pages[idx] if idx < len(pages) else []

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    assert len(events) == actual_api_page_size + 3
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_fetch_events_stops_at_max_pages(monkeypatch):
    """fetch_events() stops at MAX_PAGES even if the API keeps returning full pages."""
    client = NinkashiClient(_club())
    per_page = NinkashiClient.PER_PAGE
    max_pages = NinkashiClient.MAX_PAGES
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        call_count[0] += 1
        # always return a full page so the partial-page stop condition never fires;
        # use _WITHIN_HORIZON so the date-horizon stop condition also doesn't fire
        return [_raw_event(event_id=call_count[0] * 1000 + i, starts_at=_WITHIN_HORIZON) for i in range(per_page)]

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    assert call_count[0] == max_pages
    assert len(events) == per_page * max_pages


@pytest.mark.asyncio
async def test_fetch_events_filters_past_events(monkeypatch):
    """fetch_events() excludes events whose starts_at is in the past."""
    client = NinkashiClient(_club())

    past_event = _raw_event(event_id=1, title="Old Show", starts_at="2020-01-01 19:00:00 +0000")
    future_event = _raw_event(event_id=2, title="Future Show", starts_at="2027-01-01 19:00:00 +0000")
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        call_count[0] += 1
        # Page 1: mixed past/future; page 2: empty → stops pagination
        if call_count[0] == 1:
            return [past_event, future_event]
        return []

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    assert len(events) == 1
    assert events[0].title == "Future Show"


@pytest.mark.asyncio
async def test_fetch_events_stops_on_duplicate_page(monkeypatch):
    """fetch_events() stops when page 2 returns the same event IDs as page 1.

    Regression test for CTT (tickets.cttcomedy.com): the Ninkashi API for this
    venue ignores the 'page' parameter and returns identical event IDs on every
    page. Without deduplication the loop runs to MAX_PAGES=50, making 50 HTTP
    requests and ingesting 5250 duplicate records. The fix detects a fully-duplicate
    page and stops immediately.
    """
    client = NinkashiClient(_club())
    per_page = NinkashiClient.PER_PAGE

    # Simulate an API that returns the same page regardless of the page param.
    same_page = [_raw_event(event_id=i, starts_at=_WITHIN_HORIZON) for i in range(per_page)]
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        call_count[0] += 1
        return same_page

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    # Page 1 events are included; page 2 is detected as duplicate and stops pagination
    assert len(events) == per_page
    assert call_count[0] == 2  # fetched page 1, detected dupe on page 2, stopped


@pytest.mark.asyncio
async def test_fetch_events_stops_at_date_horizon(monkeypatch):
    """fetch_events() stops pagination and excludes events beyond DATE_HORIZON_DAYS.

    Regression test for CTT (tickets.cttcomedy.com): the venue pre-books hundreds
    of recurring open-mic slots years in advance. MAX_PAGES=50 fired on every run
    because the API keeps returning full pages of distant-future events. The fix
    stops paginating as soon as any event on a page exceeds the horizon, and those
    events are excluded from the result.
    """
    client = NinkashiClient(_club())

    within_horizon = _raw_event(event_id=1, title="Near Show", starts_at=_WITHIN_HORIZON)
    beyond_horizon = _raw_event(event_id=2, title="Far Show", starts_at=_BEYOND_HORIZON)
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        call_count[0] += 1
        # Page 1: one within-horizon + one beyond-horizon event.
        # If horizon stop works, there should be no page 2 request.
        if call_count[0] == 1:
            return [within_horizon, beyond_horizon]
        return [_raw_event(event_id=99, title="Should Not Appear", starts_at=_WITHIN_HORIZON)]

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    # Beyond-horizon event excluded; within-horizon event included
    assert len(events) == 1
    assert events[0].title == "Near Show"
    # Pagination stopped after page 1 — no page 2 requested
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_fetch_events_includes_all_within_horizon_events_from_horizon_page(monkeypatch):
    """All within-horizon events on a page are included even if a beyond-horizon event is present.

    The loop processes every event on the page before checking the horizon flag — it does
    not short-circuit on the first beyond-horizon event. This test places the beyond-horizon
    event in the middle of the page to verify events after it are still collected.
    """
    client = NinkashiClient(_club())

    page = [
        _raw_event(event_id=1, title="Near A", starts_at=_WITHIN_HORIZON),
        _raw_event(event_id=2, title="Far",    starts_at=_BEYOND_HORIZON),
        _raw_event(event_id=3, title="Near B", starts_at=_WITHIN_HORIZON),
    ]
    call_count = [0]

    async def fake_fetch_json(self, url, **kwargs):
        call_count[0] += 1
        return page if call_count[0] == 1 else []

    monkeypatch.setattr(NinkashiClient, "fetch_json", fake_fetch_json)

    events = await client.fetch_events(URL_SITE)

    titles = {e.title for e in events}
    assert "Near A" in titles
    assert "Near B" in titles
    assert "Far" not in titles
    assert call_count[0] == 1  # stopped after page 1
