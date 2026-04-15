"""
Pipeline smoke tests for SimpleTixScraper.

Exercises the extractor against sample HTML fixtures, the transformer
against SimpleTixEvent objects, and get_data() against mocked HTML responses.
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.simpletix import SimpleTixEvent
from laughtrack.scrapers.implementations.api.simpletix.scraper import SimpleTixScraper
from laughtrack.scrapers.implementations.api.simpletix.data import SimpleTixPageData
from laughtrack.scrapers.implementations.api.simpletix.extractor import SimpleTixExtractor
from laughtrack.scrapers.implementations.api.simpletix.transformer import SimpleTixTransformer


SCRAPING_URL = "https://www.simpletix.com/e/comedy-night-tickets-123456"


def _club() -> Club:
    return Club(
        id=999,
        name="Test Comedy Club",
        address="123 Main St",
        website="https://testcomedyclub.com",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

SINGLE_TIME_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Event",
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": "20.00"
  }
}
</script>
</head><body>
<h1>Comedy Night - Tickets</h1>
<script>
var timeArray = [{"Id": 1001, "Time": "Fri, Jan 10, 2099 7:30 PM - 9:00 PM"}];
</script>
</body></html>
"""

MULTI_TIME_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Event",
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": "25.00"
  }
}
</script>
</head><body>
<h1>Weekend Shows</h1>
<script>
var timeArray = [
  {"Id": 2001, "Time": "Fri, Feb 7, 2099 7:00 PM - 8:30 PM"},
  {"Id": 2002, "Time": "Sat, Feb 8, 2099 8:00 PM - 9:30 PM"},
  {"Id": 2003, "Time": "Sun, Feb 9, 2099 6:00 PM - 7:30 PM"}
];
</script>
</body></html>
"""

EMPTY_PAGE_HTML = """
<html><body>
<h1>No Events</h1>
<p>Check back soon!</p>
</body></html>
"""

MISSING_TIME_ARRAY_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Event",
  "offers": {"@type": "AggregateOffer", "lowPrice": "15.00"}
}
</script>
</head><body>
<h1>Some Show</h1>
</body></html>
"""

MISSING_JSON_LD_HTML = """
<html><body>
<h1>Open Mic Night</h1>
<script>
var timeArray = [{"Id": 3001, "Time": "Wed, Mar 5, 2099 9:00 PM - 10:30 PM"}];
</script>
</body></html>
"""

NO_TITLE_HTML = """
<html><body>
<script>
var timeArray = [{"Id": 4001, "Time": "Thu, Apr 3, 2099 8:00 PM - 9:00 PM"}];
</script>
</body></html>
"""

MALFORMED_TIME_ARRAY_HTML = """
<html><body>
<h1>Bad Data</h1>
<script>
var timeArray = [not valid json];
</script>
</body></html>
"""

MULTIPLE_JSON_LD_HTML = """
<html><head>
<script type="application/ld+json">
{"@type": "WebPage", "name": "Comedy Club"}
</script>
<script type="application/ld+json">
{
  "@type": "Event",
  "offers": [
    {"@type": "Offer", "lowPrice": "30.00"},
    {"@type": "Offer", "lowPrice": "15.00"}
  ]
}
</script>
</head><body>
<h1>Special Show</h1>
<script>
var timeArray = [{"Id": 5001, "Time": "Sat, May 3, 2099 9:00 PM - 10:30 PM"}];
</script>
</body></html>
"""

TITLE_WITH_INNER_HTML = """
<html><body>
<h1><span class="event-name">Funny Night</span> - Tickets</h1>
<script>
var timeArray = [{"Id": 6001, "Time": "Fri, Jun 6, 2099 8:00 PM - 9:30 PM"}];
</script>
</body></html>
"""


# ---------------------------------------------------------------------------
# Extractor tests — extract_time_array
# ---------------------------------------------------------------------------


def test_extract_single_time_entry():
    """Extractor parses a single timeArray entry."""
    entries = SimpleTixExtractor.extract_time_array(SINGLE_TIME_HTML)

    assert len(entries) == 1
    assert entries[0]["Id"] == 1001
    assert "Jan 10, 2099" in entries[0]["Time"]


