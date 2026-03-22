"""Unit tests for JSONUtils.extract_json_variable."""

from laughtrack.foundation.utilities.json.utils import JSONUtils


def _wrap(variable_name: str, value_json: str) -> str:
    """Minimal HTML page containing a single var assignment."""
    return f"<script>\nvar {variable_name} = {value_json};\n</script>"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_extracts_simple_dict():
    html = _wrap("EVENT", '{"event_id": "123", "name": "Show"}')
    result = JSONUtils.extract_json_variable(html, "EVENT")
    assert result == {"event_id": "123", "name": "Show"}


def test_extracts_correct_value_with_semicolons_in_string():
    """Semicolons inside string values (e.g. HTML entities) must not truncate."""
    html = _wrap("EVENT", '{"event_id": "42", "desc": "A &amp; B &amp; C"}')
    result = JSONUtils.extract_json_variable(html, "EVENT")
    assert result is not None
    assert result["event_id"] == "42"


def test_extracts_correct_value_with_closing_brace_in_string():
    """A literal } inside a string value must not terminate extraction early."""
    html = _wrap("EVENT", '{"event_id": "99", "desc": "show {feat.} artist"}')
    result = JSONUtils.extract_json_variable(html, "EVENT")
    assert result is not None
    assert result["event_id"] == "99"


def test_extracts_nested_object():
    html = _wrap("DATA", '{"outer": {"inner": 1}, "key": "val"}')
    result = JSONUtils.extract_json_variable(html, "DATA")
    assert result == {"outer": {"inner": 1}, "key": "val"}


def test_ignores_other_variables():
    """Only the named variable is extracted; adjacent assignments are ignored."""
    html = "<script>var OTHER = 1;\nvar EVENT = {\"id\": \"5\"};\n</script>"
    result = JSONUtils.extract_json_variable(html, "EVENT")
    assert result == {"id": "5"}


# ---------------------------------------------------------------------------
# Failure / edge cases
# ---------------------------------------------------------------------------


def test_returns_none_when_variable_not_present():
    html = "<script>var OTHER = {};</script>"
    result = JSONUtils.extract_json_variable(html, "EVENT")
    assert result is None


def test_returns_none_on_empty_html():
    assert JSONUtils.extract_json_variable("", "EVENT") is None


def test_returns_none_when_value_is_not_valid_json():
    html = "<script>var EVENT = {broken json here};</script>"
    result = JSONUtils.extract_json_variable(html, "EVENT")
    assert result is None
