"""Unit tests for GothamEventExtractor._extract_event_id_from_html."""

from unittest.mock import MagicMock

from laughtrack.scrapers.implementations.venues.gotham.extractor import GothamEventExtractor


def _extractor() -> GothamEventExtractor:
    mock_club = MagicMock()
    mock_club.as_context.return_value = {}
    return GothamEventExtractor(mock_club, lambda: None)


def _html(description: str = "A great show") -> str:
    return f"""<html><head></head><body>
<script>
var EVENT = {{"event_id":"10187110","event":"The Gotham All-Stars","venue_id":"69725","seller_id":"30025","event_type":"2","description":"{description}","currency":"USD"}};
var EVENT_ID = '10187110';
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_extracts_event_id_from_simple_html():
    ext = _extractor()
    result = ext._extract_event_id_from_html(_html())
    assert result == "10187110"


def test_extracts_event_id_when_description_contains_html_entities():
    """Regression: semicolons in HTML entities (e.g. &amp;) must not truncate the JSON."""
    description = (
        "Comics from Netflix, Showtime, HBO, The Daily Show &amp; The Tonight Show"
    )
    ext = _extractor()
    result = ext._extract_event_id_from_html(_html(description))
    assert result == "10187110"


def test_extracts_event_id_when_description_contains_multiple_semicolons():
    """Multiple semicolons in description (e.g. multiple HTML entities) must not truncate."""
    description = "Show &amp; Tell &lt;p&gt; and more &amp; stuff"
    ext = _extractor()
    result = ext._extract_event_id_from_html(_html(description))
    assert result == "10187110"


# ---------------------------------------------------------------------------
# Edge cases / failure paths
# ---------------------------------------------------------------------------


def test_returns_none_when_no_event_variable():
    ext = _extractor()
    result = ext._extract_event_id_from_html("<html><body>no script here</body></html>")
    assert result is None


def test_returns_none_when_event_has_no_event_id_field():
    html = '<script>var EVENT = {"name":"show","venue":"Gotham"};</script>'
    ext = _extractor()
    result = ext._extract_event_id_from_html(html)
    assert result is None