def test_extract_multiple_time_entries():
    """Extractor parses multiple timeArray entries."""
    entries = SimpleTixExtractor.extract_time_array(MULTI_TIME_HTML)

    assert len(entries) == 3
    ids = [e["Id"] for e in entries]
    assert ids == [2001, 2002, 2003]


def test_extract_time_array_empty_page():
    """Extractor returns empty list when no timeArray exists."""
    entries = SimpleTixExtractor.extract_time_array(EMPTY_PAGE_HTML)
    assert entries == []


def test_extract_time_array_missing():
    """Extractor returns empty list when HTML has no timeArray variable."""
    entries = SimpleTixExtractor.extract_time_array(MISSING_TIME_ARRAY_HTML)
    assert entries == []


def test_extract_time_array_malformed_json():
    """Extractor returns empty list when timeArray contains invalid JSON."""
    entries = SimpleTixExtractor.extract_time_array(MALFORMED_TIME_ARRAY_HTML)
    assert entries == []


# ---------------------------------------------------------------------------
# Extractor tests — extract_title
# ---------------------------------------------------------------------------


def test_extract_title_strips_tickets_suffix():
    """Extractor strips ' - Tickets' suffix from the h1 title."""
    title = SimpleTixExtractor.extract_title(SINGLE_TIME_HTML)
    assert title == "Comedy Night"


def test_extract_title_without_suffix():
    """Extractor returns the h1 text as-is when no suffix is present."""
    title = SimpleTixExtractor.extract_title(MULTI_TIME_HTML)
    assert title == "Weekend Shows"


def test_extract_title_strips_inner_html():
    """Extractor strips nested HTML tags from the h1 content."""
    title = SimpleTixExtractor.extract_title(TITLE_WITH_INNER_HTML)
    assert title == "Funny Night"


def test_extract_title_returns_none_when_missing():
    """Extractor returns None when no h1 tag exists."""
    title = SimpleTixExtractor.extract_title(NO_TITLE_HTML)
    assert title is None


def test_extract_title_from_empty_page():
    """Extractor returns title even when there are no events."""
    title = SimpleTixExtractor.extract_title(MISSING_TIME_ARRAY_HTML)
    assert title == "Some Show"


# ---------------------------------------------------------------------------
# Extractor tests — extract_json_ld_price
# ---------------------------------------------------------------------------


def test_extract_json_ld_price():
    """Extractor parses the lowPrice from JSON-LD AggregateOffer."""
    price = SimpleTixExtractor.extract_json_ld_price(SINGLE_TIME_HTML)
    assert price == 20.0


def test_extract_json_ld_price_returns_none_when_missing():
    """Extractor returns None when no JSON-LD script exists."""
    price = SimpleTixExtractor.extract_json_ld_price(MISSING_JSON_LD_HTML)
    assert price is None


def test_extract_json_ld_price_skips_non_offer_ld():
    """Extractor skips JSON-LD blocks without offers and finds the right one."""
    price = SimpleTixExtractor.extract_json_ld_price(MULTIPLE_JSON_LD_HTML)
    assert price == 30.0


def test_extract_json_ld_price_empty_page():
    """Extractor returns None for a page with no JSON-LD at all."""
    price = SimpleTixExtractor.extract_json_ld_price(EMPTY_PAGE_HTML)
    assert price is None


# ---------------------------------------------------------------------------
# Extractor tests — parse_time_entry
# ---------------------------------------------------------------------------


def test_parse_time_entry_standard_format():
    """parse_time_entry parses 'Day, Mon DD, YYYY H:MM PM - H:MM PM'."""
    dt = SimpleTixExtractor.parse_time_entry("Fri, Jan 10, 2099 7:30 PM - 9:00 PM")
    assert dt == datetime(2099, 1, 10, 19, 30)


def test_parse_time_entry_uses_start_time_only():
    """parse_time_entry ignores the end time after the dash."""
    dt = SimpleTixExtractor.parse_time_entry("Sat, Feb 8, 2099 8:00 PM - 11:00 PM")
    assert dt == datetime(2099, 2, 8, 20, 0)


def test_parse_time_entry_returns_none_for_garbage():
    """parse_time_entry returns None for unparseable strings."""
    dt = SimpleTixExtractor.parse_time_entry("not a date")
    assert dt is None


