"""
Pipeline smoke tests for MultipassScraper and MultipassEvent.

Exercises get_data() against mocked HTML matching the live
``denvercomedy.multipass.com`` card structure, the year-inference date parser,
and the MultipassEvent.to_show() transformation path.
"""

from datetime import datetime, timedelta

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.multipass import (
    MultipassEvent,
    parse_multipass_datetime,
)
from laughtrack.scrapers.implementations.api.multipass.scraper import MultipassScraper
from laughtrack.scrapers.implementations.api.multipass.data import MultipassPageData
from laughtrack.scrapers.implementations.api.multipass.extractor import (
    MultipassExtractor,
)

LISTING_URL = "https://denvercomedy.multipass.com/"


def _club() -> Club:
    _c = Club(id=999, name='Dude, IDK Studios', address='2801 N Downing St', website='https://www.dudeidkstudios.com', popularity=0, zip_code='80205', phone_number='', visible=True, timezone='America/Denver')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='multipass', source_url=LISTING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _card(
    title: str = "Dude, IDK presents MACEY ISAACS Looks Alive Tour",
    slug: str = "/maceyisaacs",
    datetime_text: str = "Fri Jul 3 &bull; 8 PM",
    price: str = "$18.06",
) -> str:
    """Render a Multipass eventCard2026 card matching the live HTML structure."""
    return f"""
<DIV class="section eventCard2026" onclick="window.location.href='{slug}'">
  <div class="xsquareimage"><img src="https://multipassimages.s3.us-east-2.amazonaws.com/events/3351/small.jpg" /></div>
  <DIV class="eventText">
    <DIV class="title truncate-text">
      <A HREF="{slug}" style="text-decoration: none;">{title}</A>
    </DIV>
    <DIV class="eventline datetime">
      <i class="fa-solid fa-clock"></i> {datetime_text}
    </DIV>
    <DIV class="eventline location">
      <i class="fa-solid fa-map-pin"></i> Dude, Idk Studios<BR>
    </DIV>
    <DIV class="_action">
      <HR>
      <DIV class="row">
        <DIV class="col-6"><span class="eventPrice pc">{price}</span></DIV>
        <DIV class="col-6"><A HREF="{slug}" class="btn btn-primary actionButton">Get Tickets</A></DIV>
      </DIV>
    </DIV>
  </DIV>
</DIV>"""


def _listing_page(cards: list[str]) -> str:
    return f"<html><body><div class='events'>{''.join(cards)}</div></body></html>"


