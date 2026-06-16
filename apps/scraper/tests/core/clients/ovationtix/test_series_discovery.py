"""
Tests for the OvationTix series-view discovery augmentation (TASK-2937).

The default "/cal/" discovery page only lists the current month's productions,
so the scraper also fetches the "/series/" view, which lists every upcoming
production on one static page. These tests cover the pure URL/merge helpers and
the scraper's series-fetch method in isolation.
"""

from types import SimpleNamespace

import pytest

from laughtrack.core.clients.ovationtix.extractor import (
    merge_production_ids,
    series_calendar_url,
)
from laughtrack.scrapers.base.ovationtix_productions_scraper import (
    OvationTixProductionsScraper,
)

CAL_PAGE = (
    '<a href="https://ci.ovationtix.com/35490/production/1243838">A</a>'
    '<a href="https://ci.ovationtix.com/35490/production/1251155">B</a>'
)
SERIES_PAGE = (
    '<a href="https://ci.ovationtix.com/35490/production/1243838">A</a>'  # dup
    '<a href="https://ci.ovationtix.com/35490/production/1244650">Jeff Allen</a>'
    '<a href="https://ci.ovationtix.com/35490/production/1267204">Xmas Carol</a>'
)


class TestSeriesCalendarUrl:
    def test_builds_series_url(self):
        assert series_calendar_url("35490") == "https://web.ovationtix.com/trs/series/35490"


class TestMergeProductionIds:
    def test_unions_and_dedupes_preserving_order(self):
        merged = merge_production_ids(["1243838", "1251155"], ["1243838", "1244650"])
        assert merged == ["1243838", "1251155", "1244650"]

    def test_empty_inputs(self):
        assert merge_production_ids([], []) == []

    def test_single_list_passthrough(self):
        assert merge_production_ids(["a", "b", "a"]) == ["a", "b"]


def _bare_scraper():
    """Construct a scraper without the heavy __init__ (DB/transformer/batch)."""
    scraper = object.__new__(OvationTixProductionsScraper)
    scraper.logger_context = {}
    # _log_prefix is a read-only property deriving from self._club.name.
    scraper._club = SimpleNamespace(name="Test Venue")
    return scraper


class TestFetchSeriesProductionIds:
    @pytest.mark.asyncio
    async def test_returns_series_production_ids(self):
        scraper = _bare_scraper()

        async def fake_fetch_html(url, headers=None):
            assert url == "https://web.ovationtix.com/trs/series/35490"
            return SERIES_PAGE

        scraper.fetch_html = fake_fetch_html
        ids = await scraper._fetch_series_production_ids(
            "https://web.ovationtix.com/trs/cal/35490", "35490"
        )
        assert ids == ["1243838", "1244650", "1267204"]

    @pytest.mark.asyncio
    async def test_no_client_id_returns_empty(self):
        scraper = _bare_scraper()
        ids = await scraper._fetch_series_production_ids(
            "https://web.ovationtix.com/trs/cal/35490", None
        )
        assert ids == []

    @pytest.mark.asyncio
    async def test_skips_when_discovery_url_is_already_series(self):
        scraper = _bare_scraper()

        async def fail_fetch(url, headers=None):  # pragma: no cover - must not run
            raise AssertionError("series view should not be re-fetched")

        scraper.fetch_html = fail_fetch
        ids = await scraper._fetch_series_production_ids(
            "https://web.ovationtix.com/trs/series/35490", "35490"
        )
        assert ids == []

    @pytest.mark.asyncio
    async def test_fetch_failure_returns_empty(self):
        scraper = _bare_scraper()

        async def boom(url, headers=None):
            raise RuntimeError("network down")

        scraper.fetch_html = boom
        ids = await scraper._fetch_series_production_ids(
            "https://web.ovationtix.com/trs/cal/35490", "35490"
        )
        assert ids == []