def test_parse_time_entry_returns_none_for_empty_string():
    """parse_time_entry returns None for an empty string."""
    dt = SimpleTixExtractor.parse_time_entry("")
    assert dt is None


# ---------------------------------------------------------------------------
# Extractor tests — extract_events (combined)
# ---------------------------------------------------------------------------


def test_extract_events_returns_all_components():
    """extract_events returns (time_entries, title, price) tuple."""
    entries, title, price = SimpleTixExtractor.extract_events(SINGLE_TIME_HTML)

    assert len(entries) == 1
    assert title == "Comedy Night"
    assert price == 20.0


def test_extract_events_empty_page():
    """extract_events returns empty entries and None price for empty page."""
    entries, title, price = SimpleTixExtractor.extract_events(EMPTY_PAGE_HTML)

    assert entries == []
    assert title == "No Events"
    assert price is None


def test_extract_events_missing_json_ld():
    """extract_events returns None price when JSON-LD is absent."""
    entries, title, price = SimpleTixExtractor.extract_events(MISSING_JSON_LD_HTML)

    assert len(entries) == 1
    assert title == "Open Mic Night"
    assert price is None


def test_extract_events_missing_title():
    """extract_events returns None title when h1 is absent."""
    entries, title, price = SimpleTixExtractor.extract_events(NO_TITLE_HTML)

    assert len(entries) == 1
    assert title is None
    assert price is None


# ---------------------------------------------------------------------------
# get_data() integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches HTML and returns SimpleTixPageData with events."""
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return SINGLE_TIME_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    with patch("laughtrack.scrapers.implementations.api.simpletix.scraper.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2000, 1, 1)
        result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SimpleTixPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Comedy Night"
    assert result.event_list[0].price == 20.0


@pytest.mark.asyncio
async def test_get_data_returns_multiple_events(monkeypatch):
    """get_data() extracts all time entries into events."""
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return MULTI_TIME_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    with patch("laughtrack.scrapers.implementations.api.simpletix.scraper.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2000, 1, 1)
        result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SimpleTixPageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_time_entries(monkeypatch):
    """get_data() returns None when the page has no timeArray."""
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return EMPTY_PAGE_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_fetch_failure(monkeypatch):
    """get_data() returns None when fetch_html returns None."""
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_filters_past_events(monkeypatch):
    """get_data() filters out events with start_date before now."""
    past_html = """
    <html><body>
    <h1>Old Show</h1>
    <script>
    var timeArray = [
      {"Id": 9001, "Time": "Fri, Jan 1, 2000 7:00 PM - 8:00 PM"},
      {"Id": 9002, "Time": "Sat, Jan 10, 2099 8:00 PM - 9:00 PM"}
    ];
    </script>
    </body></html>
    """
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return past_html

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    with patch("laughtrack.scrapers.implementations.api.simpletix.scraper.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 1)
        result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SimpleTixPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].start_date == datetime(2099, 1, 10, 20, 0)


@pytest.mark.asyncio
async def test_get_data_uses_club_name_when_no_title(monkeypatch):
    """get_data() falls back to club.name when the page has no h1."""
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return NO_TITLE_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    with patch("laughtrack.scrapers.implementations.api.simpletix.scraper.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2000, 1, 1)
        result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SimpleTixPageData)
    assert result.event_list[0].name == "Test Comedy Club"


# ---------------------------------------------------------------------------
# Module import smoke tests
# ---------------------------------------------------------------------------


def test_simpletix_package_imports():
    """Verify that the simpletix package exports are importable."""
    from laughtrack.scrapers.implementations.api.simpletix.extractor import SimpleTixExtractor
    from laughtrack.scrapers.implementations.api.simpletix.transformer import SimpleTixTransformer
    from laughtrack.scrapers.implementations.api.simpletix.data import SimpleTixPageData

    assert SimpleTixExtractor is not None
    assert SimpleTixTransformer is not None
    assert SimpleTixPageData is not None


def test_simpletix_event_entity_import():
    """Verify the SimpleTixEvent entity is importable."""
    from laughtrack.core.entities.event.simpletix import SimpleTixEvent

    assert SimpleTixEvent is not None


def test_scraper_class_has_correct_key():
    """SimpleTixScraper.key matches the expected registry key."""
    assert SimpleTixScraper.key == "simpletix"
