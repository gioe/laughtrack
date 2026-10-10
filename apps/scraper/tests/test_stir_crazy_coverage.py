"""Native Stir Crazy calendar/detail contracts and safe persistence identity."""

import calendar
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import time_machine

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.stir_crazy.extractor import (
    TZ, calendar_items, excluded_event, extract_details,
)
from laughtrack.scrapers.implementations.venues.stir_crazy.scraper import StirCrazyScraper
from laughtrack.utilities.domain.show.utils import ShowUtils

ROOT = "https://www.stircrazycomedyclub.com"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def payload():
    return json.loads((FIXTURES / "stir_crazy_october.json").read_text())


@pytest.fixture
def scraper():
    club = Club(id=17393, name="Stir Crazy Comedy Club", address="6751 N Sunset Blvd Ste E-206",
                website=ROOT, popularity=0, zip_code="85305", phone_number="", visible=False,
                timezone="America/Phoenix")
    source = ScrapingSource(club_id=17393, platform="custom", scraper_key="stir_crazy", source_url=ROOT + "/calendar")
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return StirCrazyScraper(club)


def test_native_multiple_times_prices_lineup_and_repeat_identity(payload, scraper):
    items = [i for i in calendar_items(payload, 2026, 10, ROOT) if i["name"] == "Monroe Martin"]
    html = (FIXTURES / "stir_crazy_monroe.html").read_text()
    events = extract_details(html, items[0]["url"], items)
    shows = [e.to_show(scraper.club, enhanced=False) for e in events]
    assert len(shows) == 4
    assert [(s.date.hour, s.date.minute) for s in shows] == [(18, 0), (20, 30), (18, 0), (20, 30)]
    assert all(s.tickets[0].price == 25 for s in shows)  # Calendar default zero is not a free ticket.
    assert all(s.tickets[0].purchase_url == "https://stircrazycomedyclub.com/monroe-martin-3528" for s in shows)
    assert [c.name for c in shows[0].lineup] == ["Monroe Martin", "Mike Harris", "Ron Morey"]
    assert all(s.infer_lineup_from_title is False for s in shows)
    repeated = [e.to_show(scraper.club, enhanced=False) for e in extract_details(html, items[0]["url"], items)]
    assert len(ShowUtils.deduplicate_shows(shows + repeated)) == 4


@pytest.mark.parametrize("month", [1, 7, 11])
def test_phoenix_remains_utc_minus_seven(month):
    assert datetime(2030, month, 15, 18, tzinfo=TZ).utcoffset().total_seconds() == -7 * 3600


@pytest.mark.parametrize("title,fixture", [("Stand Up Class Showcase", "showcase"), ("The Open Mic", "openmic")])
def test_boilerplate_person_does_not_create_group_comedian(payload, scraper, title, fixture):
    items = [i for i in calendar_items(payload, 2026, 10, ROOT) if i["name"] == title]
    items = [i for i in items if i["url"] == items[0]["url"]]
    events = extract_details((FIXTURES / f"stir_crazy_{fixture}.html").read_text(), items[0]["url"], items)
    for event in events:
        show = event.to_show(scraper.club, enhanced=False)
        assert title not in [c.name for c in show.lineup]
        assert show.infer_lineup_from_title is False


@pytest.mark.parametrize("title,exclude", [("Stand Up Class Showcase", False), ("The Open Mic", False),
    ("Stand Up Class", True), ("Comedy Workshop", True), ("Private Event", True), ("Gift Tickets", True)])
def test_non_performance_exclusions(title, exclude):
    assert excluded_event({"Title": title}) is exclude


@pytest.mark.parametrize("payload", [{"d": None}, {"d": {"IsSuccess": False}}, {"d": {"IsSuccess": True, "Result": {}}}])
def test_null_or_unsuccessful_envelope_fails(payload):
    with pytest.raises(ValueError):
        calendar_items(payload, 2026, 10, ROOT)


