"""
Unit tests for StandupNY ticket extraction — the empty/None price coercion fix
and the Square checkout price enhancement (TASK-2836).
"""

import os
from unittest.mock import AsyncMock, patch

from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.standup_ny.data import StandupNYPageData
from laughtrack.scrapers.implementations.venues.standup_ny.extractor import StandupNYEventExtractor
from laughtrack.scrapers.implementations.venues.standup_ny.transformer import StandupNYEventTransformer

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _square_fixture() -> str:
    with open(os.path.join(FIXTURES_DIR, "square_checkout_snippet.html")) as f:
        return f.read()


def _make_club() -> Club:
    _c = Club(id=1, name='StandUp NY', address='', zip_code='10023', website='https://standupny.com', timezone='America/New_York', popularity=0, phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://standupny.com/events', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_event(**kwargs) -> StandupNYEvent:
    defaults = dict(id="1", name="Test Show", date="2026-03-10", start_time="20:00:00", ticket_url="https://standupny.com/tickets/1")
    defaults.update(kwargs)
    return StandupNYEvent(**defaults)


def _transformer() -> StandupNYEventTransformer:
    return StandupNYEventTransformer(club=_make_club())


class TestVenuePilotTicketPriceCoercion:
    def test_empty_string_price_coerces_to_zero(self):
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": ""}, "soldOut": False, "type": "General Admission"},
        ])
        show = _transformer().transform_to_show(event)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 0.0

    def test_none_price_coerces_to_zero(self):
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": None}, "soldOut": False, "type": "General Admission"},
        ])
        show = _transformer().transform_to_show(event)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 0.0

    def test_valid_price_preserved(self):
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": "25.00"}, "soldOut": False, "type": "General Admission"},
        ])
        show = _transformer().transform_to_show(event)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 25.0


class TestSquareEnhancement:
    """Square checkout price path (TASK-2836): the venue moved paid tickets to
    square.link, whose checkout.square.site page embeds price_money cents."""

    SQUARE_URL = "https://square.link/u/WMMoWFLn"

    async def test_enhance_event_parses_captured_fixture(self):
        extractor = StandupNYEventExtractor(logger_context={})
        event = _make_event(ticket_url=self.SQUARE_URL)

        with patch(
            "laughtrack.scrapers.implementations.venues.standup_ny.extractor.HttpClient.fetch_html",
            new=AsyncMock(return_value=_square_fixture()),
        ):
            ok = await extractor.enhance_event_with_square(None, event)

        assert ok is True
        assert event.has_square_data is True
        # Captured live tiers: 2500 and 2900 cents
        assert event.square_prices == [25.0, 29.0]

    async def test_enhance_event_skips_non_square_url(self):
        extractor = StandupNYEventExtractor(logger_context={})
        event = _make_event(ticket_url="https://tickets.venuepilot.com/e/some-show")

        ok = await extractor.enhance_event_with_square(None, event)

        assert ok is False
        assert event.has_square_data is False

    async def test_enhance_event_no_prices_returns_false(self):
        extractor = StandupNYEventExtractor(logger_context={})
        event = _make_event(ticket_url=self.SQUARE_URL)

        with patch(
            "laughtrack.scrapers.implementations.venues.standup_ny.extractor.HttpClient.fetch_html",
            new=AsyncMock(return_value="<html><body>no embedded json</body></html>"),
        ):
            ok = await extractor.enhance_event_with_square(None, event)

        assert ok is False
        assert event.square_prices is None

    def test_transformer_uses_lowest_square_tier(self):
        event = _make_event(ticket_url=self.SQUARE_URL)
        event.add_square_data([25.0, 29.0])

        show = _transformer().transform_to_show(event)

        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 25.0
        assert show.tickets[0].purchase_url == self.SQUARE_URL

    def test_venue_pilot_tickets_win_over_square(self):
        """VenuePilot path is unchanged and takes precedence when present."""
        event = _make_event(venue_pilot_tickets=[
            {"breakdown": {"price": "15.00"}, "soldOut": False, "type": "General Admission"},
        ])
        event.add_square_data([25.0])

        show = _transformer().transform_to_show(event)

        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == 15.0

    def test_enhancement_urls_include_square_and_venuepilot(self):
        events = [
            _make_event(id="1", ticket_url=self.SQUARE_URL),
            _make_event(id="2", ticket_url="https://tickets.venuepilot.com/e/open-mic"),
            _make_event(id="3", ticket_url="https://www.eventbrite.com/e/123"),
        ]
        page = StandupNYPageData(event_list=events)

        urls = page.get_enhancement_urls()

        assert self.SQUARE_URL in urls
        assert "https://tickets.venuepilot.com/e/open-mic" in urls
        assert "https://www.eventbrite.com/e/123" not in urls
