"""
Pipeline smoke tests for ZaniesScraper and ZaniesEvent.

Exercises collect_scraping_targets() and get_data() against mocked HTML
pages that match the actual chicago.zanies.com structure, and unit-tests
the ZaniesEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.zanies import ZaniesEvent
from laughtrack.scrapers.implementations.venues.zanies.data import ZaniesPageData
from laughtrack.scrapers.implementations.venues.zanies.extractor import ZaniesExtractor
from laughtrack.scrapers.implementations.venues.zanies.scraper import ZaniesScraper

HOMEPAGE_URL = "https://chicago.zanies.com"
SERIES_URL = (
    "https://chicago.zanies.com/calendar/category/series/"
    "2026-roast-battle/zanies-comedy-club-chicago/chicago-illinois/"
)
SHOW_URL = (
    "https://chicago.zanies.com/show/adam-nate-levine/"
    "zanies-comedy-club-chicago/chicago-illinois/"
)


def _club() -> Club:
    return Club(
        id=999,
        name="Zanies Comedy Club",
        address="1548 N Wells St",
        website="https://chicago.zanies.com",
        scraping_url=HOMEPAGE_URL,
        popularity=0,
        zip_code="60610",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _homepage_html(
    series_urls: list[str] | None = None,
    show_urls: list[str] | None = None,
) -> str:
    """Minimal homepage HTML with configurable series and show links."""
    series_links = "".join(
        f'<a href="{u}">Series</a>' for u in (series_urls or [SERIES_URL])
    )
    show_links = "".join(
        f'<a href="{u}">Show</a>' for u in (show_urls or [SHOW_URL])
    )
    return f"<html><body>{series_links}{show_links}</body></html>"


def _series_html(title: str = "Roast Battle Chicago") -> str:
    """Minimal series page with two future performances."""
    return f"""<html><body>
<h1>{title}</h1>
<ul>
  <li class="row g-0 p-2 rhp-event-series-individual">
    <div class="col-12 col-md-8 rhp-event-series-dates">
      <div class="rhp-event-series-date font0by75 font-weight-bold text-uppercase">
        Thursday, April 03
      </div>
      <div class="rhp-event-series-time font0by75 fontWeight500">
        Doors: 9 pm Show: 9:30 pm
      </div>
    </div>
    <div class="col-12 col-md-4 rhp-event-series-dates-cta">
      <a href="https://www.etix.com/ticket/p/11111111/roast-battle-chicago-zanies-chicago?partner_id=100">Tickets</a>
    </div>
  </li>
  <li class="row g-0 p-2 rhp-event-series-individual">
    <div class="col-12 col-md-8 rhp-event-series-dates">
      <div class="rhp-event-series-date font0by75 font-weight-bold text-uppercase">
        Thursday, April 10
      </div>
      <div class="rhp-event-series-time font0by75 fontWeight500">
        Doors: 9 pm Show: 9:30 pm
      </div>
    </div>
    <div class="col-12 col-md-4 rhp-event-series-dates-cta">
      <a href="https://www.etix.com/ticket/p/22222222/roast-battle-chicago-zanies-chicago?partner_id=100">Tickets</a>
    </div>
  </li>
</ul>
</body></html>"""


def _single_show_html(
    title: str = "Adam Nate Levine",
    date_str: str = "Monday, April 06",
    time_str: str = "Doors: 6 pm Show: 7 pm",
    ticket_id: str = "32563880",
) -> str:
    """Minimal single-show page HTML."""
    return f"""<html><body>
<h1>{title}</h1>
<div class="EventsDateBox">
  <span class = "eventStDate text-uppercase">{date_str}</span>
</div>
<div class="eventDoorStartDate">
  <span class="font0Med75">{time_str}</span>
