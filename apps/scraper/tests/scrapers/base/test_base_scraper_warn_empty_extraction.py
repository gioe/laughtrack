"""Unit tests: BaseScraper._warn_empty_extraction() — TASK-2632 helper.

Centralizes the per-source diagnostic suffix pattern introduced in TASK-2631
(commit dacf5cc8f). The helper exists so a future shape change (fetch_id,
attempt_count, request_id, structured-log marker) touches one definition
site instead of all 42 venue scrapers.
"""

from unittest.mock import patch

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.base.base_scraper import BaseScraper


def _make_club() -> Club:
    _c = Club(
        id=1, name='Test Club', address='', website='https://example.com',
        popularity=0, zip_code='', phone_number='', visible=True,
    )
    _c.active_scraping_source = ScrapingSource(
        id=1, club_id=_c.id, platform='custom', scraper_key='',
        source_url='https://example.com/events', external_id=None,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


class _ConcreteScraper(BaseScraper):
    key = "test"

    async def get_data(self, target):
        return None


_LOGGER = "laughtrack.scrapers.base.base_scraper.Logger"
_URL = "https://venue.example.com/events"


@pytest.fixture
def scraper() -> _ConcreteScraper:
    return _ConcreteScraper(club=_make_club())


@pytest.fixture
def warn_msg():
    """Capture the first positional arg of the most recent Logger.warn call."""
    def _capture(mock) -> str:
        assert mock.warn.called, "Logger.warn was not called"
        return mock.warn.call_args[0][0]
    return _capture


class TestWarnEmptyExtraction:
    def test_html_suffix(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, html="<html>x</html>")
        assert warn_msg(logger) == (
            f"_ConcreteScraper [Test Club]: no events extracted from {_URL} "
            f"(html_len=14)"
        )

    def test_html_empty_string_renders_zero(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, html="")
        assert warn_msg(logger).endswith("(html_len=0)")

    def test_csv_suffix(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, csv="a,b,c\n1,2,3")
        assert warn_msg(logger).endswith("(csv_len=11)")

    def test_payload_suffix_uses_type_name(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, payload={"events": []})
        assert warn_msg(logger).endswith("(payload_type=dict)")

    def test_payload_list_type(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, payload=[])
        # payload=[] is falsy but not None — still records the type
        assert warn_msg(logger).endswith("(payload_type=list)")

    def test_n_items_suffix(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, n_items=0)
        assert warn_msg(logger).endswith("(n_items=0)")

    def test_page_suffix(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, page=4)
        assert warn_msg(logger).endswith("(page=4)")

    def test_extra_dict_appended_verbatim(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(
                _URL, extra={"last_page": 3, "n_candidates": 7},
            )
        assert warn_msg(logger).endswith("(last_page=3, n_candidates=7)")

    def test_subject_override(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, subject="event slugs", html="x")
        assert "no event slugs extracted from" in warn_msg(logger)

    def test_note_appended_after_semicolon(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(
                _URL, payload={"a": 1}, note="future month or S3 miss",
            )
        assert warn_msg(logger).endswith(
            "(payload_type=dict; future month or S3 miss)"
        )

    def test_note_alone_no_leading_semicolon(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, note="all months empty")
        assert warn_msg(logger).endswith("(all months empty)")

    def test_no_kwargs_renders_no_parens(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction("TPAC endpoint https://example.com")
        assert warn_msg(logger) == (
            "_ConcreteScraper [Test Club]: no events extracted from "
            "TPAC endpoint https://example.com"
        )

    def test_multiple_kwargs_joined_with_commas(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, html="abc", page=2)
        assert warn_msg(logger).endswith("(html_len=3, page=2)")

    def test_logger_context_passed_through(self, scraper):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, html="x")
        # second positional arg is the logger_context dict
        assert logger.warn.call_args[0][1] is scraper.logger_context

    def test_uses_warn_not_info(self, scraper):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, html="x")
        # TASK-2631 invariant — GHA WARNING+ filter relies on this level
        logger.warn.assert_called_once()
        logger.info.assert_not_called()

    # ---- None-vs-not-passed semantics (review #4960 finding) --------------
    # Original venues used `len(html) if html else 0` and
    # `type(data).__name__` patterns, so when fetch_html/fetch_json returned
    # None the suffix was still emitted as html_len=0 / payload_type=NoneType.
    # The helper must preserve that signal — caller-passed None still renders.

    def test_html_none_renders_zero(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, html=None)
        assert warn_msg(logger).endswith("(html_len=0)")

    def test_csv_none_renders_zero(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, csv=None)
        assert warn_msg(logger).endswith("(csv_len=0)")

    def test_payload_none_renders_nonetype(self, scraper, warn_msg):
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL, payload=None)
        assert warn_msg(logger).endswith("(payload_type=NoneType)")

    def test_omitted_html_is_skipped(self, scraper, warn_msg):
        # Sanity: not passing html at all (vs passing None) skips the suffix
        with patch(_LOGGER) as logger:
            scraper._warn_empty_extraction(_URL)
        msg = warn_msg(logger)
        assert "html_len" not in msg
        assert "payload_type" not in msg
        assert "csv_len" not in msg
