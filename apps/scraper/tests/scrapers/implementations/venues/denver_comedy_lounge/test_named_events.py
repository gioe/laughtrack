"""Native named-event evidence, identity checks, and bounded detail hydration."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.denver_comedy_lounge.extractor import (
    DenverComedyLoungeExtractor as Extractor,
)
from laughtrack.scrapers.implementations.venues.denver_comedy_lounge.scraper import (
    DenverComedyLoungeScraper,
)

FIXTURES = Path(__file__).parent / "fixtures"
EVENT = json.loads((FIXTURES / "jennifer_gable_event.json").read_text())
LISTING = json.loads((FIXTURES / "jennifer_gable_listing.json").read_text())
URL = EVENT["url"]
LISTING_URL = "https://denvercomedylounge.com/shows"
NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)


def html(obj, streamed=False):
    payload = json.dumps(obj)
    if streamed:
        return "".join(
            f"<script>self.__next_f.push([1,{json.dumps(chunk)}])</script>"
            for chunk in (payload[:111], payload[111:])
        )
    return f'<script type="application/ld+json">{payload}</script>'


def club():
    return Club(id=999, name="Denver Comedy Lounge", address="3559 Larimer St",
                website="https://denvercomedylounge.com", popularity=0, zip_code="80205",
                phone_number="", visible=True, timezone="America/Denver")


@pytest.mark.parametrize("streamed", [False, True])
def test_native_performance_has_verified_start_url_and_price(streamed):
    detail = html(EVENT, streamed)
    show = Extractor.extract_named_show(detail, URL)
    assert show.title == "Jennifer Gable Live In Denver"
    assert show.datetime_str == "2026-12-03 20:00:00"
    assert show.show_page_url == URL
    assert Extractor.extract_offer_price(detail, show, now=NOW) == 33
    transformed = show.to_show(club(), enhanced=False)
    assert transformed.date.astimezone(timezone.utc) == datetime(2026, 12, 4, 3, tzinfo=timezone.utc)
    assert transformed.show_page_url == URL
    assert transformed.tickets[0].purchase_url == URL


@pytest.mark.parametrize("updates", [
    {"startDate": None}, {"startDate": ""}, {"startDate": "bad"},
    {"startDate": "2026-12-03"}, {"startDate": "2026-12-03T20:00:00"},
    {"url": URL + "-different"}, {"url": URL.replace("denvercomedylounge.com", "other.example")},
    {"@type": "EventSeries"}, {"name": None},
    {"eventStatus": "https://schema.org/EventCancelled"},
])
def test_unverified_named_performances_remain_unresolved(updates):
    assert Extractor.extract_named_show(html({**EVENT, **updates}), URL) is None


def test_missing_event_never_infers_time_from_date_slug():
    assert Extractor.extract_named_event_urls(html(LISTING)) == [URL]
    assert Extractor.extract_named_show(html(LISTING), URL) is None
    assert Extractor.extract_named_show(html({"related": EVENT}, streamed=True), URL) is None


@pytest.mark.parametrize("start", ["2026-12-03T21:00:00-07:00", None, "2026-12-03"])
def test_conflicting_or_invalid_matching_event_blocks_resolution(start):
    assert Extractor.extract_named_show(html(EVENT) + html({**EVENT, "startDate": start}), URL) is None


def test_duplicate_matching_event_and_equivalent_utc_timestamp_are_safe():
    duplicate = {**EVENT, "startDate": "2026-12-04T03:00:00Z"}
    show = Extractor.extract_named_show(html(EVENT) + html(duplicate, streamed=True), URL)
    assert show.datetime_str == "2026-12-03 20:00:00"


@pytest.mark.parametrize("start", ["2026-11-01T01:30:00-06:00", "2026-11-01T01:30:00-07:00"])
def test_aware_start_preserves_both_dst_fold_instants(start):
    event = {**EVENT, "startDate": start}
    show = Extractor.extract_named_show(html(event), URL)
    expected = datetime.fromisoformat(start).astimezone(timezone.utc)
    assert show.to_show(club(), enhanced=False).date.astimezone(timezone.utc) == expected
    assert Extractor.extract_offer_price(html(event), show, now=NOW) == 33


def test_listing_deduplicates_identity_and_rejects_foreign_details():
    listing = copy.deepcopy(LISTING)
    duplicate = copy.deepcopy(listing["itemListElement"][0])
    duplicate["item"]["url"] += "/"
    foreign = copy.deepcopy(duplicate)
    foreign["item"]["url"] = URL.replace("denvercomedylounge.com", "other.example")
    listing["itemListElement"].extend([duplicate, foreign])
    assert Extractor.extract_named_event_urls(html(listing)) == [URL]


@pytest.mark.asyncio
async def test_all_named_listing_resolves_with_one_detail_fetch(monkeypatch):
    scraper = DenverComedyLoungeScraper(club())
    calls = []

    async def fetch(url, **kwargs):
        calls.append(url)
        return html(LISTING) if url == LISTING_URL else html(EVENT, streamed=True)

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    data = await scraper.get_data(LISTING_URL)
    assert len(data.event_list) == 1
    assert data.event_list[0].datetime_str == "2026-12-03 20:00:00"
    assert calls == [LISTING_URL, URL]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["missing", "timeout", "error"])
async def test_failed_named_detail_does_not_drop_recurring_show(monkeypatch, failure):
    listing = copy.deepcopy(LISTING)
    recurring_url = "https://denvercomedylounge.com/shows/friday-7pm-2099-06-26"
    listing["itemListElement"].append({"item": {"name": "Friday Night Comedy", "url": recurring_url}})
    scraper = DenverComedyLoungeScraper(club())

    async def fetch(url, **kwargs):
        if url == LISTING_URL:
            return html(listing)
        if url == URL:
            if failure == "timeout":
                raise TimeoutError("detail timeout")
            if failure == "error":
                raise RuntimeError("detail failed")
        return ""

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    data = await scraper.get_data(LISTING_URL)
    assert [s.show_page_url for s in data.event_list] == [recurring_url]
    assert data.event_list[0].price is None


@pytest.mark.asyncio
async def test_all_unresolved_named_listing_returns_no_data(monkeypatch):
    scraper = DenverComedyLoungeScraper(club())

    async def fetch(url, **kwargs):
        return html(LISTING) if url == LISTING_URL else ""

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    assert await scraper.get_data(LISTING_URL) is None
