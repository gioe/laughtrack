"""
Pipeline smoke tests for ElfsightScraper and ElfsightEvent.

Exercises the boot→token→events flow in get_data() against mocked responses,
the comedy_filter allowlist, ticket-URL extraction, and the
ElfsightEvent.to_show() transformation path.
"""

import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.elfsight import ElfsightEvent
from laughtrack.scrapers.implementations.api.elfsight.scraper import ElfsightScraper
from laughtrack.scrapers.implementations.api.elfsight.data import ElfsightPageData
from laughtrack.scrapers.implementations.api.elfsight.extractor import ElfsightExtractor

WIDGET_PID = "619cbb71-bc8f-4451-898d-bc03284f431c"
PAGE_URL = "https://www.eclecticboxsf.com/event-calendar"
FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def _club(comedy_filter: bool = False, widget_pid: str = WIDGET_PID) -> Club:
    c = Club(id=99, name="Eclectic Box SF", address="446 Valencia St", website="https://www.eclecticboxsf.com/", popularity=0, zip_code="94103", phone_number="", visible=True, timezone="America/Los_Angeles")
    meta = {"widget_pid": widget_pid}
    if comedy_filter:
        meta["comedy_filter"] = True
    c.active_scraping_source = ScrapingSource(id=1, club_id=c.id, platform="custom", scraper_key="elfsight", source_url=PAGE_URL, external_id=None, metadata=meta)
    c.scraping_sources = [c.active_scraping_source]
    return c


def _payload():
    return _load("events.json")["payload"]


# ---------------------------------------------------------------------------
# ElfsightExtractor
# ---------------------------------------------------------------------------


def test_extract_events_parses_all_when_no_filter():
    events = ElfsightExtractor.extract_events(_payload(), PAGE_URL, comedy_filter=False)
    assert len(events) == 4
    assert {e.name for e in events} == {
        "The BOAT Improv Jam Showcase",
        "Twilight Zone Parody Series",
        "BICONIC FILM FESTIVAL",
        "All Day Comedy Marathon",
    }


def test_comedy_filter_drops_non_comedy():
    """comedy_filter keeps comedy/parody events and drops the film festival."""
    events = ElfsightExtractor.extract_events(_payload(), PAGE_URL, comedy_filter=True)
    names = {e.name for e in events}
    assert "The BOAT Improv Jam Showcase" in names   # 'improv'
    assert "Twilight Zone Parody Series" in names     # 'parody'
    assert "All Day Comedy Marathon" in names         # 'comedy'/'stand-up'
    assert "BICONIC FILM FESTIVAL" not in names        # no comedy keyword


def test_ticket_url_extracted_from_description_href():
    events = ElfsightExtractor.extract_events(_payload(), PAGE_URL)
    boat = next(e for e in events if e.name == "The BOAT Improv Jam Showcase")
    assert boat.ticket_url == "https://events.humanitix.com/the-boat-showcase"


def test_ticket_url_prefers_button_link():
    events = ElfsightExtractor.extract_events(_payload(), PAGE_URL)
    parody = next(e for e in events if e.name == "Twilight Zone Parody Series")
    assert parody.ticket_url == "https://tickets.example.com/twilight"


def test_extract_events_returns_empty_for_non_list():
    assert ElfsightExtractor.extract_events({}, PAGE_URL) == []  # type: ignore[arg-type]
    assert ElfsightExtractor.extract_events(None, PAGE_URL) == []


def test_extract_events_skips_event_missing_name_or_start():
    payload = [
        {"id": "1", "name": "", "start": {"dateTime": "2026-06-28T19:00:00-07:00"}},
        {"id": "2", "name": "No Start", "start": {"date": None, "dateTime": None}},
        {"id": "3", "name": "Good", "start": {"dateTime": "2026-06-28T19:00:00-07:00"}},
    ]
    events = ElfsightExtractor.extract_events(payload, PAGE_URL)
    assert [e.name for e in events] == ["Good"]


# ---------------------------------------------------------------------------
# ElfsightEvent.to_show()
# ---------------------------------------------------------------------------


def _event(**kw) -> ElfsightEvent:
    base = dict(name="The BOAT Improv Jam Showcase", start_iso="2026-06-28T19:00:00-07:00", page_url=PAGE_URL, description_html="An improv jam.", ticket_url="https://events.humanitix.com/the-boat-showcase", image_url="")
    base.update(kw)
    return ElfsightEvent(**base)


