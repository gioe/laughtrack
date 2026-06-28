"""Unit tests for ShopifyExtractor.extract_events.

Covers Format A (variant-date) grouping, Format B (title-date) fallback,
Format C (handle/numeric-title date), non-show filtering, multi-variant
products, missing fields, and empty responses.
"""

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


# ---------------------------------------------------------------------------
# Format C: date in handle / numeric title, time in title or variants;
# non-show (class/merch/membership) filtering (TASK-2949)
# ---------------------------------------------------------------------------


class TestFormatC:
    """Improv School Redlands shape: numeric handles/titles, no weekday/month-name."""

    def test_variant_times_expand_to_one_event_each(self):
        """A YYYYMMDD handle + per-showtime variants → one event per variant time."""
        product = {
            "id": 10,
            "title": "Saturday Night Improv Shows",
            "handle": "20260620-saturday-night-improv-showcase",
            "tags": [],
            "images": [],
            "variants": [
                {"title": "6pm - Secret Time / Lethargic Salmon", "price": "15.00", "available": True},
                {"title": "7pm - The Audacity / Anecdotal Harmony", "price": "15.00", "available": True},
                {"title": "8pm - Off-Script / The Resistance", "price": "15.00", "available": False},
                {"title": "Any two shows", "price": "25.00", "available": True},
            ],
        }
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        hours = sorted(e.show_date.hour for e in events)
        assert hours == [18, 19, 20]  # "Any two shows" carries no clock time → skipped
        assert all((e.show_date.year, e.show_date.month, e.show_date.day) == (2026, 6, 20) for e in events)

    def test_title_time_fallback_when_no_variant_time(self):
        """Default-Title variant → single event using the time in the product title."""
        product = {
            "id": 11,
            "title": "6/26 7pm - Capybara Comedy Hour Featuring Jon Flanagan",
            "handle": "20260625-capybara-comedy-hour",
            "tags": ["stand up show"],
            "images": [],
            "variants": [{"title": "Default Title", "price": "20.00", "available": True}],
        }
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert len(events) == 1
        ev = events[0]
        # title day (26) + handle year (2026); time 7pm from title
        assert (ev.show_date.year, ev.show_date.month, ev.show_date.day, ev.show_date.hour) == (2026, 6, 26, 19)
        assert ev.price == "20.00"

    def test_class_and_merch_and_membership_products_dropped(self):
        products = [
            {"id": 20, "title": "Beginner Improv", "handle": "beginner-improv",
             "tags": ["class", "improv class"], "images": [],
             "variants": [{"title": "20260701 @ 6pm", "price": "100.00", "available": True}]},
            {"id": 21, "title": "Improv School Redlands Unisex Hoodie", "handle": "20260701-hoodie",
             "tags": ["merch"], "images": [],
             "variants": [{"title": "6pm - Black / S", "price": "40.00", "available": True}]},
            {"id": 22, "title": "Improv Membership", "handle": "membership",
             "tags": ["class"], "images": [],
             "variants": [{"title": "Monthly Membership", "price": "50.00", "available": True}]},
        ]
        assert ShopifyExtractor.extract_events({"products": products}, TZ) == []

    def test_undated_special_event_dropped(self):
        product = {
            "id": 30, "title": "Makers Market", "handle": "makers-market",
            "tags": ["event", "Special Event"], "images": [],
            "variants": [{"title": "Default Title", "price": "0.00", "available": True}],
        }
        assert ShopifyExtractor.extract_events({"products": [product]}, TZ) == []

    def test_substring_class_tags_are_not_treated_as_non_show(self):
        """'classic'/'masterclass' contain 'class' but are real shows (word-boundary guard)."""
        product = {
            "id": 40,
            "title": "Capybara Comedy Hour",
            "handle": "20260626-capybara-classic",
            "tags": ["classic comedy", "masterclass showcase"],
            "images": [],
            "variants": [{"title": "7pm - Headliner", "price": "20.00", "available": True}],
        }
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ)
        assert len(events) == 1
        assert events[0].show_date.hour == 19


# ---------------------------------------------------------------------------
# default_time fallback: dated products with no clock time anywhere (TASK-3378)
# ---------------------------------------------------------------------------


class TestDefaultTimeFallback:
    """Kesha's Comedy House shape: M/D title, Default-Title variant, no time.

    These ad-hoc Shopify venues advertise the showtime only on a flyer image, so
    no clock time is parseable. The opt-in default_time keeps the dated show.
    """

    def _dated_no_time_product(self) -> dict:
        # YYYYMMDD handle pins a far-future year so the inferred-past drop never
        # fires (convention #11: no test time-bombs); Default-Title variant and a
        # title with no clock leave the time unresolvable.
        return {
            "id": 50,
            "title": "6/28 Spoken Laugh Lounge",
            "handle": "20990628-spoken-laugh-lounge",
            "tags": [],
            "images": [],
            "variants": [{"title": "Default Title", "price": "15.00", "available": True}],
        }

    def test_dropped_without_default_time(self):
        """Default behavior unchanged: no time anywhere → product dropped."""
        events = ShopifyExtractor.extract_events({"products": [self._dated_no_time_product()]}, TZ)
        assert events == []

    def test_kept_with_default_time(self):
        """default_time supplies the missing clock → one event at that time."""
        events = ShopifyExtractor.extract_events(
            {"products": [self._dated_no_time_product()]}, TZ, default_time=(20, 0)
        )
        assert len(events) == 1
        ev = events[0]
        assert (ev.show_date.year, ev.show_date.month, ev.show_date.day) == (2099, 6, 28)
        assert (ev.show_date.hour, ev.show_date.minute) == (20, 0)
        assert ev.price == "15.00"

    def test_default_time_does_not_override_format_c_title_time(self):
        """Format C path: date in handle, time in title → title time wins over default_time.

        The title carries a clock but no M/D date, so Format B's date+time parse
        fails and it falls to Format C; Format C's title-clock fallback must use
        7pm, not the 20:00 default.
        """
        product = {
            "id": 51,
            "title": "7pm Capybara Comedy Hour",
            "handle": "20990628-capybara",
            "tags": [],
            "images": [],
            "variants": [{"title": "Default Title", "price": "20.00", "available": True}],
        }
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ, default_time=(20, 0))
        assert len(events) == 1
        ev = events[0]
        assert (ev.show_date.year, ev.show_date.month, ev.show_date.day) == (2099, 6, 28)
        assert ev.show_date.hour == 19  # 7pm from title, not the 20:00 default

    def test_default_time_does_not_resurrect_undated_products(self):
        """No date anywhere → still dropped even with default_time set."""
        product = {
            "id": 52, "title": "Mike Chase Comedy Showcase", "handle": "mike-chase-comedy-showcase",
            "tags": [], "images": [],
            "variants": [{"title": "Default Title", "price": "10.00", "available": True}],
        }
        events = ShopifyExtractor.extract_events({"products": [product]}, TZ, default_time=(20, 0))
        assert events == []
