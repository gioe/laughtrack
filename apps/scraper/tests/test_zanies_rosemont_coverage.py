"""Rosemont full-calendar contract, verified against RHP monthCustom.js."""

import json
from datetime import date
from urllib.parse import parse_qs

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event import zanies as event_module
from laughtrack.scrapers.implementations.venues.zanies.scraper import ZaniesScraper
from laughtrack.utilities.domain.show.utils import ShowUtils

ROOT = "https://rosemont.zanies.com"
CALENDAR = ROOT + "/calendar/?view=month"
DETAIL = ROOT + "/show/patrick-warburton-special-event-3/zanies-comedy-club-rosemont/rosemont-illinois/"
LATER = ROOT + "/show/josh-blue-special-event-3/zanies-comedy-club-rosemont/rosemont-illinois/"
WIDGET = f"""<input id="adminAjaxURL" value="{ROOT}/wp-admin/admin-ajax.php">
<input id="evPostPerPage" value="10000">
<div id="eventCalendar" class="mainCalendar" widget="true" widget-venues="8389"></div>"""


@pytest.fixture
def scraper(monkeypatch):
    class Today(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 8)

    monkeypatch.setattr(event_module, "date", Today)
    club = Club(
        id=4648,
        name="Zanies Comedy Club - Rosemont",
        address="5437 Park Pl",
        website=ROOT,
        popularity=0,
        zip_code="60018",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    source = ScrapingSource(club_id=4648, platform="custom", scraper_key="zanies", source_url=CALENDAR)
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return ZaniesScraper(club)


@pytest.mark.asyncio
async def test_full_calendar_discovers_later_months_and_only_local_performances(scraper, monkeypatch):
    async def fetch(url):
        return WIDGET

    async def post(url, data):
        assert url == ROOT + "/wp-admin/admin-ajax.php"
        assert parse_qs(data) == {
            "action": ["loadEtixMonthViewEventPageFn"],
            "data[limit]": ["10000"],
            "data[venues]": ["8389"],
            "data[widget]": ["true"],
            "data[target]": ["calendar-1"],
        }
        return json.dumps(
            {
                "success": True,
                "data": {
                    "events": [
                        {"url": DETAIL, "start": "2026-10-08T19:00:00"},
                        {"url": LATER, "start": "2027-05-21T21:15:00"},
                        {"url": DETAIL},
                        {"url": "javascript:void(0)"},
                        {"url": DETAIL.replace("rosemont.zanies.com", "chicago.zanies.com")},
                    ]
                },
            }
        )

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    monkeypatch.setattr(scraper, "post_form", post)
    assert await scraper.collect_scraping_targets() == [DETAIL, LATER]


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [[], {"success": False}, {"success": True, "data": {"events": {}}}])
async def test_calendar_failure_does_not_silently_use_partial_homepage(scraper, monkeypatch, response):
    async def fetch(url):
        return WIDGET + f'<a href="{DETAIL}">Partial teaser</a>'

    async def post(url, data):
        return json.dumps(response)

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    monkeypatch.setattr(scraper, "post_form", post)
    with pytest.raises(ValueError, match="invalid event response"):
        await scraper.collect_scraping_targets()


@pytest.mark.asyncio
async def test_calendar_rejects_cross_host_endpoint(scraper, monkeypatch):
    async def fetch(url):
        return WIDGET.replace(ROOT + "/wp-admin", "https://other.example/wp-admin")

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    with pytest.raises(ValueError, match="invalid endpoint"):
        await scraper.collect_scraping_targets()


@pytest.mark.asyncio
async def test_calendar_limit_refuses_partial_coverage(scraper, monkeypatch):
    async def fetch(url):
        return WIDGET.replace('value="10000"', 'value="1"')

    async def post(url, data):
        return json.dumps({"success": True, "data": {"events": [{"url": DETAIL}]}})

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    monkeypatch.setattr(scraper, "post_form", post)
    with pytest.raises(ValueError, match="truncated"):
        await scraper.collect_scraping_targets()


@pytest.mark.asyncio
async def test_configured_month_calendar_requires_widget(scraper, monkeypatch):
    async def fetch(url):
        return f'<a href="{DETAIL}">Partial teaser</a>'

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    with pytest.raises(ValueError, match="widget is missing"):
        await scraper.collect_scraping_targets()


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows_with_local_time_and_repeat_identity(scraper, monkeypatch):
    early_url = LATER.replace("special-event-3/", "special-event-2/")

    async def fetch(url):
        early = url.rstrip("/") == early_url.rstrip("/")
        time = "Doors: 6 pm Show: 7 pm" if early else "Doors: 8:15 pm Show: 9:15 pm"
        ticket_id = "38309472" if early else "38309473"
        return f"""<h1>Josh Blue **Special Event**</h1>
        <span class="eventStDate">Friday, May 21</span>
        <span>{time}</span>
        <a href="https://www.etix.com/ticket/p/{ticket_id}/josh-blue">Buy Tickets</a>"""

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    pages = [await scraper.get_data(url) for url in (early_url, LATER)]
    shows = [show for page in pages for show in scraper.transformation_pipeline.transform(page)]
    assert len(shows) == 2
    assert all(show.club_id == 4648 for show in shows)
    assert [show.date.isoformat() for show in shows] == ["2027-05-21T19:00:00-05:00", "2027-05-21T21:15:00-05:00"]
    assert [show.show_page_url.rstrip("/") for show in shows] == [early_url.rstrip("/"), LATER.rstrip("/")]
    assert "38309472" in shows[0].tickets[0].purchase_url
    assert "38309473" in shows[1].tickets[0].purchase_url
    repeated = [show for page in pages for show in scraper.transformation_pipeline.transform(page)]
    assert len(ShowUtils.deduplicate_shows(shows + repeated)) == 2