def test_missing_day_or_detail_fails(payload):
    damaged = deepcopy(payload)
    damaged["d"]["Result"]["CalendarDays"].pop()
    with pytest.raises(ValueError, match="incomplete"):
        calendar_items(damaged, 2026, 10, ROOT)
    items = [i for i in calendar_items(payload, 2026, 10, ROOT) if i["name"] == "Monroe Martin"]
    with pytest.raises(ValueError, match="missing"):
        extract_details("<html>Unavailable</html>", items[0]["url"], items)


def test_soldout_retained(payload):
    items = [i for i in calendar_items(payload, 2026, 10, ROOT) if i["name"] == "Monroe Martin"]
    items[0]["sold_out"] = True
    events = extract_details((FIXTURES / "stir_crazy_monroe.html").read_text(), items[0]["url"], items)
    assert len(events) == 4 and events[0].sold_out


def test_native_thanksgiving_closure_is_excluded_without_hiding_broken_events():
    payload = json.loads((FIXTURES / "stir_crazy_november.json").read_text())
    items = calendar_items(payload, 2026, 11, ROOT)
    assert items and all(item["name"] != "No Show Tonight" for item in items)
    closure = next(item for day in payload["d"]["Result"]["CalendarDays"]
                   for item in day["CalendarItems"] if item["Event"]["Title"] == "No Show Tonight")
    closure["Event"]["Title"] = "Unknown Headliner"
    with pytest.raises(ValueError, match="2026-11.*Unknown Headliner.*local URL"):
        calendar_items(payload, 2026, 11, ROOT)


def test_native_same_timestamp_ticket_tiers_are_one_show(scraper):
    payload = json.loads((FIXTURES / "stir_crazy_november.json").read_text())
    items = [i for i in calendar_items(payload, 2026, 11, ROOT) if i["name"] == "Ilya Axelrod"]
    html = (FIXTURES / "stir_crazy_ilya.html").read_text()
    events = extract_details(html, items[0]["url"], items)
    # Calendar also has one row per ticket tier; get_data de-duplicates these.
    shows = ShowUtils.deduplicate_shows([e.to_show(scraper.club, enhanced=False) for e in events])
    assert len(shows) == 1
    assert [(t.type, t.price) for t in shows[0].tickets] == [("General Admission", 60), ("VIP Front Row", 100)]
    assert shows[0].date.hour == 20 and shows[0].date.minute == 30
    with pytest.raises(ValueError, match="conflicting performance"):
        extract_details(html.replace('"name":"Ilya Axelrod"', '"name":"Other Act"', 1), items[0]["url"], items)


def test_identical_native_jsonld_duplicates_are_safe(payload):
    from bs4 import BeautifulSoup
    items = [i for i in calendar_items(payload, 2026, 10, ROOT) if i["name"] == "Monroe Martin"]
    soup = BeautifulSoup((FIXTURES / "stir_crazy_monroe.html").read_text(), "html.parser")
    script = soup.select_one('script[type="application/ld+json"]')
    nodes = json.loads(script.string)
    script.string = json.dumps(nodes + [nodes[0]])
    assert len(extract_details(str(soup), items[0]["url"], items)) == 4


def test_native_unnamed_ga_and_low_inventory_vip_tiers(scraper):
    payload = json.loads((FIXTURES / "stir_crazy_november.json").read_text())
    items = [i for i in calendar_items(payload, 2026, 11, ROOT) if i["name"] == "Comedy Hypnosis Show"]
    html = (FIXTURES / "stir_crazy_hypnosis.html").read_text()
    show = extract_details(html, items[0]["url"], items)[0].to_show(scraper.club, enhanced=False)
    assert [(t.type, t.price) for t in show.tickets] == [
        ("General Admission", 20), ("VIP - Guaranteed Spot in Show + Meet & Greet", 30)]
    assert not any(t.sold_out for t in show.tickets)
    with pytest.raises(ValueError, match="cannot verify distinct ticket tier"):
        extract_details(html.replace("$30.00", "$31.00"), items[0]["url"], items)


