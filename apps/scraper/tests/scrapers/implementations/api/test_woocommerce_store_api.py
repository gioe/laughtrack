"""Smoke tests for the generic woocommerce_store_api scraper (TASK-2947).

Fixtures mirror the verified live shape of grandcomedyclub.com (WordPress +
WooCommerce 10.8.1): GET /wp-json/wc/store/v1/products returns a top-level JSON
array of products. Comedy products sit in the "Comedy Events" category and carry
"Show Dates" (MM/DD/YYYY) + "Show Times" attribute terms plus a permalink; a
product fans out into one show per (date, time) showtime.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.woocommerce import WoocommerceEvent
from laughtrack.scrapers.implementations.api.woocommerce_store_api.extractor import (
    WoocommerceStoreApiExtractor,
)
from laughtrack.scrapers.implementations.api.woocommerce_store_api.scraper import (
    WoocommerceStoreApiScraper,
)


def _club() -> Club:
    return Club(
        id=8897,
        name="Grand Comedy Club & Pizzeria",
        address="123 Main St",
        website="https://www.grandcomedyclub.com/",
        popularity=0,
        zip_code="90012",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _products() -> list:
    return [
        {
            "id": 39813,
            "name": "Jeremiah Watkins &#8211;  $20 (First time at our club!)",
            "permalink": "https://www.grandcomedyclub.com/product/j-watkins/",
            "type": "variable",
            "prices": {"price": "2000", "currency_minor_unit": 2},
            "categories": [{"id": 35, "name": "Comedy Events", "slug": "comedyevents"}],
            "attributes": [
                {"name": "Show Dates", "terms": [{"name": "09/18/2026"}, {"name": "09/19/2026"}]},
                {"name": "Show Times", "terms": [{"name": "6:30pm"}, {"name": "8:45pm"}]},
            ],
        },
        {
            "id": 39804,
            "name": "PMAN Productions Presents- Raw Comedy Night",
            "permalink": "https://www.grandcomedyclub.com/product/pman/",
            "type": "variable",
            "prices": {"price": "1500", "currency_minor_unit": 2},
            "categories": [{"id": 35, "name": "Comedy Events", "slug": "comedyevents"}],
            "attributes": [
                {"name": "Show Dates", "terms": [{"name": "07/23/2026"}]},
                {"name": "Show Times", "terms": [{"name": "7:30pm"}]},
            ],
        },
        {
            "id": 100,
            "name": "Margherita Pizza",
            "permalink": "https://www.grandcomedyclub.com/product/pizza/",
            "type": "simple",
            "prices": {"price": "1200", "currency_minor_unit": 2},
            "categories": [{"id": 9, "name": "Food", "slug": "food"}],
            "attributes": [],
        },
    ]


def test_extractor_expands_dates_times_and_filters_category():
    events = WoocommerceStoreApiExtractor.extract_events(_products())

    # 2 dates x 2 times (Watkins) + 1 (PMAN) = 5; the Food product is filtered out.
    assert len(events) == 5

    watkins = [e for e in events if e.permalink.endswith("/j-watkins/")]
    assert len(watkins) == 4
    assert {(e.date_str, e.time_str) for e in watkins} == {
        ("09/18/2026", "6:30pm"),
        ("09/18/2026", "8:45pm"),
        ("09/19/2026", "6:30pm"),
        ("09/19/2026", "8:45pm"),
    }
    # HTML entities are unescaped and price is parsed from minor units.
    assert "&#8211;" not in watkins[0].name
    assert watkins[0].price == 20.0


def test_event_to_show_parses_datetime_and_ticket():
    events = WoocommerceStoreApiExtractor.extract_events(_products())
    event = next(e for e in events if e.date_str == "09/18/2026" and e.time_str == "6:30pm")

    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 9
    assert show.date.day == 18
    assert show.date.hour == 18
    assert show.date.minute == 30
    # The show factory normalizes the URL (trailing slash dropped).
    assert show.show_page_url.rstrip("/") == "https://www.grandcomedyclub.com/product/j-watkins"
    assert show.tickets and show.tickets[0].price == 20.0


@pytest.mark.parametrize(
    "time_str, expected_hour, expected_minute",
    [
        ("6:30pm", 18, 30),
        ("6:30 pm", 18, 30),  # space-separated meridiem must not fall back to midnight
        ("7pm", 19, 0),
        ("7 pm", 19, 0),
    ],
)
def test_to_show_handles_time_formats(time_str, expected_hour, expected_minute):
    event = WoocommerceEvent(
        name="Show",
        date_str="07/23/2026",
        time_str=time_str,
        permalink="https://www.grandcomedyclub.com/product/x/",
    )
    show = event.to_show(_club())
    assert show is not None
    assert (show.date.hour, show.date.minute) == (expected_hour, expected_minute)


@pytest.mark.asyncio
async def test_get_data_parses_mocked_feed(monkeypatch):
    scraper = WoocommerceStoreApiScraper(_club())

    async def fake_fetch_json(url, **kwargs):
        # Return the feed only on page 1; empty after so pagination terminates.
        return _products() if "page=1" in url else []

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    page_data = await scraper.get_data(
        "https://www.grandcomedyclub.com/wp-json/wc/store/v1/products?per_page=100"
    )

    assert page_data is not None
    assert len(page_data.event_list) == 5


@pytest.mark.asyncio
async def test_collect_scraping_targets_builds_products_url():
    club = _club()
    club.scraping_url = "https://www.grandcomedyclub.com"
    scraper = WoocommerceStoreApiScraper(club)

    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 1
    assert "/wp-json/wc/store/v1/products" in targets[0]
    assert "per_page=100" in targets[0]
