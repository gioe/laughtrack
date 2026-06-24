"""Smoke tests for the generic Tessitura TNEW scraper."""

import json
from datetime import datetime, timezone
from urllib.parse import parse_qs

import pytz

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tessitura_tnew import TessituraTNEWEvent
from laughtrack.scrapers.implementations.api.tessitura_tnew.extractor import extract_events
from laughtrack.scrapers.implementations.api.tessitura_tnew.scraper import TessituraTNEWScraper

EVENTS_URL = "https://purchase.groundlings.com/events?view=list"
API_URL = "https://purchase.groundlings.com/api/products/productionseasons"


def _club(extra_metadata: dict | None = None) -> Club:
    metadata = {"api_url": API_URL, "events_url": EVENTS_URL}
    if extra_metadata:
        metadata.update(extra_metadata)
    source = ScrapingSource(
        id=1,
        club_id=8836,
        platform="custom",
        scraper_key="tessitura_tnew",
        source_url=EVENTS_URL,
        metadata=metadata,
    )
    club = Club(
        id=8836,
        name="The Groundlings Theatre & School",
        address="7307 Melrose Ave",
        website="https://groundlings.com/",
        popularity=0,
        zip_code="90046",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
        scraping_sources=[source],
        active_scraping_source=source,
    )
    return club


PRODUCTIONS = [
    {
        "productionSeasonId": "17748",
        "productionTitle": "Crazy Uncle Joe Show",
        "performances": [
            {
                "id": 18349,
                "performanceDate": "2026-09-17T20:00:00-07:00",
                "iso8601DateString": "2026-09-17T20:00:00",
                "performanceTitle": "Crazy Uncle Joe Show",
                "actionUrl": "https://purchase.groundlings.com/17748/18349",
                "isPerformanceVisible": True,
                "isOnSale": True,
            },
            {
                "id": 99999,
                "performanceDate": "2026-09-18T20:00:00-07:00",
                "performanceTitle": "Hidden",
                "actionUrl": "/17748/99999",
                "isPerformanceVisible": False,
            },
        ],
    },
    {
        "productionSeasonId": "18000",
        "productionTitle": "The Crazy Uncle Joe Show",
        "performances": [
            {
                "id": 18001,
                "iso8601DateString": "2026-10-01T19:30:00",
                "performanceTitle": "",
                "actionUrl": "/18000/18001",
                "isPerformanceVisible": True,
            },
        ],
    },
]


LISTING_HTML = """
<html>
  <body>
    <input name="__RequestVerificationToken" value="token-123" />
    <script>
      var listingStartDate = "2026-09-17T00:00:00.0000000";
      var listingEndDate = "2027-03-17T00:00:00.0000000";
    </script>
  </body>
</html>
"""


def test_extract_events_flattens_performances_and_resolves_urls():
    events = extract_events(PRODUCTIONS, EVENTS_URL)

    assert [event.title for event in events] == [
        "Crazy Uncle Joe Show",
        "Hidden",
        "The Crazy Uncle Joe Show",
    ]
    assert events[2].show_page_url == "https://purchase.groundlings.com/18000/18001"
    assert events[1].is_visible is False


def test_tnew_event_to_show_uses_offset_or_club_timezone():
    offset_event = extract_events(PRODUCTIONS[:1], EVENTS_URL)[0]
    offset_show = offset_event.to_show(_club())
    assert offset_show is not None
    local = offset_show.date.astimezone(pytz.timezone("America/Los_Angeles"))
    assert (local.hour, local.minute) == (20, 0)

    naive_event = extract_events(PRODUCTIONS[1:], EVENTS_URL)[0]
    naive_show = naive_event.to_show(_club())
    assert naive_show is not None
    naive_local = naive_show.date.astimezone(pytz.timezone("America/Los_Angeles"))
    assert (naive_local.hour, naive_local.minute) == (19, 30)


def test_hidden_or_past_performance_returns_none():
    hidden = extract_events(PRODUCTIONS[:1], EVENTS_URL)[1]
    assert hidden.to_show(_club()) is None

    past = TessituraTNEWEvent(
        title="Old Show",
        start_date_str="2020-01-01T19:00:00-08:00",
        show_page_url="https://purchase.groundlings.com/1/2",
    )
    assert past.to_show(_club()) is None


async def test_scraper_posts_browser_equivalent_form(monkeypatch):
    scraper = TessituraTNEWScraper(_club())
    calls = {}

    async def fake_fetch_html(url, **kwargs):
        calls["fetch_url"] = url
        return LISTING_HTML

    async def fake_post_form(url, data, **kwargs):
        calls["post_url"] = url
        calls["data"] = data
        calls["headers"] = kwargs["headers"]
        return json.dumps(PRODUCTIONS)

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "post_form", fake_post_form)

    page = await scraper.get_data(EVENTS_URL)

    assert page is not None
    assert len(page.event_list) == 3
    assert calls["fetch_url"] == EVENTS_URL
    assert calls["post_url"] == API_URL
    parsed = parse_qs(calls["data"], keep_blank_values=True)
    assert parsed["keywordIds"] == [""]
    assert parsed["startDate"] == ["2026-09-17T00:00:00-07:00"]
    assert parsed["endDate"] == ["2027-03-17T23:59:59-07:00"]
    assert calls["headers"]["requestverificationtoken"] == "token-123"
    assert calls["headers"]["x-requested-with"] == "XMLHttpRequest"


async def test_mixed_use_keyword_ids_filter_passed_to_api(monkeypatch):
    """A PAC with comedy among many genres sends its Comedy genre id server-side."""
    scraper = TessituraTNEWScraper(_club({"keyword_ids": "78"}))
    calls = {}

    async def fake_fetch_html(url, **kwargs):
        return LISTING_HTML

    async def fake_post_form(url, data, **kwargs):
        calls["data"] = data
        return json.dumps(PRODUCTIONS)

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "post_form", fake_post_form)

    await scraper.get_data(EVENTS_URL)
    parsed = parse_qs(calls["data"], keep_blank_values=True)
    assert parsed["keywordIds"] == ["78"]


async def test_keyword_ids_list_serializes_comma_separated(monkeypatch):
    scraper = TessituraTNEWScraper(_club({"keyword_ids": ["78", "211"]}))
    calls = {}

    async def fake_fetch_html(url, **kwargs):
        return LISTING_HTML

    async def fake_post_form(url, data, **kwargs):
        calls["data"] = data
        return json.dumps(PRODUCTIONS)

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "post_form", fake_post_form)

    await scraper.get_data(EVENTS_URL)
    parsed = parse_qs(calls["data"], keep_blank_values=True)
    assert parsed["keywordIds"] == ["78,211"]


def test_future_show_has_ticket_url():
    event = extract_events(PRODUCTIONS[:1], EVENTS_URL)[0]
    show = event.to_show(_club())
    assert show is not None
    assert show.date > datetime.now(timezone.utc)
    assert show.tickets[0].purchase_url == "https://purchase.groundlings.com/17748/18349"
