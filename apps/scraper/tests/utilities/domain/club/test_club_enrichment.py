"""Tests for the club description enrichment extractor."""

from laughtrack.utilities.domain.club.enrichment import extract_description

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
    html = "<html><head>" '<meta property="og:description" content="OG social description">' "</head></html>"
    assert extract_description(html) == "OG social description"


def test_description_collapses_whitespace_and_decodes_nbsp():
    html = (
        "<html><head>"
        '<meta name="description" content="multi   line&nbsp;description\n\twith\twhitespace">'
        "</head></html>"
    )
    assert extract_description(html) == "multi line description with whitespace"


def test_description_decodes_common_html_entities():
    html = (
        "<html><head>"
        '<meta name="description" content="Cocktails &amp; laughs &mdash; don&#39;t miss it">'
        "</head></html>"
    )
    assert extract_description(html) == "Cocktails & laughs \u2014 don't miss it"


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
