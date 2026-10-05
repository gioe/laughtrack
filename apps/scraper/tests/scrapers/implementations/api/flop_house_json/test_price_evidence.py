import asyncio
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import time_machine
from bs4 import BeautifulSoup

from laughtrack.core.entities.event.flop_house_json import FlopHouseJsonEvent
from laughtrack.scrapers.implementations.api.flop_house_json.pricing import eventbrite_id, extract_admission
from laughtrack.scrapers.implementations.api.flop_house_json.scraper import FlopHouseJsonScraper
from laughtrack.scrapers.implementations.api.flop_house_json import scraper as scraper_module
from .test_pipeline_smoke import _club, _event_groups

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/venues"
NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)


def fixture(index=0):
    return (AUDIT / f"flop_house_json-{index}.html").read_text()


def source(index=0):
    for node in BeautifulSoup(fixture(index), "html.parser").select('script[type="application/ld+json"]'):
        data = json.loads(node.string or node.get_text())
        if data.get("@type") == "Event":
            return data
    raise AssertionError("Retained Event missing")


def event(index=0):
    data = source(index)
    return FlopHouseJsonEvent(data["name"], int(datetime.fromisoformat(data["startDate"]).timestamp() * 1000),
        f'https://www.eventbrite.com/e/tickets-{eventbrite_id(data["url"])}')


def html(data):
    return '<script type="application/ld+json">' + json.dumps(data) + '</script>'


@pytest.mark.parametrize("index,price", [(0, 12.51), (1, 19.98)])
def test_real_offer_id_and_date_match_and_retain_price(index, price):
    item = event(index)
    item.admission_price, item.admission_label = extract_admission(fixture(index), item, NOW)
    show = item.to_show(_club())
    assert show.tickets[0].price == price
    assert show.tickets[0].purchase_url == item.show_page_url
    assert "advertised minimum" in show.tickets[0].type
    assert show.date.timestamp() * 1000 == item.start_ms


@pytest.mark.parametrize("index", [0, 1])
def test_expired_retained_offers_are_historical_only(index):
    assert extract_admission(fixture(index), event(index), datetime(2026, 10, 5, tzinfo=timezone.utc)) is None


@pytest.mark.parametrize("field,value", [
    ("priceCurrency", "CAD"), ("priceCurrency", None), ("availability", "SoldOut"),
    ("availability", "PreOrder"), ("availability", None), ("lowPrice", "0"),
    ("lowPrice", "-2"), ("lowPrice", "NaN"), ("lowPrice", "Infinity"),
    ("lowPrice", "n/a"), ("highPrice", "1"), ("highPrice", None),
    ("availabilityStarts", "2026-09-27T02:00:00Z"),
    ("availabilityEnds", "2026-09-25T12:00:00Z"),
    ("availabilityEnds", "2026-09-26T12:00:00Z"),
    ("availabilityStarts", "2026-09-25T12:00:00"),
    ("validFrom", "2026-09-27T02:00:00Z"), ("validThrough", "2026-09-25T12:00:00Z"),
    ("validFrom", "bad"), ("url", "https://www.eventbrite.com/e/tickets-999"),
    ("name", "Table package"), ("name", "Donation"), ("name", "2 tickets"),
    ("description", "2 for 1 deal"), ("eligibleQuantity", {"value": 2}),
    ("offers", [{"name": "Donation", "price": 1}]), ("@type", "Offer"),
])
def test_unsafe_aggregate_stays_unknown(field, value):
    data = source()
    data["offers"][0][field] = value
    assert extract_admission(html(data), event(), NOW) is None


@pytest.mark.parametrize("field,value", [
    ("url", "https://www.eventbrite.com/e/tickets-999"),
    ("startDate", "2026-09-27T23:00:00-04:00"),
    ("startDate", "2026-09-26T23:00:00"),
    ("eventStatus", "https://schema.org/EventCancelled"), ("name", "Group package"),
])
def test_wrong_event_identity_date_or_status_stays_unknown(field, value):
    data = source()
    data[field] = value
    assert extract_admission(html(data), event(), NOW) is None


def test_range_retains_minimum_and_range_wording():
    data = source()
    data["offers"][0]["highPrice"] = "25.02"
    price, label = extract_admission(html(data), event(), NOW)
    assert price == 12.51
    assert "12.51–25.02" in label


def test_unrelated_recommendation_is_ignored_and_conflicts_rejected():
    data = source()
    other = source(1)
    assert extract_admission(html([other, data]), event(), NOW)[0] == 12.51
    conflict = copy.deepcopy(data)
    conflict["offers"][0]["lowPrice"] = "1"
    assert extract_admission(html([data, conflict]), event(), NOW) is None
    assert extract_admission(html([data, data]), event(), NOW)[0] == 12.51


