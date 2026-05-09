"""Unit tests for HtmlUtils.strip_tags."""

from laughtrack.foundation.utilities.html.utils import HtmlUtils


# ---------------------------------------------------------------------------
# Tag stripping
# ---------------------------------------------------------------------------


def test_strips_simple_tag():
    assert HtmlUtils.strip_tags("<b>Hello</b>") == "Hello"


def test_strips_nested_tags():
    assert HtmlUtils.strip_tags("<div><span>Nested</span></div>") == "Nested"


def test_strips_self_closing_and_attribute_tags():
    assert HtmlUtils.strip_tags('<img src="x" alt="y"/>Caption<br>') == "Caption"


def test_returns_input_when_no_tags():
    assert HtmlUtils.strip_tags("plain text") == "plain text"


# ---------------------------------------------------------------------------
# HTML entity decoding
# ---------------------------------------------------------------------------


def test_decodes_named_entities():
    assert HtmlUtils.strip_tags("Tom &amp; Jerry") == "Tom & Jerry"


def test_decodes_numeric_entities():
    # &#8217; is a right single quotation mark
    assert HtmlUtils.strip_tags("It&#8217;s") == "It’s"


def test_decodes_entities_inside_tags():
    assert HtmlUtils.strip_tags("<p>A &lt; B &amp; C &gt; D</p>") == "A < B & C > D"


# ---------------------------------------------------------------------------
# Default mode: trim only, tags collapse with no replacement
# ---------------------------------------------------------------------------


def test_default_strips_without_replacement():
    # Adjacent tags concatenate the text — no whitespace inserted.
    assert HtmlUtils.strip_tags("<b>Hi</b><span>There</span>") == "HiThere"


def test_default_trims_surrounding_whitespace_only():
    # Internal whitespace is preserved in default mode.
    assert HtmlUtils.strip_tags("   <p>a  b</p>   ") == "a  b"


def test_default_preserves_non_breaking_space():
    # \xa0 is left untouched in default mode.
    assert HtmlUtils.strip_tags("<p>A\xa0B</p>") == "A\xa0B"


# ---------------------------------------------------------------------------
# normalize_whitespace=True
# ---------------------------------------------------------------------------


def test_normalize_replaces_tags_with_space():
    # Tag-as-separator preserves word boundaries that default mode would lose.
    assert (
        HtmlUtils.strip_tags("<b>Hi</b><span>There</span>", normalize_whitespace=True)
        == "Hi There"
    )


def test_normalize_collapses_runs_of_whitespace():
    assert (
        HtmlUtils.strip_tags("<p>a   b\n\nc\td</p>", normalize_whitespace=True)
        == "a b c d"
    )


def test_normalize_replaces_nbsp_with_space():
    assert (
        HtmlUtils.strip_tags("A\xa0\xa0B\xa0C", normalize_whitespace=True) == "A B C"
    )


def test_normalize_decodes_entities():
    assert (
        HtmlUtils.strip_tags("<p>Tom&nbsp;&amp;&nbsp;Jerry</p>", normalize_whitespace=True)
        == "Tom & Jerry"
    )


# ---------------------------------------------------------------------------
# None / empty inputs
# ---------------------------------------------------------------------------


def test_none_returns_empty_string():
    assert HtmlUtils.strip_tags(None) == ""


def test_empty_string_returns_empty_string():
    assert HtmlUtils.strip_tags("") == ""


def test_none_with_normalize_returns_empty_string():
    assert HtmlUtils.strip_tags(None, normalize_whitespace=True) == ""


def test_whitespace_only_returns_empty_after_trim():
    assert HtmlUtils.strip_tags("   \n\t  ") == ""


def test_whitespace_only_with_normalize_returns_empty():
    assert HtmlUtils.strip_tags("   \n\t  ", normalize_whitespace=True) == ""