def _future_card_text(days_ahead: int, time_text: str = "7 PM") -> str:
    """Card datetime text for a real future date, e.g. "Sat Jul 11 &bull; 7 PM".

    The get_data() path runs the extractor against the wall clock (no ``now``
    injection point), and the year-less card text is weekday-pinned by
    ``_infer_year`` — so the text must be derived from an actual upcoming date
    or the card past-drops once the hardcoded date passes (TASK-3586).
    """
    d = datetime.now() + timedelta(days=days_ahead)
    return f"{d:%a} {d:%b} {d.day} &bull; {time_text}"


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    scraper = MultipassScraper(_club())
    html = _listing_page([
        _card(title="Dude, IDK presents MACEY ISAACS Looks Alive Tour", slug="/maceyisaacs", datetime_text=_future_card_text(30)),
        _card(title="Good Night Denver!", slug="/goodnightdenver", datetime_text=_future_card_text(60, "8 PM"), price="$23.47"),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(MultipassScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LISTING_URL)

    assert isinstance(result, MultipassPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Dude, IDK presents MACEY ISAACS Looks Alive Tour" in titles
    assert "Good Night Denver!" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    scraper = MultipassScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(MultipassScraper, "fetch_html", fake_fetch_html)
    assert await scraper.get_data(LISTING_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    scraper = MultipassScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No events at the moment</p></body></html>"

    monkeypatch.setattr(MultipassScraper, "fetch_html", fake_fetch_html)
    assert await scraper.get_data(LISTING_URL) is None


@pytest.mark.asyncio
async def test_collect_targets_returns_single_listing_url():
    scraper = MultipassScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert "denvercomedy.multipass.com" in targets[0]


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


def test_extractor_builds_absolute_urls_and_price():
    html = _listing_page([_card(slug="/maceyisaacs", price="$28.87")])
    # Inject now so the default card's "Fri Jul 3" (weekday-pinned to 2026)
    # never falls past the extractor's past-event cutoff (TASK-3585).
    events = MultipassExtractor.extract_events(html, LISTING_URL, now=datetime(2026, 6, 25))

    assert len(events) == 1
    assert events[0].show_url == "https://denvercomedy.multipass.com/maceyisaacs"
    assert events[0].price == 28.87


def test_extractor_handles_missing_price():
    html = _listing_page([_card(slug="/freeshow", price="")])
    events = MultipassExtractor.extract_events(html, LISTING_URL, now=datetime(2026, 6, 25))
    assert len(events) == 1
    assert events[0].price is None


def test_extractor_skips_card_without_datetime():
    bad = """
<DIV class="section eventCard2026">
  <DIV class="title"><A HREF="/x">Test Show</A></DIV>
</DIV>"""
    events = MultipassExtractor.extract_events(f"<html><body>{bad}</body></html>", LISTING_URL)
    assert len(events) == 0


def test_extractor_skips_card_with_unparseable_datetime():
    html = _listing_page([_card(datetime_text="Some day soon")])
    events = MultipassExtractor.extract_events(html, LISTING_URL)
    assert len(events) == 0


def test_extractor_filters_past_events():
    """Multipass static HTML carries past + future cards; only upcoming survive."""
    now = datetime(2026, 6, 25)
    html = _listing_page([
        _card(title="Old Show", slug="/old", datetime_text="Fri Apr 4 &bull; 7 PM"),       # 2025-04-04, past
        _card(title="Future Show", slug="/future", datetime_text="Sat Jul 11 &bull; 7 PM"),  # 2026-07-11, upcoming
    ])
    events = MultipassExtractor.extract_events(html, LISTING_URL, now=now)
    assert len(events) == 1
    assert events[0].title == "Future Show"


# ---------------------------------------------------------------------------
# Date parsing / year inference
# ---------------------------------------------------------------------------


def test_parse_datetime_infers_year_from_weekday():
    # 2026-07-03 is a Friday; with 'now' in June 2026 the year resolves to 2026.
    now = datetime(2026, 6, 25)
    assert parse_multipass_datetime("Fri Jul 3 • 8 PM", now=now) == "2026-07-03T20:00"


def test_parse_datetime_handles_minutes_and_pm():
    now = datetime(2026, 6, 25)
    assert parse_multipass_datetime("Sat Jul 25 • 7:30 PM", now=now) == "2026-07-25T19:30"


def test_parse_datetime_rolls_over_to_next_year():
    # Late December "now"; a January date should resolve to the following year.
    now = datetime(2026, 12, 20)
    parsed = parse_multipass_datetime("Fri Jan 15 • 8 PM", now=now)
    assert parsed is not None
    assert parsed.startswith("2027-01-15")


def test_parse_datetime_returns_none_on_garbage():
    assert parse_multipass_datetime("not a date") is None
    assert parse_multipass_datetime("") is None


# ---------------------------------------------------------------------------
# MultipassEvent.to_show() tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Dude, IDK presents MACEY ISAACS",
    start_iso: str = "2026-07-11T19:00",
    show_url: str = "https://denvercomedy.multipass.com/maceyisaacs",
    price=28.87,
) -> MultipassEvent:
    return MultipassEvent(title=title, start_iso=start_iso, show_url=show_url, price=price)


def test_to_show_sets_name_and_parses_datetime():
    show = _make_event().to_show(_club())
    assert show is not None
    assert show.name == "Dude, IDK presents MACEY ISAACS"
    assert show.date.hour == 19
    assert show.date.minute == 0


def test_to_show_creates_ticket_with_price():
    show = _make_event(price=28.87).to_show(_club())
    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://denvercomedy.multipass.com/maceyisaacs"
    assert show.tickets[0].price == 28.87


def test_to_show_returns_none_when_title_missing():
    assert _make_event(title="").to_show(_club()) is None


def test_to_show_returns_none_when_show_url_missing():
    assert _make_event(show_url="").to_show(_club()) is None


def test_to_show_returns_none_on_invalid_iso():
    assert _make_event(start_iso="not-a-date").to_show(_club()) is None
