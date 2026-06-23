"""Unit tests: BaseScraper.compile_title_patterns() — TASK-3250.

Shared helper that compiles case-insensitive title-match regexes from
``scraping_sources.metadata``. Consolidates the parse/compile logic previously
duplicated across eventbrite / sellingticket / showare. Behavior contract:
- reads a str or list value under the given metadata key (+ optional extras)
- returns a list of compiled re.Pattern (all re.IGNORECASE)
- returns [] when nothing is configured
- skips invalid regexes with a warning (re.error guard) instead of raising
"""

import re
from unittest.mock import patch

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.base.base_scraper import BaseScraper

_LOGGER = "laughtrack.scrapers.base.base_scraper.Logger"


def _make_club(metadata: dict) -> Club:
    c = Club(
        id=1, name="Test Club", address="", website="https://example.com",
        popularity=0, zip_code="", phone_number="", visible=True,
    )
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform="custom", scraper_key="",
        source_url="https://example.com/events", external_id=None,
        metadata=metadata,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


class _ConcreteScraper(BaseScraper):
    key = "test"

    async def get_data(self, target):
        return None


def _scraper(metadata: dict) -> _ConcreteScraper:
    return _ConcreteScraper(club=_make_club(metadata))


def test_returns_empty_when_key_absent():
    assert _scraper({}).compile_title_patterns("exclude_title_patterns") == []


def test_compiles_single_string_value():
    pats = _scraper({"exclude_title_patterns": "open mic"}).compile_title_patterns(
        "exclude_title_patterns"
    )
    assert len(pats) == 1
    assert all(isinstance(p, re.Pattern) for p in pats)
    # case-insensitive
    assert pats[0].search("OPEN MIC Night") is not None


def test_compiles_list_value_and_skips_blanks():
    pats = _scraper(
        {"exclude_title_patterns": ["class", "  ", "workshop"]}
    ).compile_title_patterns("exclude_title_patterns")
    assert len(pats) == 2


def test_extra_patterns_are_prepended():
    pats = _scraper({"exclude_title_patterns": ["custom"]}).compile_title_patterns(
        "exclude_title_patterns", extra_patterns=[r"\bclass\b", r"\bcourse\b"]
    )
    assert len(pats) == 3


def test_extra_patterns_only_when_no_metadata():
    pats = _scraper({}).compile_title_patterns(
        "exclude_title_patterns", extra_patterns=[r"\bclass\b"]
    )
    assert len(pats) == 1
    assert pats[0].search("Improv Class") is not None


def test_invalid_regex_is_skipped_with_warning():
    with patch(_LOGGER) as logger:
        pats = _scraper(
            {"exclude_title_patterns": ["(unclosed", r"workshop"]}
        ).compile_title_patterns("exclude_title_patterns")
    assert len(pats) == 1
    assert pats[0].search("Improv Workshop") is not None
    assert logger.warn.called


def test_non_str_non_list_value_yields_empty():
    # A dict (or other unexpected type) under the key is ignored.
    assert _scraper({"exclude_title_patterns": {"a": 1}}).compile_title_patterns(
        "exclude_title_patterns"
    ) == []
