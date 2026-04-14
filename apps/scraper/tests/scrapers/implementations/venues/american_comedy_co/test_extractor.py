"""Unit tests for ShopifyExtractor.extract_events.

Covers Format A (variant-date) grouping, Format B (title-date) fallback,
multi-variant products, missing fields, and empty responses.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from laughtrack.scrapers.implementations.venues.american_comedy_co.extractor import (
    ShopifyExtractor,
)

TZ = "America/Los_Angeles"


def _product_format_a(
    product_id: int = 1,
    title: str = "Michael Rapaport LIVE! [THU]",
    handle: str = "michael-rapaport-live-thu",
    variants: list | None = None,
) -> dict:
    """Build a Format A product (date in variant title)."""
    if variants is None:
        variants = [
            {
                "title": "Thursday April 9 2026 / 8:00pm General Admission",
                "price": "25.00",
                "available": True,
            },
            {
                "title": "Thursday April 9 2026 / 8:00pm VIP",
                "price": "45.00",
                "available": True,
            },
        ]
    return {
        "id": product_id,
        "title": title,
        "handle": handle,
        "body_html": "<p>Show description</p>",
        "tags": ["comedy"],
        "images": [{"src": "https://cdn.shopify.com/img.jpg"}],
        "variants": variants,
    }


def _product_format_b(
    product_id: int = 2,
    title: str = "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry",
    handle: str = "des-mulrooney-sat-apr-11",
    variants: list | None = None,
) -> dict:
    """Build a Format B product (date in product title)."""
    if variants is None:
        variants = [
            {"title": "General Admission", "price": "20.00", "available": True},
            {"title": "VIP", "price": "35.00", "available": False},
        ]
    return {
        "id": product_id,
        "title": title,
        "handle": handle,
        "body_html": "",
        "tags": [],
        "images": [],
        "variants": variants,
    }


# ---------------------------------------------------------------------------
# Format A: variant-date products
# ---------------------------------------------------------------------------


class TestExtractEventsFormatA:
    def test_single_showtime_grouped_from_two_variants(self):
        """Two variants at the same date/time → one event with lowest price."""
        response = {"products": [_product_format_a()]}
        events = ShopifyExtractor.extract_events(response, TZ)

        assert len(events) == 1
        assert events[0].title == "Michael Rapaport LIVE! [THU]"
        assert events[0].price == "25.00"  # lowest of 25.00 and 45.00
        assert events[0].available is True

    def test_multiple_showtimes_produce_multiple_events(self):
        """Variants at different dates → multiple events."""
        product = _product_format_a(
            variants=[
                {
                    "title": "Thursday April 9 2026 / 8:00pm General Admission",
                    "price": "25.00",
                    "available": True,
                },
                {
                    "title": "Friday April 10 2026 / 9:00pm General Admission",
                    "price": "30.00",
                    "available": True,
                },
            ]
        )
        response = {"products": [product]}
        events = ShopifyExtractor.extract_events(response, TZ)

        assert len(events) == 2
        dates = sorted(e.show_date for e in events)
        assert dates[0].day == 9
        assert dates[1].day == 10

    def test_availability_is_ored_across_variants(self):
        """If any variant is available, the event is available."""
        product = _product_format_a(
            variants=[
                {
                    "title": "Thursday April 9 2026 / 8:00pm GA",
                    "price": "25.00",
                    "available": False,
                },
                {
                    "title": "Thursday April 9 2026 / 8:00pm VIP",
                    "price": "45.00",
                    "available": True,
                },
            ]
        )
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert len(events) == 1
        assert events[0].available is True

    def test_image_url_from_first_image(self):
        events = ShopifyExtractor.extract_events(
            {"products": [_product_format_a()]}, TZ
        )
        assert events[0].image_url == "https://cdn.shopify.com/img.jpg"


# ---------------------------------------------------------------------------
# Format B: title-date products
# ---------------------------------------------------------------------------


class TestExtractEventsFormatB:
    def test_single_product(self):
        response = {"products": [_product_format_b()]}
        events = ShopifyExtractor.extract_events(response, TZ)

        assert len(events) == 1
        e = events[0]
        assert e.title == "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"
        assert e.show_date.month == 4
        assert e.show_date.day == 11
        assert e.show_date.hour == 18
        assert e.show_date.minute == 30

    def test_lowest_price_selected(self):
        events = ShopifyExtractor.extract_events(
            {"products": [_product_format_b()]}, TZ
        )
        assert events[0].price == "20.00"  # lowest of 20.00 and 35.00

    def test_availability_any_true(self):
        events = ShopifyExtractor.extract_events(
            {"products": [_product_format_b()]}, TZ
        )
        assert events[0].available is True  # GA is available, VIP is not


# ---------------------------------------------------------------------------
# Mixed / edge cases
# ---------------------------------------------------------------------------


class TestExtractEventsEdgeCases:
    def test_empty_products_list(self):
        assert ShopifyExtractor.extract_events({"products": []}, TZ) == []

    def test_missing_products_key(self):
        assert ShopifyExtractor.extract_events({}, TZ) == []

    def test_products_not_a_list(self):
        assert ShopifyExtractor.extract_events({"products": "bad"}, TZ) == []

    def test_product_missing_title_skipped(self):
        product = _product_format_a(title="")
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert events == []

    def test_product_missing_handle_skipped(self):
        product = _product_format_a()
        product["handle"] = ""
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert events == []

    def test_product_no_variants_skipped(self):
        product = _product_format_a(variants=[])
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert events == []

    def test_product_no_images_yields_empty_image_url(self):
        product = _product_format_b()
        product["images"] = []
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert len(events) == 1
        assert events[0].image_url == ""

    def test_multiple_products_mixed_formats(self):
        """One Format A + one Format B product yields events from both."""
        response = {"products": [_product_format_a(), _product_format_b()]}
        events = ShopifyExtractor.extract_events(response, TZ)
        assert len(events) == 2

    def test_unparseable_variant_and_title_skipped(self):
        """Product where neither variant nor title yields a date → no events."""
        product = {
            "id": 99,
            "title": "Gift Card",
            "handle": "gift-card",
            "body_html": "",
            "tags": [],
            "images": [],
            "variants": [
                {"title": "Default", "price": "50.00", "available": True}
            ],
        }
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert events == []

    def test_tags_preserved(self):
        product = _product_format_a()
        product["tags"] = ["comedy", "headliner"]
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert events[0].tags == ["comedy", "headliner"]

    def test_non_list_tags_default_to_empty(self):
        product = _product_format_a()
        product["tags"] = "comedy"
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert events[0].tags == []
