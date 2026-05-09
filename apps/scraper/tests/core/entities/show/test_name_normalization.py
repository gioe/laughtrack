"""Unit tests for Show name HTML-entity decoding (TASK-2096).

The scraper boundary saw raw `&amp;` and `&#8211;` slipping into 96
production rows from etix and json_ld scrapers. Show.__post_init__ now
calls html.unescape() before whitespace normalization to decode these at
write time.
"""

from datetime import datetime

import pytest

from laughtrack.core.entities.show.model import Show


def _show(name: str) -> Show:
    return Show(
        name=name,
        club_id=42,
        date=datetime(2026, 6, 1, 20, 0, 0),
        show_page_url="https://example.com/show",
        room="Main Room",
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Love is Blindfolded w/ Jason Banks &amp; Henry Allen",
         "Love is Blindfolded w/ Jason Banks & Henry Allen"),
        ("Stand-Up Comedy Class &#8211; July 12, 2026",
         "Stand-Up Comedy Class – July 12, 2026"),
        ("Show with &lt;tag&gt; in name",
         "Show with <tag> in name"),
        ("Numeric &#39;quote&#39;",
         "Numeric 'quote'"),
        ("Hex &#x2014; em-dash",
         "Hex — em-dash"),
    ],
)
def test_html_entities_decoded_in_name(raw: str, expected: str) -> None:
    assert _show(raw).name == expected


def test_already_decoded_name_unchanged() -> None:
    assert _show("Love & Henry").name == "Love & Henry"


def test_nbsp_decoded_then_collapsed_by_whitespace_normalizer() -> None:
    # &nbsp; decodes to U+00A0; whitespace normalizer should collapse it
    # alongside any surrounding spaces into a single ASCII space.
    show = _show("Foo&nbsp;&nbsp;Bar")
    assert show.name == "Foo Bar"
