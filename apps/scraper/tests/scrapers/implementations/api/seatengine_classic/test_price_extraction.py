"""Unit tests for classic SeatEngine price extraction.

Covers the pure HTML/JSON parser (``price_extractor``) plus the transformer's
NULL-fallback behavior so the silent default-to-zero regression cannot return.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine_classic.price_extractor import (
    cheapest_price,
    extract_inventories,
)
from laughtrack.scrapers.implementations.api.seatengine_classic.scraper import (
    SeatEngineClassicScraper,
)
from laughtrack.scrapers.implementations.api.seatengine_classic.transformer import (
    SeatEngineClassicTransformer,
)


def _make_show_html(config: dict) -> str:
    return (
        "<html><head><script>\n"
        "//<![CDATA[\n"
        f"window.seat_engine_app_config = {json.dumps(config)};\n"
        "//]]>\n"
        "</script></head><body></body></html>"
    )


class TestExtractInventories:

    def test_extracts_active_inventories(self):
        cfg = {
            "showtime": {
                "inventories": [
                    {"id": 1, "name": "Single Ticket", "price": 3500},
                    {"id": 2, "name": "VIP Table of 2", "price": 9000},
                ]
            }
        }
        invs = extract_inventories(_make_show_html(cfg))
        assert [inv["price"] for inv in invs] == [3500, 9000]

    def test_returns_empty_when_config_missing(self):
        assert extract_inventories("<html><body>nothing here</body></html>") == []

    def test_returns_empty_when_inventories_key_missing(self):
        assert extract_inventories(_make_show_html({"showtime": {}})) == []

    def test_returns_empty_when_inventories_is_not_a_list(self):
        assert extract_inventories(_make_show_html({"showtime": {"inventories": {}}})) == []

    def test_returns_empty_on_truncated_json(self):
        truncated = '<html><script>window.seat_engine_app_config = {"showtime":{"inv'
        assert extract_inventories(truncated) == []

    def test_returns_empty_on_unparseable_json(self):
        garbage = '<html><script>window.seat_engine_app_config = {not json};</script></html>'
        assert extract_inventories(garbage) == []

    def test_skips_non_dict_inventory_items(self):
        cfg = {
            "showtime": {
                "inventories": [
                    {"id": 1, "price": 3500},
                    "not a dict",
                    None,
                    {"id": 2, "price": 5000},
                ]
            }
        }
        invs = extract_inventories(_make_show_html(cfg))
        assert [inv["id"] for inv in invs] == [1, 2]

    def test_handles_braces_inside_string_literals(self):
        cfg = {
            "showtime": {
                "inventories": [
                    {"id": 1, "name": "Tier {A} (the } one)", "price": 4500},
                ]
            }
        }
        invs = extract_inventories(_make_show_html(cfg))
        assert len(invs) == 1
        assert invs[0]["price"] == 4500


class TestCheapestPrice:

    def test_returns_min_positive_price_in_dollars(self):
        invs = [{"price": 3500}, {"price": 9000}, {"price": 7000}]
        assert cheapest_price(invs) == 35.0

    def test_returns_none_for_empty_list(self):
        assert cheapest_price([]) is None

    def test_returns_none_when_all_prices_are_zero_or_missing(self):
        assert cheapest_price([{"price": 0}, {"price": None}, {"name": "x"}]) is None

    def test_treats_zero_price_as_extraction_failure(self):
        # An all-zero set is the silent default-to-zero state we are guarding
        # against — callers must persist NULL instead of $0.
        assert cheapest_price([{"price": 0}, {"price": 0}]) is None

    def test_skips_non_numeric_prices(self):
        assert cheapest_price([{"price": "free"}, {"price": 4500}]) == 45.0

    def test_accepts_numeric_strings(self):
        assert cheapest_price([{"price": "3500"}, {"price": 9000}]) == 35.0


class TestTransformerNullFallback:
    """Guard the silent default-to-zero regression at the transformer boundary."""

    @staticmethod
    def _club():
        return SimpleNamespace(id=42, timezone="America/New_York")

    def _transformer(self):
        return SeatEngineClassicTransformer(self._club())

    def test_no_price_field_yields_null_ticket_price(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/1",
            "sold_out": False,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price is None

    def test_explicit_none_price_passes_through(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/2",
            "sold_out": False,
            "price": None,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price is None

    def test_positive_price_is_preserved(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/3",
            "sold_out": False,
            "price": 35.0,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price == 35.0

    def test_zero_price_is_persisted_as_null(self):
        # If a caller hands the transformer a zero (e.g., legacy raw_data dict),
        # treat it the same as a missing price — never write $0 to the catalog
        # for a paid show.
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/4",
            "sold_out": False,
            "price": 0,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price is None

    def test_sold_out_with_price_unknown_yields_null(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/5",
            "sold_out": True,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].sold_out is True
        assert show.tickets[0].price is None


# ---------------------------------------------------------------------------
# Scraper-level orchestration — _enrich_with_prices end-to-end
# ---------------------------------------------------------------------------


_ENRICH_LISTING_URL = "https://example.com/events"
_ENRICH_BASE = "https://example.com"


def _scraper_club() -> Club:
    c = Club(
        id=999,
        name="Test Venue",
        address="1 Main",
        website="https://example.com",
        popularity=0,
        zip_code="00000",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=c.id,
        platform="custom",
        scraper_key="",
        source_url=_ENRICH_LISTING_URL,
        external_id=None,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def _listing_html(show_hrefs: list) -> str:
    items = "".join(
        f"""
        <div class="event-list-item">
          <h3 class="el-header"><a href="/events/{i}">Show {i}</a></h3>
          <h6 class="event-date">Thu Mar 26 2026, 7:30 PM</h6>
          <a class="btn btn-primary" href="{href}">Buy Tickets</a>
        </div>
        """
        for i, href in enumerate(show_hrefs, start=1)
    )
    return f"<html><body>{items}</body></html>"


def _show_detail_html(prices_cents: list) -> str:
    cfg = {
        "showtime": {
            "inventories": [
                {"id": idx, "name": f"Tier {idx}", "price": p}
                for idx, p in enumerate(prices_cents, start=1)
            ]
        }
    }
    return (
        "<html><head><script>\n"
        f"window.seat_engine_app_config = {json.dumps(cfg)};\n"
        "</script></head><body></body></html>"
    )


@pytest.mark.asyncio
async def test_enrich_with_prices_merges_cheapest_price_per_show():
    """get_data fetches listing then each detail page and writes cheapest price."""
    scraper = SeatEngineClassicScraper(_scraper_club())

    detail_responses = {
        f"{_ENRICH_BASE}/shows/100": _show_detail_html([3500, 9000, 7000]),
        f"{_ENRICH_BASE}/shows/200": _show_detail_html([4500]),
    }

    async def _route(url, *args, **kwargs):
        if url == _ENRICH_LISTING_URL:
            return _listing_html(["/shows/100", "/shows/200"])
        if url == f"{_ENRICH_BASE}/calendar":
            return ""
        return detail_responses.get(url, "")

    scraper.fetch_html = AsyncMock(side_effect=_route)

    page_data = await scraper.get_data(_ENRICH_LISTING_URL)

    by_url = {s["show_url"]: s for s in page_data.event_list}
    assert by_url[f"{_ENRICH_BASE}/shows/100"]["price"] == 35.0
    assert by_url[f"{_ENRICH_BASE}/shows/200"]["price"] == 45.0
    # Listing fetch + calendar probe + one fetch per show URL
    assert scraper.fetch_html.await_count == 4


@pytest.mark.asyncio
async def test_enrich_with_prices_leaves_price_unset_on_fetch_failure():
    """A detail fetch that raises must not crash the pipeline; price stays unset."""
    scraper = SeatEngineClassicScraper(_scraper_club())

    async def _route(url, *args, **kwargs):
        if url == _ENRICH_LISTING_URL:
            return _listing_html(["/shows/300"])
        raise RuntimeError("simulated 5xx")

    scraper.fetch_html = AsyncMock(side_effect=_route)

    page_data = await scraper.get_data(_ENRICH_LISTING_URL)

    assert len(page_data.event_list) == 1
    assert "price" not in page_data.event_list[0]


@pytest.mark.asyncio
async def test_enrich_with_prices_leaves_price_unset_when_no_inventories():
    """A detail page with no embedded config leaves the show's price unset."""
    scraper = SeatEngineClassicScraper(_scraper_club())

    async def _route(url, *args, **kwargs):
        if url == _ENRICH_LISTING_URL:
            return _listing_html(["/shows/400"])
        return "<html><body>no config here</body></html>"

    scraper.fetch_html = AsyncMock(side_effect=_route)

    page_data = await scraper.get_data(_ENRICH_LISTING_URL)
    assert "price" not in page_data.event_list[0]