</div>
<a href="https://www.etix.com/ticket/p/{ticket_id}/test-chicago-zanies-chicago?partner_id=100">Buy Tickets</a>
</body></html>"""


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_series_and_show_urls(monkeypatch):
    """collect_scraping_targets() returns series URLs followed by show URLs."""
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return _homepage_html()

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 2
    assert any("/calendar/category/series/" in t for t in targets)
    assert any("/show/" in t for t in targets)


@pytest.mark.asyncio
async def test_collect_targets_deduplicates_urls(monkeypatch):
    """Duplicate href values on the homepage are deduplicated."""
    html = (
        f'<a href="{SERIES_URL}"><a href="{SERIES_URL}">'
        f'<a href="{SHOW_URL}"><a href="{SHOW_URL}">'
    )
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    targets = await scraper.collect_scraping_targets()
    assert targets.count(SERIES_URL) == 1
    assert targets.count(SHOW_URL) == 1


@pytest.mark.asyncio
async def test_collect_targets_returns_empty_on_no_html(monkeypatch):
    """collect_scraping_targets() returns [] when the homepage fetch fails."""
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    targets = await scraper.collect_scraping_targets()
    assert targets == []


# ---------------------------------------------------------------------------
# get_data() — series URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_series_url_returns_page_data(monkeypatch):
    """get_data() with a series URL returns ZaniesPageData with all performances."""
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return _series_html()

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SERIES_URL)

    assert isinstance(result, ZaniesPageData)
    assert len(result.event_list) == 2
    assert result.event_list[0].title == "Roast Battle Chicago"
    assert result.event_list[0].date_str == "Thursday, April 03"


@pytest.mark.asyncio
async def test_get_data_single_show_url_returns_page_data(monkeypatch):
    """get_data() with a single-show URL returns ZaniesPageData with one event."""
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return _single_show_html()

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    result = await scraper.get_data(SHOW_URL)

    assert isinstance(result, ZaniesPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Adam Nate Levine"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when fetch returns empty HTML."""
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    assert await scraper.get_data(SERIES_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when a page contains no extractable events."""
    scraper = ZaniesScraper(_club())

    async def fake_fetch(self, url: str, **kwargs) -> str:
        return "<html><body><p>No shows scheduled.</p></body></html>"

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fake_fetch)

    assert await scraper.get_data(SHOW_URL) is None


# ---------------------------------------------------------------------------
# ZaniesExtractor unit tests
# ---------------------------------------------------------------------------


def test_extract_series_strips_year_prefix():
    """Series titles like '2026 Roast Battle' are cleaned to 'Roast Battle'."""
    events = ZaniesExtractor.extract_series_events(_series_html("2026 Roast Battle"))
    assert len(events) == 2
    assert events[0].title == "Roast Battle"


def test_extract_series_no_year_prefix_unchanged():
    """Series titles without a year prefix are returned as-is."""
    events = ZaniesExtractor.extract_series_events(_series_html("Gary Vider"))
    assert events[0].title == "Gary Vider"


def test_extract_series_empty_html_returns_empty():
    assert ZaniesExtractor.extract_series_events("") == []


def test_extract_single_show_parses_title_date_time_ticket():
    events = ZaniesExtractor.extract_single_show_events(_single_show_html())
    assert len(events) == 1
    e = events[0]
    assert e.title == "Adam Nate Levine"
    assert e.date_str == "Monday, April 06"
    assert "Doors: 6 pm Show: 7 pm" in e.time_str
    assert "etix.com/ticket/p/32563880" in e.ticket_url


def test_extract_single_show_empty_html_returns_empty():
    assert ZaniesExtractor.extract_single_show_events("") == []


# ---------------------------------------------------------------------------
# ZaniesEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Roast Battle Chicago",
    date_str: str = "Thursday, April 03",
    time_str: str = "Doors: 9 pm Show: 9:30 pm",
    ticket_url: str = "https://www.etix.com/ticket/p/52372512/roast-battle-chicago-zanies-chicago?partner_id=100",
) -> ZaniesEvent:
    return ZaniesEvent(
        title=title,
        date_str=date_str,
        time_str=time_str,
        ticket_url=ticket_url,
    )


def test_to_show_returns_show_with_correct_name():
    show = _make_event(title="Gary Vider").to_show(_club())
    assert show is not None
    assert show.name == "Gary Vider"


def test_to_show_extracts_show_time_not_doors_time():
    """to_show() uses the Show: time, not the Doors: time."""
    show = _make_event(time_str="Doors: 9 pm Show: 9:30 pm").to_show(_club())
    assert show is not None
    assert show.date.hour == 21   # 9:30 PM Chicago local hour
    assert show.date.minute == 30


def test_to_show_parses_7pm_show_time():
    show = _make_event(time_str="Doors: 6 pm Show: 7 pm").to_show(_club())
    assert show is not None
    assert show.date.hour == 19


def test_to_show_creates_etix_ticket():
    ticket_url = "https://www.etix.com/ticket/p/52372512/roast-battle-chicago-zanies-chicago?partner_id=100"
    show = _make_event(ticket_url=ticket_url).to_show(_club())
    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == ticket_url


def test_to_show_returns_none_when_title_missing():
    assert _make_event(title="").to_show(_club()) is None


def test_to_show_returns_none_when_ticket_url_missing():
    assert _make_event(ticket_url="").to_show(_club()) is None


def test_to_show_returns_none_on_unparseable_date():
    assert _make_event(date_str="Not A Date").to_show(_club()) is None


def test_to_show_infers_future_year():
    """Year inference produces a date >= today."""
    from datetime import date

    show = _make_event(
        date_str="Thursday, January 01",
        time_str="Doors: 9 pm Show: 9:30 pm",
    ).to_show(_club())
    assert show is not None
    assert show.date.date() >= date.today()


def test_to_show_returns_none_when_time_unparseable():
    assert _make_event(time_str="").to_show(_club()) is None
