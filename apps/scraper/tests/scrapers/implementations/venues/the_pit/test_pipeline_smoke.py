"""Focused tests for The PIT's PatronTicket and WordPress composite scraper."""

from datetime import datetime, timezone

import pytest

from laughtrack.app.registry import discover_scrapers
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.scrapers.implementations.venues.patron_ticket.scraper import (
    PatronTicketScraper,
)
from laughtrack.scrapers.implementations.venues.the_pit.scraper import ThePitScraper


_WORDPRESS_URL = "https://thepit-nyc.com/events/feed/"
_PATRONTICKET_URL = "https://thepit.my.salesforce-sites.com/ticket"
_VENUE_ID = "a0T1I000009YHXGUA4"


def _club() -> Club:
    club = Club(
        id=16062,
        name="The PIT",
        address="154 W 29th St",
        website="https://thepit-nyc.com/",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    source = ScrapingSource(
        id=7658,
        club_id=club.id,
        platform="custom",
        scraper_key="the_pit",
        source_url=_WORDPRESS_URL,
        metadata={
            "patronticket_source_url": _PATRONTICKET_URL,
            "patronticket_venue_id": _VENUE_ID,
            "detail_fetch": {
                "feed_item_links": True,
                "set_same_as_to_detail_url": True,
                "skip_parent_events_with_subevents": True,
            },
        },
    )
    club.scraping_sources = [source]
    club.active_scraping_source = source
    return club


def _show(
    name: str,
    hour: int,
    *,
    url: str,
    tickets: list[Ticket],
    description: str = "",
) -> Show:
    return Show(
        name=name,
        club_id=16062,
        date=datetime(2099, 1, 1, hour, tzinfo=timezone.utc),
        show_page_url=url,
        tickets=tickets,
        description=description,
        room="",
    )


@pytest.mark.asyncio
async def test_combines_sources_and_deduplicates_overlaps(monkeypatch):
    online = _show(
        "Authoritative Online Title",
        20,
        url=f"{_PATRONTICKET_URL}/#/instances/online-one",
        tickets=[
            Ticket(
                price=12.0,
                purchase_url=f"{_PATRONTICKET_URL}/#/instances/online-one",
                type="General Admission",
            )
        ],
    )
    wordpress_overlap = _show(
        "Slightly Different WordPress Title",
        16,
        url="https://thepit-nyc.com/events/online-one",
        tickets=[
            Ticket(
                price=None,
                purchase_url=f"{_PATRONTICKET_URL}/#/instances/online-one",
            )
        ],
    )
    cash_only = _show(
        "Saturday Open Mic",
        21,
        url="https://thepit-nyc.com/events/saturday-open-mic",
        tickets=[
            Ticket(
                price=None,
                purchase_url="https://thepit-nyc.com/events/saturday-open-mic/",
            )
        ],
        description="Tickets $5 CASH at the door.",
    )

    async def fake_patron_ticket(self):
        return [online]

    async def fake_wordpress(self):
        return [wordpress_overlap, cash_only]

    monkeypatch.setattr(PatronTicketScraper, "scrape_async", fake_patron_ticket)
    monkeypatch.setattr(JsonLdScraper, "scrape_async", fake_wordpress)

    shows = await ThePitScraper(_club()).scrape_async()

    assert shows == [online, cash_only]
    assert cash_only.tickets[0].price == 5.0


@pytest.mark.asyncio
async def test_online_events_preserve_ticket_fields(monkeypatch):
    purchase_url = f"{_PATRONTICKET_URL}/#/instances/online-two"
    online = _show(
        "Paid PIT Show",
        20,
        url=purchase_url,
        tickets=[
            Ticket(
                price=12.0,
                purchase_url=purchase_url,
                type="General Admission",
                sold_out=False,
            ),
            Ticket(
                price=27.5,
                purchase_url=purchase_url,
                type="VIP",
                sold_out=True,
            ),
        ],
    )

    async def fake_patron_ticket(self):
        return [online]

    async def fake_wordpress(self):
        return []

    monkeypatch.setattr(PatronTicketScraper, "scrape_async", fake_patron_ticket)
    monkeypatch.setattr(JsonLdScraper, "scrape_async", fake_wordpress)

    shows = await ThePitScraper(_club()).scrape_async()

    assert shows[0].show_page_url == purchase_url
    assert [
        (ticket.price, ticket.type, ticket.purchase_url, ticket.sold_out)
        for ticket in shows[0].tickets
    ] == [
        (12.0, "General Admission", purchase_url, False),
        (27.5, "VIP", purchase_url, True),
    ]


def test_cash_price_phrases_are_parsed_without_false_matches():
    assert ThePitScraper.extract_cash_price("Tickets $5 CASH at the door") == 5.0
    assert ThePitScraper.extract_cash_price("$10 for the evening (both shows)") == 10.0
    assert ThePitScraper.extract_cash_price("Tickets $7.50 cash only") == 7.5
    assert ThePitScraper.extract_cash_price("$20 food/beverage minimum") is None
    assert ThePitScraper.extract_cash_price("Win a $100 cash prize") is None
    assert ThePitScraper.extract_cash_price("Doors at 6:15 PM; bring $5") is None
    assert ThePitScraper.extract_cash_price("") is None
    assert ThePitScraper.extract_cash_price(None) is None


@pytest.mark.asyncio
async def test_one_source_failure_does_not_drop_the_other(monkeypatch):
    wordpress = _show(
        "WordPress Survives",
        19,
        url="https://thepit-nyc.com/events/survives",
        tickets=[Ticket(price=None, purchase_url="https://thepit-nyc.com/events/survives/")],
    )

    async def failed_patron_ticket(self):
        raise RuntimeError("Salesforce unavailable")

    async def fake_wordpress(self):
        return [wordpress]

    monkeypatch.setattr(PatronTicketScraper, "scrape_async", failed_patron_ticket)
    monkeypatch.setattr(JsonLdScraper, "scrape_async", fake_wordpress)

    assert await ThePitScraper(_club()).scrape_async() == [wordpress]


def test_builds_unfiltered_patron_ticket_child_and_registers_key():
    scraper = ThePitScraper(_club())
    child = scraper._patron_ticket_scraper

    assert child.club.scraping_url == _PATRONTICKET_URL
    assert child.club.source_metadata == {
        "patronticket_venue_id": _VENUE_ID,
        "patronticket_categories": "*",
    }
    assert discover_scrapers().get("the_pit") is ThePitScraper
