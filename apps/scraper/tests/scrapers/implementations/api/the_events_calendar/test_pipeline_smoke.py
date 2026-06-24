"""
Pipeline smoke tests for TheEventsCalendarScraper and TribeEvent.

Exercises get_data() against mocked Tribe Events REST API responses matching
the actual /wp-json/tribe/events/v1/events structure (modelled on the live
Pritchard Laughlin Civic Center API), and unit-tests the TribeEvent.to_show()
transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tribe_events import TribeEvent
from laughtrack.scrapers.implementations.api.the_events_calendar.scraper import TheEventsCalendarScraper
from laughtrack.scrapers.implementations.api.the_events_calendar.data import TribeEventsPageData


API_URL = "https://pritchardlaughlin.com/wp-json/tribe/events/v1/events"


def _club(metadata: dict | None = None) -> Club:
    _c = Club(id=300, name='Pritchard Laughlin Civic Center', address='7033 Glenn Hwy', website='https://pritchardlaughlin.com', popularity=0, zip_code='43725', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='the_events_calendar', scraper_key='the_events_calendar', source_url=API_URL, external_id=None, metadata=metadata or {})
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _raw_event(
    id_="pritchardlaughlin.com?id=6989",
    title="An Evening of Stand-Up Comedy",
    start_date="2099-04-01 19:00:00",
    timezone="America/New_York",
    url="https://pritchardlaughlin.com/event/an-evening-of-stand-up-comedy/",
    cost="$25 – $40",
    cost_values=None,
) -> dict:
    return {
        "global_id": id_,
        "title": title,
        "start_date": start_date,
        "timezone": timezone,
        "url": url,
        "cost": cost,
        "cost_details": {"currency_symbol": "$", "values": cost_values or ["25", "40"]},
        "description": "<p>A night of laughs.</p>",
    }


def _api_response(events: list, total_pages: int = 1) -> dict:
    return {
        "events": events,
        "total": len(events),
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# get_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses the API JSON and returns TribeEventsPageData with events."""
    scraper = TheEventsCalendarScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _raw_event(id_="1", title="Comedy Night"),
            _raw_event(id_="2", title="Tribute Concert"),
        ])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, TribeEventsPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Comedy Night" in titles
    assert "Tribute Concert" in titles


