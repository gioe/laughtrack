"""Unit tests for Grove34EventExtractor (Webflow site)."""

import json
import pytest
from unittest.mock import AsyncMock, patch

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


# ---------------------------------------------------------------------------
# get_next_page_url — strengthened assertion (Fix #937)
# ---------------------------------------------------------------------------

def test_get_next_page_url_returns_url_when_pagination_present_strengthened():
    html = _make_listing_html([], next_page_href="?1a7d9b18_page=2")
    next_url = Grove34EventExtractor.get_next_page_url(html, "https://grove34.com/")
    assert next_url is not None
    assert "1a7d9b18_page=2" in next_url
    assert next_url.startswith("https://grove34.com")


# ---------------------------------------------------------------------------
# Grove34Event.to_show() (Fix #935)
# ---------------------------------------------------------------------------

def _make_club():
    from laughtrack.core.entities.club.model import Club
    return Club(
        id=1,
        name="Grove 34",
        address="34 Grove St, New York, NY",
        website="https://grove34.com",
        scraping_url="https://grove34.com/",
        popularity=50,
        zip_code="10014",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def test_grove34_event_to_show_with_milliseconds():
    """to_show() succeeds with a date that includes milliseconds."""
    club = _make_club()
    event = Grove34Event(
        title="Friday Night Comedy",
        start_date="2026-03-20T01:00:00.000Z",
        show_page_url="https://grove34.com/shows/friday-night-comedy",
    )
    show = event.to_show(club)
    assert show is not None
    assert show.name == "Friday Night Comedy"
    assert show.date is not None
    assert show.date.tzinfo is not None  # timezone-aware


def test_grove34_event_to_show_without_milliseconds():
    """to_show() succeeds with a date that already ends in Z (no milliseconds)."""
    club = _make_club()
    event = Grove34Event(
        title="Saturday Special",
        start_date="2026-03-21T00:00:00Z",
        show_page_url="https://grove34.com/shows/saturday-special",
    )
    show = event.to_show(club)
    assert show is not None
    assert show.name == "Saturday Special"
    assert show.date is not None
    assert show.date.tzinfo is not None


def test_grove34_event_to_show_returns_none_with_bad_date():
    """to_show() returns None when startDate is not a parseable ISO string."""
    club = _make_club()
    event = Grove34Event(
        title="Bad Date Show",
        start_date="not-a-date",
        show_page_url="https://grove34.com/shows/bad-date",
    )
    show = event.to_show(club)
    assert show is None


# ---------------------------------------------------------------------------
# Grove34Scraper async tests (Fix #935)
# ---------------------------------------------------------------------------

@pytest.fixture
def grove34_club():
    from laughtrack.core.entities.club.model import Club
    return Club(
        id=2,
        name="Grove 34",
        address="34 Grove St, New York, NY",
        website="https://grove34.com",
        scraping_url="https://grove34.com/",
        popularity=50,
        zip_code="10014",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        rate_limit=1.0,
        max_retries=1,
        timeout=5,
    )


async def test_collect_scraping_targets_pagination_and_deduplication(monkeypatch, grove34_club):
    """
    Two listing pages with pagination: all unique show URLs are collected,
    duplicates across pages are deduplicated, and pagination is followed.
    """
    from laughtrack.scrapers.implementations.venues.grove_34.scraper import Grove34Scraper

    page1_html = _make_listing_html(
        ["/shows/show-a", "/shows/show-b"],
        next_page_href="?1a7d9b18_page=2",
    )
    page2_html = _make_listing_html(
        ["/shows/show-b", "/shows/show-c"],  # show-b is a duplicate
        next_page_href=None,
    )

    call_count = {"n": 0}

    async def fake_fetch_html_bare(self, url: str) -> str:
        call_count["n"] += 1
        if "1a7d9b18_page=2" in url:
            return page2_html
        return page1_html

    async def fake_rate_limiter_await(url: str) -> None:
        pass

    scraper = Grove34Scraper(grove34_club)
    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_rate_limiter_await)

    targets = await scraper.collect_scraping_targets()

    assert "https://grove34.com/shows/show-a" in targets
    assert "https://grove34.com/shows/show-b" in targets
    assert "https://grove34.com/shows/show-c" in targets
    assert len(targets) == 3  # show-b deduplicated
    assert call_count["n"] == 2  # two listing pages fetched


async def test_collect_scraping_targets_breaks_on_repeated_listing_url(monkeypatch, grove34_club):
    """
    If get_next_page_url() returns the same listing URL twice, the loop breaks
    instead of running indefinitely.
    """
    from laughtrack.scrapers.implementations.venues.grove_34.scraper import Grove34Scraper

    # Pagination link points back to the same base URL — simulates a loop
    looping_html = _make_listing_html(
        ["/shows/show-x"],
        next_page_href="?1a7d9b18_page=1",
    )

    # Make ?1a7d9b18_page=1 resolve back to the same base URL for the test
    call_count = {"n": 0}

    async def fake_fetch_html_bare(self, url: str) -> str:
        call_count["n"] += 1
        return looping_html

    async def fake_rate_limiter_await(url: str) -> None:
        pass

    scraper = Grove34Scraper(grove34_club)
    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_rate_limiter_await)

    # Override get_next_page_url to return the same URL every time
    original_get_next = Grove34EventExtractor.get_next_page_url

    def always_same_url(html_content: str, current_page_url: str):
        # normalize_url strips the trailing slash, so the initial listing_url is
        # "https://grove34.com" (no slash). Return the same value to trigger the
        # visited-URL break on the second iteration.
        return "https://grove34.com"  # always returns the normalized start URL

    monkeypatch.setattr(Grove34EventExtractor, "get_next_page_url", staticmethod(always_same_url))

    targets = await scraper.collect_scraping_targets()

    # Should only have fetched once before the loop broke on the repeated URL
    assert call_count["n"] == 1
    assert targets == ["https://grove34.com/shows/show-x"]


async def test_get_data_returns_grove34_page_data(monkeypatch, grove34_club):
    """get_data() fetches a show detail page and returns Grove34PageData."""
    from laughtrack.scrapers.implementations.venues.grove_34.scraper import Grove34Scraper
    from laughtrack.scrapers.implementations.venues.grove_34.data import Grove34PageData

    detail_html = _make_detail_html(
        name="Comedy Thursday",
        start_date="2099-04-02T01:00:00.000Z",
        description="Stand-up showcase",
    )

    async def fake_fetch_html_bare(self, url: str) -> str:
        return detail_html

    scraper = Grove34Scraper(grove34_club)
    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("https://grove34.com/shows/comedy-thursday")

    assert result is not None
    assert isinstance(result, Grove34PageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Comedy Thursday"


async def test_get_data_returns_none_when_no_event(monkeypatch, grove34_club):
    """get_data() returns None when the detail page has no valid Event JSON-LD."""
    from laughtrack.scrapers.implementations.venues.grove_34.scraper import Grove34Scraper

    async def fake_fetch_html_bare(self, url: str) -> str:
        return "<html><body><h1>No events here</h1></body></html>"

    scraper = Grove34Scraper(grove34_club)
    monkeypatch.setattr(Grove34Scraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("https://grove34.com/shows/empty-page")
    assert result is None
