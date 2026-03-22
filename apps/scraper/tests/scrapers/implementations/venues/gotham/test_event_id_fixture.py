"""
Fixture-based smoke test for Gotham event_id HTML extraction.

Uses a pre-recorded Showclix event page HTML fixture to verify that
_extract_event_id_from_html correctly parses a representative page structure.
This catches regressions where page structure changes would silently break
event_id extraction in CI — without requiring network access.
"""

import pathlib
from unittest.mock import MagicMock

from laughtrack.scrapers.implementations.venues.gotham.extractor import GothamEventExtractor

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def _extractor() -> GothamEventExtractor:
    mock_club = MagicMock()
    mock_club.as_context.return_value = {}
    return GothamEventExtractor(mock_club, lambda: None)


def test_extract_event_id_from_showclix_page_fixture():
    """
    _extract_event_id_from_html must return a non-None event_id from the
    pre-recorded Showclix event page fixture.

    Regression guard: if Showclix changes the EVENT variable format or the
    JSON structure, this test fails in CI the night the page structure changes.
    """
    html = (_FIXTURES_DIR / "showclix_event_page.html").read_text(encoding="utf-8")
    ext = _extractor()

    event_id = ext._extract_event_id_from_html(html)

    assert event_id is not None, (
        "event_id extraction returned None from showclix_event_page.html fixture — "
        "the EVENT JS variable or event_id field may have changed structure"
    )
    assert event_id == "10187110", (
        f"Unexpected event_id '{event_id}' — fixture contains event_id 10187110"
    )