@pytest.mark.asyncio
async def test_get_data_handles_pagination(monkeypatch):
    """get_data() fetches multiple pages when total_pages > 1."""
    scraper = TheEventsCalendarScraper(_club())
    call_count = 0

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        nonlocal call_count
        call_count += 1
        if "page=1" in url:
            return _api_response(
                [_raw_event(id_="1", title="Show A")],
                total_pages=2,
            )
        return _api_response(
            [_raw_event(id_="2", title="Show B")],
            total_pages=2,
        )

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, TribeEventsPageData)
    assert len(result.event_list) == 2
    assert call_count == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_events(monkeypatch):
    """get_data() returns None when the API returns no events."""
    scraper = TheEventsCalendarScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when fetch_json returns an empty dict."""
    scraper = TheEventsCalendarScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_non_numeric_cost(monkeypatch):
    """get_data() preserves non-numeric cost_values like 'varies' verbatim."""
    scraper = TheEventsCalendarScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_raw_event(cost="Varies", cost_values=["varies"])])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].cost_values == ["varies"]


# ---------------------------------------------------------------------------
# Mixed-use venue filtering (event_categories / title patterns) — all OFF by default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_query_appended_when_configured(monkeypatch):
    """event_categories metadata adds &categories= to the API request (server-side filter)."""
    scraper = TheEventsCalendarScraper(_club(metadata={"event_categories": "on-the-spot-improv"}))
    seen_urls = []

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        seen_urls.append(url)
        return _api_response([_raw_event(id_="1", title="On The Spot Improv")])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    await scraper.get_data(API_URL)

    assert seen_urls
    assert "&categories=on-the-spot-improv" in seen_urls[0]


@pytest.mark.asyncio
async def test_category_query_supports_list(monkeypatch):
    """event_categories accepts a list of slugs, joined with commas."""
    scraper = TheEventsCalendarScraper(_club(metadata={"event_categories": ["comedy", "improv"]}))
    seen_urls = []

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        seen_urls.append(url)
        return _api_response([_raw_event(id_="1", title="Comedy Night")])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    await scraper.get_data(API_URL)

    assert "&categories=comedy,improv" in seen_urls[0]


@pytest.mark.asyncio
async def test_no_category_query_by_default(monkeypatch):
    """No &categories= fragment is added when event_categories is unset."""
    scraper = TheEventsCalendarScraper(_club())
    seen_urls = []

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        seen_urls.append(url)
        return _api_response([_raw_event(id_="1", title="Comedy Night")])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    await scraper.get_data(API_URL)

    assert "categories=" not in seen_urls[0]


@pytest.mark.asyncio
async def test_filters_off_by_default_keep_all_events(monkeypatch):
    """With no title filters configured, all events pass through untouched."""
    scraper = TheEventsCalendarScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _raw_event(id_="1", title="On The Spot Improv"),
            _raw_event(id_="2", title="Auditions: On The Spot Improv"),
            _raw_event(id_="3", title="Winnie the Pooh Kids"),
        ])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_include_title_patterns_keeps_only_matches(monkeypatch):
    """include_title_patterns keeps only matching titles."""
    scraper = TheEventsCalendarScraper(
        _club(metadata={"include_title_patterns": r"^On The Spot Improv$"})
    )

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _raw_event(id_="1", title="On The Spot Improv"),
            _raw_event(id_="2", title="Auditions: On The Spot Improv"),
            _raw_event(id_="3", title="Improv Workshop with the On the Spot Improv Team"),
        ])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    titles = [e.title for e in result.event_list]
    assert titles == ["On The Spot Improv"]


@pytest.mark.asyncio
async def test_exclude_title_patterns_drops_matches(monkeypatch):
    """exclude_title_patterns drops matching titles (e.g. auditions/workshops)."""
    scraper = TheEventsCalendarScraper(
        _club(metadata={"exclude_title_patterns": ["Auditions", "Workshop"]})
    )

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _raw_event(id_="1", title="On The Spot Improv"),
            _raw_event(id_="2", title="Auditions: On The Spot Improv"),
            _raw_event(id_="3", title="Improv Workshop with the On the Spot Improv Team"),
        ])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    titles = [e.title for e in result.event_list]
    assert titles == ["On The Spot Improv"]


@pytest.mark.asyncio
async def test_returns_none_when_filters_drop_all(monkeypatch):
    """get_data() returns None when title filters drop every event."""
    scraper = TheEventsCalendarScraper(
        _club(metadata={"include_title_patterns": "Nonexistent Series"})
    )

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_raw_event(id_="1", title="On The Spot Improv")])

    monkeypatch.setattr(TheEventsCalendarScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


# ---------------------------------------------------------------------------
# TribeEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title="An Evening of Stand-Up Comedy",
    start_date="2099-04-01 19:00:00",
    timezone="America/New_York",
    url="https://pritchardlaughlin.com/event/an-evening-of-stand-up-comedy/",
    cost_values=None,
) -> TribeEvent:
    return TribeEvent(
        id="pritchardlaughlin.com?id=6989",
        title=title,
        start_date=start_date,
        timezone=timezone,
        url=url,
        cost="$25 – $40",
        cost_values=cost_values or ["25", "40"],
        description="A night of laughs.",
    )


def test_to_show_returns_show_with_correct_date_and_name():
    """to_show() produces a Show with the correct date and name."""
    event = _make_event(title="Comedy Night", start_date="2099-04-05 20:00:00")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Comedy Night"
    assert show.date.year == 2099
    assert show.date.month == 4
    assert show.date.day == 5


def test_to_show_strips_sold_out_prefix():
    """to_show() strips the 'SOLD OUT!' prefix from the show name."""
    event = _make_event(title="SOLD OUT! Comedy Night")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Comedy Night"
    assert "SOLD OUT" not in show.name


def test_to_show_creates_ticket_from_cost_values():
    """to_show() creates a ticket using the lowest cost_value as price."""
    event = _make_event(cost_values=["25", "40"])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 25.0


def test_to_show_picks_lowest_price_when_cost_values_unsorted():
    """to_show() picks the minimum numeric cost_value even when values are out of order."""
    event = _make_event(cost_values=["40", "25", "55"])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 25.0


def test_to_show_creates_fallback_ticket_on_non_numeric_cost():
    """to_show() still creates a (price-less) ticket when cost_values are non-numeric."""
    event = _make_event(cost_values=["varies"])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when start_date cannot be parsed."""
    event = _make_event(start_date="not-a-date")
    show = event.to_show(_club())

    assert show is None


def test_to_show_sets_sold_out_on_ticket_when_prefix_present():
    """to_show() sets sold_out=True on tickets when SOLD OUT prefix is in title."""
    event = _make_event(title="SOLD OUT! Comedy Night")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].sold_out is True
