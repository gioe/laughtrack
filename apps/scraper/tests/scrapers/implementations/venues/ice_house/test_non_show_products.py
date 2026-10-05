"""Real Que Sera fixtures distinguish admission from post-show drink promotions."""
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.ice_house.scraper import IceHouseScraper

URL = "https://tockify.com/api/ngevent?calname=queseralb&max=200"
FIXTURES = json.loads((Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/platforms/queseralb-matched-representatives.json").read_text())

def scraper(monkeypatch, pages, configured=True):
    club = Club(id=8856, name="Que Sera", address="1923 E 7th St", website="https://queseralb.com",
                popularity=0, zip_code="90813", phone_number="", visible=True, timezone="America/Los_Angeles")
    metadata = {"comedy_filter": True}
    if configured:
        metadata["exclude_title_patterns"] = ["^After Comedy Happy Hour$"]
    club.active_scraping_source = ScrapingSource(id=5914, club_id=8856, platform="custom",
        scraper_key="tockify", source_url=URL, metadata=metadata)
    s = IceHouseScraper(club)
    monkeypatch.setattr(s, "fetch_json", AsyncMock(side_effect=pages))
    monkeypatch.setattr(s.rate_limiter, "await_if_needed", AsyncMock())
    monkeypatch.setattr(s, "fetch_html", AsyncMock(side_effect=AssertionError("No ticket buttons: never extract drink prices")))
    return s

def page(names, more=False):
    return {"events": [copy.deepcopy(FIXTURES[n]) for n in names], "metaData": {"hasNext": more}}

@pytest.mark.asyncio
async def test_real_promotion_excluded_and_bear_city_unknown_price_preserved(monkeypatch):
    s = scraper(monkeypatch, [page(list(FIXTURES))])
    data = await s.get_data(URL)
    assert [e.title for e in data.event_list] == ["Bear City Comedy"]
    show = data.event_list[0].to_show(s.club)
    assert show.tickets[0].price is None
    assert '/queseralb/detail/11/' in show.show_page_url
    s.fetch_html.assert_not_called()

@pytest.mark.asyncio
async def test_promotion_only_page_does_not_hide_later_comedy(monkeypatch):
    later = page(["Bear City Comedy"])
    later['events'][0]['when']['start']['millis'] += 7*86400000
    s = scraper(monkeypatch, [page(["After Comedy Happy Hour"], True), later])
    data = await s.get_data(URL)
    assert [e.title for e in data.event_list] == ["Bear City Comedy"]
    assert s.fetch_json.await_count == 2
    assert 'startms=1790829000001' in s.fetch_json.call_args_list[1].args[0]

@pytest.mark.asyncio
async def test_unconfigured_sources_keep_existing_behavior(monkeypatch):
    s = scraper(monkeypatch, [page(list(FIXTURES))], configured=False)
    assert len((await s.get_data(URL)).event_list) == 2

@pytest.mark.asyncio
async def test_comedy_with_drink_specials_survives(monkeypatch):
    data = page(["Bear City Comedy"])
    data['events'][0]['content']['description']['text'] += ' Stay after comedy for happy hour: $3 Hamms, $5 drinks.'
    s = scraper(monkeypatch, [data])
    events = (await s.get_data(URL)).event_list
    assert [e.title for e in events] == ['Bear City Comedy']
    assert events[0].price is None

@pytest.mark.asyncio
async def test_only_promotions_returns_empty_container_without_price_fetch(monkeypatch):
    s = scraper(monkeypatch, [page(["After Comedy Happy Hour"])])
    assert (await s.get_data(URL)).event_list == []
    s.fetch_html.assert_not_called()
