"""Unit tests for the TicketSpice (Webconnex) ticketing-form scraper (TASK-3207).

The fixture is a recorded thestage.ticketspice.com/barley-me-comedy form page
(The Stage at Burke Junction's "Barley & Me Pod-uctions Comedy Show"). The form
embeds its config in a ``window.__BOOTSTRAP__`` JS object: ``appSettings``
(formName, eventStart 2026-06-07, timeZone America/Los_Angeles, status 1) and
``formData`` (one GA ticket level, price $9).
"""

import os

import pytz

from datetime import date

from laughtrack.core.entities.event.ticketspice import TicketSpiceEvent
from laughtrack.scrapers.implementations.api.ticketspice.extractor import (
    extract_event,
)

_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "barley_me_comedy_form.html"
)
_FORM_URL = "https://thestage.ticketspice.com/barley-me-comedy"


def _load_fixture() -> str:
    with open(_FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "The Stage at Burke Junction"
    timezone = "America/Los_Angeles"

    def metadata_value(self, key):
        return None


class TestExtractEventFromFixture:
    def test_parses_event(self):
        ev = extract_event(_load_fixture(), _FORM_URL)
        assert ev is not None
        assert ev.title == "Barley & Me Pod-uctions Comedy Show"
        assert ev.event_date == date(2026, 6, 7)
        assert ev.form_url == _FORM_URL
        assert ev.price == 9.0

    def test_empty_html_returns_none(self):
        assert extract_event("", _FORM_URL) is None

    def test_no_bootstrap_returns_none(self):
        assert extract_event("<html><body>nothing here</body></html>", _FORM_URL) is None

    def test_unpublished_form_returns_none(self):
        # status != 1 (draft/disabled) must not yield a live show.
        html = (
            'window.__BOOTSTRAP__ = {\n'
            '\tappSettings: "{\\"status\\":0,\\"formName\\":\\"Draft Show\\",'
            '\\"eventStart\\":\\"2099-01-01T00:00:00Z\\"}",\n'
            '}'
        )
        assert extract_event(html, _FORM_URL) is None

    def test_missing_date_returns_none(self):
        html = (
            'window.__BOOTSTRAP__ = {\n'
            '\tappSettings: "{\\"status\\":1,\\"formName\\":\\"No Date Show\\"}",\n'
            '}'
        )
        assert extract_event(html, _FORM_URL) is None

    def test_non_ascii_form_name_is_not_mojibake(self):
        # A formName with literal (non-\u-escaped) UTF-8 must survive intact.
        # The earlier decode("unicode_escape") path corrupted such titles into
        # mojibake; the json.loads re-quote path preserves them.
        html = (
            'window.__BOOTSTRAP__ = {\n'
            '\tappSettings: "{\\"status\\":1,\\"formName\\":\\"略谷 Comedy\\",'
            '\\"eventStart\\":\\"2099-01-01T00:00:00Z\\"}",\n'
            '}'
        )
        ev = extract_event(html, _FORM_URL)
        assert ev is not None
        assert ev.title == "略谷 Comedy"


class TestToShow:
    def test_builds_future_show_with_default_time(self):
        ev = TicketSpiceEvent(
            title="Barley & Me Comedy",
            event_date=date(2099, 6, 7),
            form_url=_FORM_URL,
            price=9.0,
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == "Barley & Me Comedy"
        local = show.date.astimezone(pytz.timezone("America/Los_Angeles"))
        assert (local.year, local.hour, local.minute) == (2099, 19, 0)  # default 19:00
        assert show.tickets[0].purchase_url == _FORM_URL
        assert show.tickets[0].price == 9.0

    def test_default_show_time_override(self):
        class _ClubAt8(_Club):
            def metadata_value(self, key):
                return "20:30" if key == "default_show_time" else None

        ev = TicketSpiceEvent(
            title="Late Comedy",
            event_date=date(2099, 6, 7),
            form_url=_FORM_URL,
        )
        show = ev.to_show(_ClubAt8())
        local = show.date.astimezone(pytz.timezone("America/Los_Angeles"))
        assert (local.hour, local.minute) == (20, 30)

    def test_past_show_returns_none(self):
        ev = TicketSpiceEvent(
            title="Old Comedy",
            event_date=date(2020, 1, 6),
            form_url=_FORM_URL,
        )
        assert ev.to_show(_Club()) is None

    def test_missing_title_returns_none(self):
        ev = TicketSpiceEvent(title="", event_date=date(2099, 6, 7), form_url=_FORM_URL)
        assert ev.to_show(_Club()) is None


from unittest.mock import AsyncMock

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticketspice.scraper import (
    TicketSpiceScraper,
)


def _make_scraper(source_url=_FORM_URL):
    src = ScrapingSource(
        platform="custom", scraper_key="ticketspice", source_url=source_url,
        priority=0, enabled=True, id=1, club_id=999, metadata={},
    )
    club = Club(
        id=999, name="The Stage at Burke Junction", address="",
        website="https://www.stageatburke.com/", popularity=0, zip_code="95682",
        phone_number="", visible=True, timezone="America/Los_Angeles",
        city="Cameron Park", state="CA",
        scraping_sources=[src], active_scraping_source=src,
    )
    return TicketSpiceScraper(club)


class TestScraperGlue:
    async def test_no_form_url_returns_empty_targets(self):
        scraper = _make_scraper(source_url="")
        assert await scraper.collect_scraping_targets() == []

    async def test_collect_targets_returns_form_url(self):
        scraper = _make_scraper()
        targets = await scraper.collect_scraping_targets()
        assert targets == [_FORM_URL]

    async def test_get_data_parses_fixture(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value=_load_fixture())
        page = await scraper.get_data(_FORM_URL)
        assert page is not None
        assert len(page.event_list) == 1
        assert page.event_list[0].title == "Barley & Me Pod-uctions Comedy Show"

    async def test_get_data_empty_html_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value="")
        assert await scraper.get_data(_FORM_URL) is None

    async def test_get_data_no_event_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(return_value="<html><body>no form</body></html>")
        assert await scraper.get_data(_FORM_URL) is None

    async def test_get_data_fetch_exception_returns_none(self):
        scraper = _make_scraper()
        scraper.fetch_html = AsyncMock(side_effect=RuntimeError("boom"))
        assert await scraper.get_data(_FORM_URL) is None