@pytest.mark.parametrize("fixture,month,title,names", [
    ("tons", 11, "Tons of Fun", ["Dan Diego", "Gabriel Olivares", "Pete Perez", "Liz Gaynor", "Greg Frieler", "Mike James"]),
    ("nurmi", 10, "Life of Nurmi", ["Kirk Nurmi", "Ashley Rose", "Mike Dapper", "Chris Bennett"]),
    ("hypnosis", 11, "Comedy Hypnosis Show", ["Johnathan Mark Smith", "Mike Harris"]),
    ("jay", 11, "Jay Penn", ["Jay Penn"]),
])
def test_verified_event_path_override_preserves_real_program_acts(scraper, fixture, month, title, names):
    from urllib.parse import urlparse
    payload = json.loads((FIXTURES / ("stir_crazy_october.json" if month == 10 else "stir_crazy_november.json")).read_text())
    items = [i for i in calendar_items(payload, 2026, month, ROOT) if i["name"] == title]
    html = (FIXTURES / f"stir_crazy_{fixture}.html").read_text()
    raw = extract_details(html, items[0]["url"], items)[0]
    assert title not in raw.performers
    overrides = {f"{urlparse(item['url']).path}#{item['start'].date().isoformat()}": names for item in items}
    event = extract_details(html, items[0]["url"], items, overrides)[0]
    show = event.to_show(scraper.club, enhanced=False)
    assert set(names).issubset({c.name for c in show.lineup})
    assert len(show.lineup) == len({c.name for c in show.lineup})
    assert show.infer_lineup_from_title is False
    # An expired or undated correction must not leak onto a reused event slug.
    stale = {urlparse(items[0]["url"]).path + "#2025-01-01": names}
    assert extract_details(html, items[0]["url"], items, stale)[0].performers == raw.performers


@pytest.mark.asyncio
async def test_horizon_includes_endpoint_month_and_year_rollover(scraper, monkeypatch):
    async def post(url, data, **kwargs):
        assert kwargs["headers"]["Referer"].startswith(ROOT + "/calendar?month=")
        if url.endswith("GetMaxMonths"):
            return {"d": 4}
        year, month = data["Year"], data["Month"]
        return {"d": {"IsSuccess": True, "Result": {"CalendarDays": [
            {"DayNumber": day, "CalendarItems": []} for day in range(1, calendar.monthrange(year, month)[1] + 1)
        ]}}}
    mock = AsyncMock(side_effect=post)
    monkeypatch.setattr(scraper, "post_json", mock)
    with time_machine.travel(datetime(2026, 10, 9, tzinfo=TZ), tick=False):
        result = await scraper.get_data(ROOT + "/calendar")
    assert result.event_list == []
    assert [call.args[1] for call in mock.call_args_list[1:]] == [
        {"Month": 10, "Year": 2026}, {"Month": 11, "Year": 2026}, {"Month": 12, "Year": 2026},
        {"Month": 1, "Year": 2027}, {"Month": 2, "Year": 2027},
    ]


@pytest.mark.asyncio
async def test_native_fixture_through_scraper_pipeline(payload, scraper, monkeypatch):
    for day in payload["d"]["Result"]["CalendarDays"]:
        day["CalendarItems"] = [i for i in day["CalendarItems"] if i["Event"]["Title"] == "Monroe Martin"]
    monkeypatch.setattr(scraper, "post_json", AsyncMock(side_effect=[{"d": 0}, payload]))
    detail = AsyncMock(return_value=(FIXTURES / "stir_crazy_monroe.html").read_text())
    monkeypatch.setattr(scraper, "fetch_html", detail)
    with time_machine.travel(datetime(2026, 10, 9, 12, tzinfo=TZ), tick=False):
        data = await scraper.get_data(ROOT + "/calendar")
        shows = scraper.transformation_pipeline.transform(data)
    assert len(shows) == 4
    assert detail.await_count == 1
    assert all(show.club_id == 17393 for show in shows)


@pytest.mark.asyncio
async def test_failed_month_does_not_emit_partial(scraper, monkeypatch):
    monkeypatch.setattr(scraper, "post_json", AsyncMock(side_effect=[{"d": 1}, {"d": None}]))
    with pytest.raises(ValueError):
        await scraper.get_data(ROOT + "/calendar")
