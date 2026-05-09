"""Tests for ShowHandler.insert_shows scraper-key attribution stamping (TASK-2051).

Covers the `scraper_key` parameter: shows whose last_scraped_by is unset get
stamped with the producing scraper's key before persistence; shows that
already carry a per-row attribution are left alone (e.g. production-company
proxy paths that override per-show).
"""

from unittest.mock import MagicMock, patch

from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.models.operation_result import DatabaseOperationResult


def _handler():
    """Construct a ShowHandler without running its real __init__ (which builds DB connections)."""
    h = ShowHandler.__new__(ShowHandler)
    h.ticket_handler = MagicMock()
    h.tag_handler = MagicMock()
    h.lineup_handler = MagicMock()
    h.comedian_handler = MagicMock()
    return h


def _show(name="A", last_scraped_by=None):
    s = Show(
        name=name,
        club_id=1,
        date=__import__("datetime").datetime(2099, 1, 1, 20, 0, 0),
        show_page_url="https://example.com/show",
    )
    s.last_scraped_by = last_scraped_by
    return s


class TestScraperKeyStamping:
    def test_stamps_unset_shows_with_scraper_key(self):
        h = _handler()
        shows = [_show("A"), _show("B")]
        with patch.object(h, "_process_single_batch", return_value=DatabaseOperationResult()):
            h.insert_shows(shows, scraper_key="live_nation")

        assert all(s.last_scraped_by == "live_nation" for s in shows)

    def test_preserves_per_row_overrides(self):
        """Pre-set per-row attribution is preserved over the bulk scraper_key fallback.

        Forward-looking guard: today every Show enters insert_shows with
        last_scraped_by=None and gets stamped from the bulk argument, but the
        contract on the parameter is "fallback for unset rows" — any future
        per-show attribution path (e.g., a cross-platform aggregator that
        produces shows from multiple producers in one batch) must not have its
        per-row values clobbered by the bulk fallback.
        """
        h = _handler()
        shows = [_show("A", last_scraped_by="comedian_websites"), _show("B")]
        with patch.object(h, "_process_single_batch", return_value=DatabaseOperationResult()):
            h.insert_shows(shows, scraper_key="live_nation")

        assert shows[0].last_scraped_by == "comedian_websites"
        assert shows[1].last_scraped_by == "live_nation"

    def test_no_scraper_key_leaves_field_unset(self):
        """Backward compatibility: callers that don't pass scraper_key still work."""
        h = _handler()
        shows = [_show("A")]
        with patch.object(h, "_process_single_batch", return_value=DatabaseOperationResult()):
            h.insert_shows(shows)

        assert shows[0].last_scraped_by is None


class TestShowWriteBoundaryValidation:
    def test_process_single_batch_drops_far_future_show_before_database_write(self):
        h = _handler()
        show = _show("Sentinel Date")
        h.execute_batch_operation = MagicMock()

        result = h._process_single_batch([show])

        assert result.validation_errors == 1
        assert result.total == 0
        h.execute_batch_operation.assert_not_called()