def test_to_show_basic_fields():
    show = _event().to_show(_club())
    assert show is not None
    assert show.name == "The BOAT Improv Jam Showcase"
    assert show.date.year == 2026 and show.date.month == 6 and show.date.day == 28
    assert show.date.hour == 19
    assert show.show_page_url == PAGE_URL


def test_to_show_uses_ticket_url_for_purchase():
    show = _event().to_show(_club())
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://events.humanitix.com/the-boat-showcase"


def test_to_show_falls_back_to_page_url_when_no_ticket():
    show = _event(ticket_url="").to_show(_club())
    assert show.tickets[0].purchase_url == PAGE_URL


def test_to_show_strips_html_description():
    show = _event(description_html="<p>An <b>improv</b> jam.</p>").to_show(_club())
    assert show.description == "An improv jam."


def test_to_show_all_day_event_pins_to_club_timezone():
    show = _event(start_iso="2026-08-15").to_show(_club())
    assert show is not None
    assert show.date.year == 2026 and show.date.month == 8 and show.date.day == 15
    assert show.date.tzinfo is not None


def test_to_show_returns_none_for_unparseable_date():
    assert _event(start_iso="not-a-date").to_show(_club()) is None


# ---------------------------------------------------------------------------
# _parse_boot / collect_scraping_targets / get_data
# ---------------------------------------------------------------------------


def test_parse_boot_extracts_token_and_source():
    boot = _load("boot.json")
    # fixture uses a placeholder widget key; remap to the test pid
    boot["data"]["widgets"][WIDGET_PID] = boot["data"]["widgets"].pop("WIDGETPID")
    token, source = ElfsightScraper._parse_boot(boot, WIDGET_PID)
    assert token == "test.jwt.token"
    assert source == "test-source-uuid"


def test_parse_boot_returns_empty_for_garbage():
    assert ElfsightScraper._parse_boot(None, WIDGET_PID) == ("", "")
    assert ElfsightScraper._parse_boot({"data": {}}, WIDGET_PID) == ("", "")


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_widget_pid():
    scraper = ElfsightScraper(_club())
    assert await scraper.collect_scraping_targets() == [WIDGET_PID]


@pytest.mark.asyncio
async def test_collect_scraping_targets_empty_without_widget_pid():
    scraper = ElfsightScraper(_club(widget_pid=""))
    assert await scraper.collect_scraping_targets() == []


@pytest.mark.asyncio
async def test_get_data_boots_then_fetches_events(monkeypatch):
    """get_data() calls boot for the token/source, then the events API."""
    scraper = ElfsightScraper(_club(comedy_filter=True))

    boot = _load("boot.json")
    boot["data"]["widgets"][WIDGET_PID] = boot["data"]["widgets"].pop("WIDGETPID")
    events_resp = _load("events.json")

    async def fake_fetch_json(self, url: str, **kwargs):
        if "/p/boot/" in url:
            return boot
        return events_resp

    monkeypatch.setattr(ElfsightScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data(WIDGET_PID)
    assert isinstance(result, ElfsightPageData)
    # comedy_filter on → film festival dropped, improv + comedy marathon kept
    names = {e.name for e in result.event_list}
    assert "The BOAT Improv Jam Showcase" in names
    assert "BICONIC FILM FESTIVAL" not in names


@pytest.mark.asyncio
async def test_get_data_returns_none_when_boot_lacks_token(monkeypatch):
    scraper = ElfsightScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return {"data": {"widgets": {}}}

    monkeypatch.setattr(ElfsightScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    assert await scraper.get_data(WIDGET_PID) is None


@pytest.mark.asyncio
async def test_full_pipeline_transformation_produces_shows(monkeypatch):
    scraper = ElfsightScraper(_club())

    boot = _load("boot.json")
    boot["data"]["widgets"][WIDGET_PID] = boot["data"]["widgets"].pop("WIDGETPID")
    events_resp = _load("events.json")

    async def fake_fetch_json(self, url: str, **kwargs):
        return boot if "/p/boot/" in url else events_resp

    monkeypatch.setattr(ElfsightScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    page_data = await scraper.get_data(WIDGET_PID)
    assert isinstance(page_data, ElfsightPageData)
    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) == 4
    assert any(s.name == "The BOAT Improv Jam Showcase" for s in shows)
