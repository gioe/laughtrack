"""
Regression tests for the SimpleTix list-shaped JSON-LD response (TASK-2824).

SimpleTix changed its event pages to emit the JSON-LD block as a top-level
array of event objects instead of a single object. extract_json_ld_price
indexed the parsed payload as a dict (`ld.get("offers")`), crashing every
ImprovCity nightly with "'list' object has no attribute 'get'".
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.simpletix.scraper import SimpleTixScraper
from laughtrack.scrapers.implementations.api.simpletix.data import SimpleTixPageData
from laughtrack.scrapers.implementations.api.simpletix.extractor import SimpleTixExtractor


SCRAPING_URL = "https://www.simpletix.com/e/improvcity-show-tickets-249393"


def _club() -> Club:
    _c = Club(id=786, name='ImprovCity', address='123 Main St', website='https://improvcity.com', popularity=0, zip_code='92660', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# Mirrors the live ImprovCity page shape: the JSON-LD block is a top-level
# array of per-showtime Event objects, each carrying an AggregateOffer list.
LIST_SHAPED_JSON_LD_HTML = """
<html><head>
<script type="application/ld+json">
[
  {
    "@type": "Event",
    "name": "ImprovCity Show - Tickets",
    "startDate": "2099-01-02T19:30:00+00:00",
    "offers": [
      {
        "@type": "AggregateOffer",
        "priceCurrency": "USD",
        "lowPrice": 5.72,
        "highPrice": 20.03
      }
    ]
  },
  {
    "@type": "Event",
    "name": "ImprovCity Show - Tickets",
    "startDate": "2099-01-02T21:30:00+00:00",
    "offers": [
      {
        "@type": "AggregateOffer",
        "priceCurrency": "USD",
        "lowPrice": 5.72,
        "highPrice": 20.03
      }
    ]
  }
]
</script>
</head><body>
<h1>ImprovCity Show - Tickets</h1>
<script>
var timeArray = [
  {"Id": 1330258, "Time": "Fri, Jan 2, 2099 7:30 PM - 9:00 PM"},
  {"Id": 1330261, "Time": "Fri, Jan 2, 2099 9:30 PM - 11:00 PM"}
];
</script>
</body></html>
"""

LIST_SHAPED_NO_OFFERS_HTML = """
<html><head>
<script type="application/ld+json">
["not an object", 42, {"@type": "Event", "name": "Offerless Show"}]
</script>
</head><body>
<h1>Offerless Show</h1>
<script>
var timeArray = [{"Id": 7001, "Time": "Fri, Mar 6, 2099 8:00 PM - 9:30 PM"}];
</script>
</body></html>
"""


def test_extract_json_ld_price_list_shaped():
    """extract_json_ld_price handles a top-level JSON-LD array without crashing."""
    price = SimpleTixExtractor.extract_json_ld_price(LIST_SHAPED_JSON_LD_HTML)
    assert price == 5.72


def test_extract_json_ld_price_list_shaped_skips_non_dict_entries():
    """Non-dict entries in a list-shaped JSON-LD block are skipped, not fatal."""
    price = SimpleTixExtractor.extract_json_ld_price(LIST_SHAPED_NO_OFFERS_HTML)
    assert price is None


def test_extract_events_list_shaped_does_not_crash():
    """extract_events returns full results on a list-shaped JSON-LD page."""
    entries, title, price = SimpleTixExtractor.extract_events(LIST_SHAPED_JSON_LD_HTML)

    assert len(entries) == 2
    assert title == "ImprovCity Show"
    assert price == 5.72


@pytest.mark.asyncio
async def test_get_data_list_shaped_json_ld(monkeypatch):
    """get_data() persists shows from a page with a list-shaped JSON-LD block."""
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return LIST_SHAPED_JSON_LD_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    with patch("laughtrack.scrapers.implementations.api.simpletix.scraper.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2000, 1, 1)
        result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, SimpleTixPageData)
    assert len(result.event_list) == 2
    assert result.event_list[0].name == "ImprovCity Show"
    assert result.event_list[0].price == 5.72
