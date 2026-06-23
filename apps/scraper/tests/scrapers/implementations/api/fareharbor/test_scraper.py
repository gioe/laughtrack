"""Smoke tests for the generic FareHarbor scraper."""

import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.fareharbor.data import (
    FareHarborPageData,
    parse_fareharbor_datetime,
)
from laughtrack.scrapers.implementations.api.fareharbor.extractor import (
    extract_events_from_calendar,
    extract_items,
    item_is_operational,
)
from laughtrack.scrapers.implementations.api.fareharbor.scraper import (
    FareHarborScraper,
)

FIXTURES = Path(__file__).parent / "fixtures"
ITEMS_PAYLOAD = json.loads((FIXTURES / "firehouse_items.json").read_text())
CALENDAR_PAYLOAD = json.loads((FIXTURES / "firehouse_calendar.json").read_text())


def _club(metadata=None, source_url="https://fareharbor.com/embeds/book/firehousetheater/"):
    if metadata is None:
        metadata = {
            "shortname": "firehousetheater",
            "exclude_item_pks": [187485, 232371, 695268],
            "months_ahead": 1,
        }
    source = ScrapingSource(
        id=1,
        club_id=11074,
        platform="custom",
        scraper_key="fareharbor",
        source_url=source_url,
        metadata=metadata,
    )
    club = Club(
        id=11074,
        name="Firehouse Theater",
        address="4 Equality Park Pl",
        website="https://firehousetheater.org/",
        popularity=0,
        zip_code="02840",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        scraping_sources=[source],
        active_scraping_source=source,
    )
    return club


def test_extract_items_and_filter_operational_products():
    items = extract_items(ITEMS_PAYLOAD)

    kept = [
        item["name"]
        for item in items
        if not item_is_operational(
            item, excluded_item_pks=[187485, 232371, 695268]
        )
    ]

    assert kept == ["The Bit Players"]


def test_default_operational_filter_does_not_match_class_substring():
    assert not item_is_operational(
        {"pk": 1, "name": "World Class Comedy", "headline": "Stand-up"}
    )


def test_allow_item_pks_override_operational_keywords():
    assert not item_is_operational(
        {"pk": 695268, "name": "Improv Practice", "headline": "Free"},
        allowed_item_pks=[695268],
    )


def test_calendar_events_include_price_and_absolute_booking_url():
    event = extract_events_from_calendar(
        CALENDAR_PAYLOAD,
        item=ITEMS_PAYLOAD["items"][0],
        base_url="https://fareharbor.com",
    )[0]

    assert event.title == "The Bit Players"
    assert event.price == 18.0
    assert event.show_page_url == (
        "https://fareharbor.com/firehousetheater/items/187495/"
        "availability/1864951701/book/"
    )


def test_event_to_show_localizes_start_time_and_builds_ticket():
    event = extract_events_from_calendar(
        CALENDAR_PAYLOAD,
        item=ITEMS_PAYLOAD["items"][0],
        base_url="https://fareharbor.com",
    )[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "The Bit Players"
    assert show.date.isoformat() == "2026-10-02T20:00:00-04:00"
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 18.0


def test_datetime_parser_falls_back_to_utc_timestamp():
    parsed = parse_fareharbor_datetime("", "2026-10-03T00:00:00+0000", "America/New_York")
    assert parsed is not None
    assert parsed.isoformat() == "2026-10-03T00:00:00+00:00"


@pytest.mark.asyncio
async def test_scraper_fetches_items_and_monthly_calendar(monkeypatch):
    scraper = FareHarborScraper(_club(metadata={"shortname": "firehousetheater", "months_ahead": 2}))
    calls = []

    async def fake_fetch_json(url, *, allow_404=False):
        calls.append((url, allow_404))
        if url.endswith("/items/"):
            return ITEMS_PAYLOAD
        return CALENDAR_PAYLOAD if "/items/187495/calendar/" in url else None

    monkeypatch.setattr(scraper, "_fetch_json_or_none", fake_fetch_json)

    result = await scraper.get_data(
        "https://fareharbor.com/api/v1/companies/firehousetheater/items/"
    )

    assert isinstance(result, FareHarborPageData)
    assert len(result.event_list) == 1
    assert calls[0] == (
        "https://fareharbor.com/api/v1/companies/firehousetheater/items/",
        False,
    )
    assert any("/calendar/" in url and allow_404 for url, allow_404 in calls)


def test_shortname_can_be_derived_from_embed_url():
    scraper = FareHarborScraper(
        _club(metadata={}, source_url="https://fareharbor.com/embeds/book/firehousetheater/items/")
    )
    assert scraper._config() is not None
    assert scraper._config().shortname == "firehousetheater"
