"""Unit tests for ScraperMapping._get_all_scrapers() duplicate-key detection.

Verifies that when two BaseScraper subclasses share the same key value:
  - Only the first registered subclass is kept in the returned mapping.
  - Logger.warn is called with a message containing the colliding key name
    and both class names.
"""

from unittest.mock import patch

import pytest

from laughtrack.scrapers.base.base_scraper import BaseScraper


# ---------------------------------------------------------------------------
# Concrete scraper pairs with a shared key
# ---------------------------------------------------------------------------


class _FirstScraper(BaseScraper):
    key = "duplicate_key"

    async def get_data(self, target):
        return None


class _SecondScraper(BaseScraper):
    key = "duplicate_key"

    async def get_data(self, target):
        return None


# ---------------------------------------------------------------------------
# Helper: build a bare ScraperMapping instance (no __init__ side-effects)
# ---------------------------------------------------------------------------


def _make_mapping():
    """Return a ScraperMapping with __init__ bypassed and modules pre-loaded."""
    from laughtrack.infrastructure.config.scraper_mapping import ScraperMapping

    with patch.object(ScraperMapping, "__init__", lambda self, *a, **kw: None):
        mapping = ScraperMapping.__new__(ScraperMapping)
        # Mark scrapers as already loaded so _import_scraper_modules() is a no-op
        mapping._scrapers_loaded = True

    return mapping


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetAllScrapersDuplicateKey:
    def test_first_subclass_is_kept_in_mapping(self):
        mapping = _make_mapping()

        result = mapping._get_all_scrapers()

        assert "duplicate_key" in result
        assert result["duplicate_key"] is _FirstScraper

    def test_second_subclass_is_excluded_from_mapping(self):
        mapping = _make_mapping()

        result = mapping._get_all_scrapers()

        assert result.get("duplicate_key") is not _SecondScraper

    def test_logger_warn_called_with_key_and_both_class_names(self):
        mapping = _make_mapping()

        with patch(
            "laughtrack.infrastructure.config.scraper_mapping.Logger"
        ) as mock_logger:
            mapping._get_all_scrapers()

        # Logger.warn should have been called at least once for the duplicate
        warn_calls = mock_logger.warn.call_args_list
        assert warn_calls, "Logger.warn was not called"

        # At least one call must mention the key and both class names
        messages = [str(call.args[0]) for call in warn_calls]
        matching = [
            m
            for m in messages
            if "duplicate_key" in m
            and "_FirstScraper" in m
            and "_SecondScraper" in m
        ]
        assert matching, (
            f"No Logger.warn call contained the key and both class names. "
            f"Got messages: {messages}"
        )
