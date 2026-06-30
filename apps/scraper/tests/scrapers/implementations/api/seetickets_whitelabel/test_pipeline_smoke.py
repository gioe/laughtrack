from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.data import (
    SeeTicketsWhitelabelPageData,
)
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.extractor import (
    SeeTicketsWhitelabelExtractor,
)
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.scraper import (
    SeeTicketsWhitelabelScraper,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _club(metadata=None):
    c = Club(
        id=11479,
        name="The Port Comedy Club",
        address="813 S Broadway, Baltimore, MD 21231",
        website="https://portcomedy.com/",
        popularity=0,
        zip_code="21231",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=c.id,
        platform="custom",
        scraper_key="seetickets_whitelabel",
        source_url="https://wl.eventim.us/?afflky=ThePortComedyClub",
        external_id=None,
        metadata={
            "profile_id": "15127815",
            "whitelabel_key": "ThePortComedyClub",
            **(metadata or {}),
        },
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def test_extract_events_parses_event_cards_from_recorded_fixture():
    html = (FIXTURES / "eventim_page.html").read_text()

    events = SeeTicketsWhitelabelExtractor.extract_events(html, base_url="https://wl.eventim.us")

    assert [event.name for event in events] == ["New Material Night", "Captain's Quarters"]
    assert events[0].event_id == "679796"
    assert events[0].start_date == "June 28 2026"
    assert events[0].ticket_url == "https://wl.eventim.us/event/New-Material-Night/679796?afflky=ThePortComedyClub"


def test_event_to_show_uses_date_and_ticket_url():
    html = (FIXTURES / "eventim_page.html").read_text()
    event = SeeTicketsWhitelabelExtractor.extract_events(html, base_url="https://wl.eventim.us")[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "New Material Night"
    assert show.date.year == 2026 and show.date.month == 6 and show.date.day == 28
    assert show.date.tzinfo is not None
    assert show.tickets[0].purchase_url == event.ticket_url


@pytest.mark.asyncio
async def test_get_data_fetches_whitelabel_pages_from_browser(monkeypatch):
    scraper = SeeTicketsWhitelabelScraper(_club({"max_months": 2, "page_size": 15}))
    html = (FIXTURES / "eventim_page.html").read_text()
    calls = []

    class FakeBrowser:
        async def fetch_seetickets_whitelabel_pages(self, **kwargs):
            calls.append(kwargs)
            return [html]

        async def close(self):
            return None

    monkeypatch.setattr(
        "laughtrack.scrapers.implementations.api.seetickets_whitelabel.scraper.PlaywrightBrowser",
        lambda *args, **kwargs: FakeBrowser(),
    )

    # get_data now enriches each event with its detail-page time via fetch_html;
    # stub it to an empty page so this test stays offline and the events keep
    # their date-only (midnight) values.
    async def _no_detail(url, **kwargs):
        return ""

    monkeypatch.setattr(scraper, "fetch_html", _no_detail)

    result = await scraper.get_data("https://wl.eventim.us/?afflky=ThePortComedyClub")

    assert isinstance(result, SeeTicketsWhitelabelPageData)
    assert len(result.event_list) == 2
    assert calls == [
        {
            "profile_id": "15127815",
            "whitelabel_key": "ThePortComedyClub",
            "affiliate_key": "ThePortComedyClub",
            "base_url": "https://wl.eventim.us",
            "max_months": 2,
            "page_size": 15,
        }
    ]


@pytest.mark.asyncio
async def test_collect_scraping_targets_requires_profile_and_whitelabel_keys():
    assert await SeeTicketsWhitelabelScraper(_club()).collect_scraping_targets() == [
        "https://wl.eventim.us/?afflky=ThePortComedyClub"
    ]
    assert await SeeTicketsWhitelabelScraper(_club({"profile_id": ""})).collect_scraping_targets() == []


def test_parse_detail_start_datetime_reads_timed_json_ld_startdate():
    html = (FIXTURES / "event_detail.html").read_text()

    assert SeeTicketsWhitelabelScraper._parse_detail_start_datetime(html) == "2026-06-29T20:00"


def test_parse_detail_start_datetime_ignores_date_only_startdate():
    html = (
        '<script type="application/ld+json">'
        '{"@type": "Event", "name": "X", "startDate": "2026-06-29", '
        '"url": "https://wl.eventim.us/event/X/1"}'
        "</script>"
    )

    assert SeeTicketsWhitelabelScraper._parse_detail_start_datetime(html) is None


def test_event_to_show_uses_detail_page_time_when_present():
    event = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )[0]
    event.start_datetime = "2026-06-29T20:00"

    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 20 and show.date.minute == 0
    assert show.date.tzinfo is not None


def test_event_to_show_falls_back_to_midnight_without_detail_time():
    event = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.date.hour == 0 and show.date.minute == 0


@pytest.mark.asyncio
async def test_attach_detail_page_times_enriches_and_degrades(monkeypatch):
    scraper = SeeTicketsWhitelabelScraper(_club())
    detail_html = (FIXTURES / "event_detail.html").read_text()
    events = SeeTicketsWhitelabelExtractor.extract_events(
        (FIXTURES / "eventim_page.html").read_text(), base_url="https://wl.eventim.us"
    )
    # First event's detail fetch fails (degrade to midnight); second returns the
    # timed JSON-LD page (enriched).
    fetched = []

    async def _fetch(url, **kwargs):
        fetched.append((url, kwargs.get("skip_js_fallback")))
        if url == events[0].ticket_url:
            raise RuntimeError("blocked")
        return detail_html

    monkeypatch.setattr(scraper, "fetch_html", _fetch)

    await scraper._attach_detail_page_times(events)

    assert events[0].start_datetime == ""  # failed fetch → degraded
    assert events[1].start_datetime == "2026-06-29T20:00"  # enriched
    # Convention #296: detail fetches opt out of the Playwright fallback.
    assert all(skip is True for _, skip in fetched)