@pytest.mark.asyncio
async def test_enrich_with_prices_skips_shows_without_show_url():
    """Sold-out shows extracted with show_url=None are not fetched."""
    scraper = SeatEngineClassicScraper(_scraper_club())

    soldout_listing = """
    <html><body>
    <div class="event-list-item">
      <h3 class="el-header"><a href="/events/1">Show A</a></h3>
      <div class="event-times-group">
        <h6 class="event-date align-right">Thu Mar 26 2026</h6>
        <span class="event-btns">
          <span class="event-btn-soldout">SOLD OUT</span>
          <span class="event-btn-inline inactive">7:30 PM</span>
        </span>
      </div>
    </div>
    </body></html>
    """

    async def _route(url, *args, **kwargs):
        if url == _ENRICH_LISTING_URL:
            return soldout_listing
        if url == f"{_ENRICH_BASE}/calendar":
            return ""
        raise AssertionError(f"unexpected detail fetch: {url}")

    scraper.fetch_html = AsyncMock(side_effect=_route)

    page_data = await scraper.get_data(_ENRICH_LISTING_URL)
    assert page_data.event_list[0].get("show_url") is None
    assert "price" not in page_data.event_list[0]
    # Listing fetch + calendar probe — no per-show detail fetches
    assert scraper.fetch_html.await_count == 2
