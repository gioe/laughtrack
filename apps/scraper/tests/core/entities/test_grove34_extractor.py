"""Unit tests for Grove34EventExtractor (Webflow site)."""

import json
import pytest

from laughtrack.scrapers.implementations.venues.grove_34.extractor import Grove34EventExtractor
from laughtrack.core.entities.event.grove34 import Grove34Event


# ---------------------------------------------------------------------------
# HTML fixture helpers
# ---------------------------------------------------------------------------

def _make_listing_html(show_hrefs: list[str], next_page_href: str | None = None) -> str:
    """Build a minimal Webflow listing page with the given show hrefs."""
    items = "\n".join(
        f'<li role="listitem"><a href="{href}"><h5>Show Title</h5></a></li>'
        for href in show_hrefs
    )
    pagination = ""
    if next_page_href:
        pagination = f'<a href="{next_page_href}">Next</a>'
    return f"""
    <html><body>
      <ul role="list">
        {items}
      </ul>
      {pagination}
    </body></html>
    """


def _make_detail_html(name: str, start_date: str, description: str | None = None, schema_type: str = "Event") -> str:
    """Build a minimal show detail page with JSON-LD."""
    ld = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": name,
        "startDate": start_date,
    }
    if description is not None:
        ld["description"] = description
    return f"""
    <html><head>
      <script type="application/ld+json">{json.dumps(ld)}</script>
    </head><body></body></html>
    """


# ---------------------------------------------------------------------------
# extract_show_urls
# ---------------------------------------------------------------------------

def test_extract_show_urls_finds_absolute_urls():
    html = _make_listing_html([
        "https://grove34.com/shows/jazz-night",
        "https://grove34.com/shows/comedy-hour",
    ])
    urls = Grove34EventExtractor.extract_show_urls(html)
    assert "https://grove34.com/shows/jazz-night" in urls
    assert "https://grove34.com/shows/comedy-hour" in urls
    assert len(urls) == 2


def test_extract_show_urls_converts_relative_urls():
    html = _make_listing_html(["/shows/open-mic", "/shows/headliner-night"])
    urls = Grove34EventExtractor.extract_show_urls(html)
    assert "https://grove34.com/shows/open-mic" in urls
    assert "https://grove34.com/shows/headliner-night" in urls


def test_extract_show_urls_deduplicates():
    html = _make_listing_html([
        "/shows/open-mic",
        "/shows/open-mic",
        "https://grove34.com/shows/open-mic",
    ])
    urls = Grove34EventExtractor.extract_show_urls(html)
    assert urls.count("https://grove34.com/shows/open-mic") == 1
    assert len(urls) == 1


def test_extract_show_urls_strips_query_params_from_show_urls():
    html = _make_listing_html(["/shows/jazz-night?ref=home"])
    urls = Grove34EventExtractor.extract_show_urls(html)
    assert urls == ["https://grove34.com/shows/jazz-night"]


def test_extract_show_urls_returns_empty_when_no_shows():
    html = "<html><body><a href='/about'>About</a><a href='/contact'>Contact</a></body></html>"
    urls = Grove34EventExtractor.extract_show_urls(html)
    assert urls == []


def test_extract_show_urls_ignores_non_show_links():
    html = _make_listing_html(["/shows/friday-special"]) + "<a href='/about'>About</a>"
    urls = Grove34EventExtractor.extract_show_urls(html)
    assert len(urls) == 1
    assert urls[0] == "https://grove34.com/shows/friday-special"


# ---------------------------------------------------------------------------
# get_next_page_url
# ---------------------------------------------------------------------------

def test_get_next_page_url_returns_url_when_pagination_present():
    html = _make_listing_html([], next_page_href="?1a7d9b18_page=2")
    next_url = Grove34EventExtractor.get_next_page_url(html, "https://grove34.com/")
    assert next_url is not None
    assert "1a7d9b18_page=2" in next_url


def test_get_next_page_url_returns_none_when_no_pagination():
    html = _make_listing_html(["/shows/jazz-night"])
    next_url = Grove34EventExtractor.get_next_page_url(html, "https://grove34.com/")
    assert next_url is None


def test_get_next_page_url_builds_url_from_query_param_href():
    html = _make_listing_html([], next_page_href="?1a7d9b18_page=3")
    next_url = Grove34EventExtractor.get_next_page_url(html, "https://grove34.com/")
    # Should be absolute URL with the page param
    assert next_url is not None
    assert next_url.startswith("https://grove34.com")
    assert "1a7d9b18_page=3" in next_url


# ---------------------------------------------------------------------------
# extract_event
# ---------------------------------------------------------------------------

def test_extract_event_returns_grove34_event_from_valid_json_ld():
    html = _make_detail_html(
        name="Friday Night Laughs",
        start_date="2026-03-20T01:00:00.000Z",
        description="A great comedy show",
    )
    show_url = "https://grove34.com/shows/friday-night-laughs"
    event = Grove34EventExtractor.extract_event(html, show_url)

    assert event is not None
    assert isinstance(event, Grove34Event)
    assert event.title == "Friday Night Laughs"
    assert event.start_date == "2026-03-20T01:00:00.000Z"
    assert event.show_page_url == show_url
    assert event.description == "A great comedy show"


def test_extract_event_returns_none_when_type_is_not_event():
    html = _make_detail_html(
        name="Some Organization",
        start_date="2026-03-20T01:00:00.000Z",
        schema_type="Organization",
    )
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/whatever")
    assert event is None


def test_extract_event_returns_none_when_name_missing():
    html = _make_detail_html(name="", start_date="2026-03-20T01:00:00.000Z")
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/no-name")
    assert event is None


def test_extract_event_returns_none_when_start_date_missing():
    html = _make_detail_html(name="Great Show", start_date="")
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/no-date")
    assert event is None


def test_extract_event_returns_none_when_no_json_ld():
    html = "<html><body><h1>Show Page</h1></body></html>"
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/empty")
    assert event is None


def test_extract_event_decodes_html_entities_in_name():
    html = _make_detail_html(name="Jazz &amp; Blues Night", start_date="2026-04-01T00:00:00.000Z")
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/jazz-blues")
    assert event is not None
    assert event.title == "Jazz & Blues Night"


def test_extract_event_description_is_none_when_absent():
    html = _make_detail_html(name="Comedy Night", start_date="2026-05-10T23:00:00.000Z")
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/comedy-night")
    assert event is not None
    assert event.description is None


def test_extract_event_skips_non_event_json_ld_and_finds_event():
    """Page has both a non-Event JSON-LD block and a valid Event block."""
    org_ld = json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": "Grove 34"})
    event_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Special Saturday Show",
        "startDate": "2026-06-06T01:00:00.000Z",
    })
    html = f"""
    <html><head>
      <script type="application/ld+json">{org_ld}</script>
      <script type="application/ld+json">{event_ld}</script>
    </head><body></body></html>
    """
    event = Grove34EventExtractor.extract_event(html, "https://grove34.com/shows/saturday-special")
    assert event is not None
    assert event.title == "Special Saturday Show"