def test_canonical_redirect_must_keep_identity():
    assert extract_admission(f'<link rel="canonical" href="{source()["url"]}">' + html(source()), event(), NOW)
    assert extract_admission('<link rel="canonical" href="https://www.eventbrite.com/e/tickets-999">' + html(source()), event(), NOW) is None


@pytest.mark.parametrize("flag", ["hasDonationTicketsAvailable", "hasExternalTickets"])
def test_eventbrite_page_flags_reject_nonstandard_minimum(flag):
    context = {"props": {"pageProps": {"context": {"basicInfo": {"id": "2002265475938", flag: True}}}}}
    page = html(source()) + '<script id="__NEXT_DATA__">' + json.dumps(context) + '</script>'
    assert extract_admission(page, event(), NOW) is None


@pytest.mark.parametrize("url", ["https://eventbrite.com.evil/e/tickets-123", "http://www.eventbrite.com/e/tickets-123",
    "https://www.eventbrite.com@evil/e/tickets-123", "https://www.eventbrite.com/o/tickets-123", "https://www.eventbrite.com/e/tickets-abc"])
def test_only_valid_eventbrite_identity_is_fetchable(url):
    assert eventbrite_id(url) is None


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
async def test_feed_to_show_retains_matched_admission(monkeypatch):
    scraper = FlopHouseJsonScraper(_club())
    item = event()
    groups = _event_groups(item.start_ms)
    groups[0]["events"][0]["eventbriteId"] = "2002265475938"

    async def fetch_json(url):
        return groups

    async def fetch_html(url, **kwargs):
        return fixture()

    monkeypatch.setattr(scraper, "fetch_json", fetch_json)
    monkeypatch.setattr(scraper, "fetch_html", fetch_html)
    data = await scraper.get_data("https://www.flophousecomedy.com/venues/test_events.json")
    show = data.event_list[0].to_show(_club())
    assert show.tickets[0].price == 12.51
    assert show.tickets[0].purchase_url == item.show_page_url
    assert show.description == "A stand-up comedy showcase."


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
async def test_enrichment_deduplicates_id_and_matches_each_date(monkeypatch):
    scraper = FlopHouseJsonScraper(_club())
    a, b, wrong_date = event(), event(), event()
    b.show_page_url = source()["url"]
    wrong_date.start_ms += 3600000
    calls = []

    async def fetch(url, **kwargs):
        calls.append(url)
        assert kwargs == {"skip_js_fallback": True}
        return fixture()

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    await scraper._enrich_admissions([a, b, wrong_date])
    assert len(calls) == 1
    assert a.admission_price == b.admission_price == 12.51
    assert wrong_date.admission_price is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["empty", "error", "malformed"])
async def test_optional_failures_preserve_show(monkeypatch, failure):
    scraper = FlopHouseJsonScraper(_club())
    item = event()

    async def fetch(url, **kwargs):
        if failure == "error":
            raise RuntimeError("blocked")
        return "" if failure == "empty" else '<script type="application/ld+json">broken</script>'

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    await scraper._enrich_admissions([item])
    show = item.to_show(_club())
    assert show.name == item.title
    assert show.tickets[0].price is None


@pytest.mark.asyncio
async def test_phase_budget_bounds_concurrency_and_cancels_pending_fetches(monkeypatch):
    scraper = FlopHouseJsonScraper(_club())
    monkeypatch.setattr(scraper_module, "_DETAIL_BUDGET", 0.05)
    running = peak = calls = 0

    async def fetch(url, **kwargs):
        nonlocal running, peak, calls
        calls += 1
        running += 1
        peak = max(peak, running)
        try:
            await asyncio.Event().wait()
        finally:
            running -= 1

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    items = [FlopHouseJsonEvent("Show", 1794531600000, f"https://www.eventbrite.com/e/tickets-{i}") for i in range(12)]
    await scraper._enrich_admissions(items)
    assert peak == calls == 4
    assert running == 0
    assert all(item.to_show(_club()).tickets[0].price is None for item in items)


@pytest.mark.asyncio
async def test_per_request_timeout_keeps_unknown_ticket(monkeypatch):
    scraper = FlopHouseJsonScraper(_club())
    monkeypatch.setattr(scraper_module, "_DETAIL_TIMEOUT", 0.01)
    cancelled = False

    async def fetch(url, **kwargs):
        nonlocal cancelled
        try:
            await asyncio.Event().wait()
        finally:
            cancelled = True

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    item = event()
    await scraper._enrich_admissions([item])
    assert cancelled
    assert item.admission_price is None
