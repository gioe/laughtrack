"""Tests for the club description/hours enrichment extractors."""

import pytest

from laughtrack.utilities.domain.club.enrichment import (
    extract_description,
    extract_hours,
)


# ---------------------------------------------------------------------------
# extract_description
# ---------------------------------------------------------------------------


def test_description_prefers_ldjson_over_meta():
    html = """
    <html><head>
      <meta name="description" content="meta fallback description">
      <script type="application/ld+json">
        {"@type": "ComedyClub", "description": "LD-JSON description wins"}
      </script>
    </head></html>
    """
    assert extract_description(html) == "LD-JSON description wins"


def test_description_falls_back_to_meta_when_ldjson_absent():
    html = '<html><head><meta name="description" content="simple meta"></head></html>'
    assert extract_description(html) == "simple meta"


def test_description_uses_og_description_when_meta_missing():
    html = (
        '<html><head>'
        '<meta property="og:description" content="OG social description">'
        '</head></html>'
    )
    assert extract_description(html) == "OG social description"


def test_description_collapses_whitespace_and_decodes_nbsp():
    html = (
        '<html><head>'
        '<meta name="description" content="multi   line&nbsp;description\n\twith\twhitespace">'
        '</head></html>'
    )
    assert extract_description(html) == "multi line description with whitespace"


def test_description_returns_none_when_nothing_matches():
    assert extract_description("<html><head></head></html>") is None
    assert extract_description("") is None
    assert extract_description(None) is None


def test_description_ignores_invalid_ldjson():
    html = """
    <html><head>
      <meta name="description" content="meta survives bad ldjson">
      <script type="application/ld+json">{this is not json}</script>
    </head></html>
    """
    assert extract_description(html) == "meta survives bad ldjson"


def test_description_truncates_long_text():
    long_desc = "a" * 2000
    html = f'<meta name="description" content="{long_desc}">'
    result = extract_description(html)
    assert result is not None
    assert len(result) <= 1000
    assert result.endswith("\u2026")


def test_description_walks_graph():
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {"@type": "WebPage", "name": "Homepage"},
        {"@type": "ComedyClub", "description": "Nested ComedyClub description"}
      ]
    }
    </script>
    """
    assert extract_description(html) == "Nested ComedyClub description"


# ---------------------------------------------------------------------------
# extract_hours — structured openingHoursSpecification
# ---------------------------------------------------------------------------


def test_hours_from_opening_hours_specification_single_day():
    html = """
    <script type="application/ld+json">
    {
      "@type": "ComedyClub",
      "openingHoursSpecification": [
        {
          "@type": "OpeningHoursSpecification",
          "dayOfWeek": "http://schema.org/Friday",
          "opens": "19:00",
          "closes": "23:30"
        }
      ]
    }
    </script>
    """
    assert extract_hours(html) == {"friday": "7pm-11:30pm"}


def test_hours_from_opening_hours_specification_multiple_days():
    html = """
    <script type="application/ld+json">
    {
      "@type": "ComedyClub",
      "openingHoursSpecification": [
        {
          "dayOfWeek": ["Monday", "Tuesday", "Wednesday"],
          "opens": "17:00",
          "closes": "22:00"
        },
        {
          "dayOfWeek": ["Friday", "Saturday"],
          "opens": "17:00",
          "closes": "02:00"
        }
      ]
    }
    </script>
    """
    assert extract_hours(html) == {
        "monday": "5pm-10pm",
        "tuesday": "5pm-10pm",
        "wednesday": "5pm-10pm",
        "friday": "5pm-2am",
        "saturday": "5pm-2am",
    }


def test_hours_specification_skips_invalid_days():
    html = """
    <script type="application/ld+json">
    {
      "openingHoursSpecification": [
        {"dayOfWeek": "http://schema.org/PublicHolidays", "opens": "10:00", "closes": "20:00"},
        {"dayOfWeek": "http://schema.org/Sunday", "opens": "12:00", "closes": "18:00"}
      ]
    }
    </script>
    """
    # PublicHolidays is not a real day — should be dropped silently.
    assert extract_hours(html) == {"sunday": "12pm-6pm"}


# ---------------------------------------------------------------------------
# extract_hours — openingHours string form
# ---------------------------------------------------------------------------


def test_hours_from_opening_hours_strings():
    html = """
    <script type="application/ld+json">
    {"openingHours": ["Mo-Th 17:00-22:00", "Fr-Sa 17:00-02:00", "Su 12:00-20:00"]}
    </script>
    """
    assert extract_hours(html) == {
        "monday": "5pm-10pm",
        "tuesday": "5pm-10pm",
        "wednesday": "5pm-10pm",
        "thursday": "5pm-10pm",
        "friday": "5pm-2am",
        "saturday": "5pm-2am",
        "sunday": "12pm-8pm",
    }


def test_hours_string_wrap_around_range():
    # "Fr-Mo" wraps through the weekend — exercise the wrap-around branch.
    html = '<script type="application/ld+json">{"openingHours": "Fr-Mo 18:00-23:00"}</script>'
    assert extract_hours(html) == {
        "friday": "6pm-11pm",
        "saturday": "6pm-11pm",
        "sunday": "6pm-11pm",
        "monday": "6pm-11pm",
    }


def test_hours_string_comma_separated_days():
    html = '<script type="application/ld+json">{"openingHours": "Mo,We,Fr 19:00-22:00"}</script>'
    assert extract_hours(html) == {
        "monday": "7pm-10pm",
        "wednesday": "7pm-10pm",
        "friday": "7pm-10pm",
    }


def test_hours_returns_none_when_absent():
    assert extract_hours("<html><head></head></html>") is None
    assert extract_hours("") is None
    assert extract_hours(None) is None


def test_hours_specification_takes_precedence_over_strings():
    html = """
    <script type="application/ld+json">
    {
      "openingHours": ["Mo 09:00-17:00"],
      "openingHoursSpecification": {
        "dayOfWeek": "Monday", "opens": "17:00", "closes": "23:00"
      }
    }
    </script>
    """
    # Structured spec beats the legacy string form on the same node.
    assert extract_hours(html) == {"monday": "5pm-11pm"}


def test_hours_falls_back_to_strings_when_spec_invalid():
    html = """
    <script type="application/ld+json">
    {
      "openingHoursSpecification": [{"dayOfWeek": "", "opens": "17:00", "closes": "23:00"}],
      "openingHours": ["Tu 18:00-22:00"]
    }
    </script>
    """
    assert extract_hours(html) == {"tuesday": "6pm-10pm"}


def test_hours_midnight_and_noon_formatting():
    html = """
    <script type="application/ld+json">
    {
      "openingHoursSpecification": [
        {"dayOfWeek": "Monday", "opens": "00:00", "closes": "12:00"},
        {"dayOfWeek": "Tuesday", "opens": "12:00", "closes": "00:00"}
      ]
    }
    </script>
    """
    assert extract_hours(html) == {
        "monday": "12am-12pm",
        "tuesday": "12pm-12am",
    }


@pytest.mark.parametrize("bad_input", ["not valid ldjson", "{}", "<html/>"])
def test_hours_is_resilient_to_malformed_html(bad_input):
    assert extract_hours(bad_input) is None
