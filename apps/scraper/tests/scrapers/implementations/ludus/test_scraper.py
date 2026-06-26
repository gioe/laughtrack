"""Smoke tests for LudusScraper using recorded Ludus embed + detail fixtures.

Fixtures captured 2026-06-20 from parktheatreholland.ludus.com (curl_cffi
impersonate=chrome120 to clear Cloudflare), trimmed to a handful of cards:
  - embed.html : 3 comedy cards (Mitch Fatel, Cam Bertrand, Radiohead tribute
    mis-tag) + 2 non-comedy cards
  - detail.html: one upcoming showtime (Sunday, July 12, 2026 7:00 PM)
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.ludus.extractor import (
    detail_url_for_show,
    embed_url_for_subdomain,
    extract_show_cards,
    extract_showtimes,
)
from laughtrack.scrapers.implementations.ludus.scraper import LudusScraper

_FIXTURES = Path(__file__).parent / "fixtures"
_EMBED = (_FIXTURES / "embed.html").read_text()
_DETAIL = (_FIXTURES / "detail.html").read_text()


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=9100,
        name="Park Theatre",
        address="248 S River Ave",
        website="https://parktheatreholland.org",
        popularity=0,
        zip_code="49423",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
        city="Holland",
        state="MI",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        platform="custom",
        scraper_key="ludus",
        source_url="https://parktheatreholland.ludus.com/",
        metadata={
            "ludus_subdomain": "parktheatreholland",
            "comedy_category_id": "468",
            # comedy_filter intentionally OFF here so the smoke test stays DB-free;
            # the keyword/comedian filter is covered by test_full_scrape_live.
        },
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_url_builders():
    assert (
        embed_url_for_subdomain("parktheatreholland")
        == "https://parktheatreholland.ludus.com/embed/index.php?widget=1&sections=all&hideNav=false"
    )
    assert (
        detail_url_for_show("parktheatreholland", "200509131")
        == "https://parktheatreholland.ludus.com/index.php?show_id=200509131"
    )


def test_extract_show_cards_filters_by_category():
    cards = extract_show_cards(_EMBED, "468")
    # 3 cards carry category 468; the 2 non-comedy cards are excluded.
    ids = {sid for sid, _ in cards}
    assert "200509131" in ids  # Mitch Fatel
    assert "200529894" in ids  # Cam Bertrand
    assert "200536480" in ids  # Radiohead tribute (mis-tag, kept at category stage)
    assert len(cards) == 3
    titles = {sid: t for sid, t in cards}
    # Title trimmed at the " ★ <Venue>" separator.
    assert titles["200509131"] == "Comedian Mitch Fatel w/ Jordan Garnett"
    assert "Park Theatre" not in titles["200509131"]


def test_extract_show_cards_other_category_empty():
    assert extract_show_cards(_EMBED, "999") == []
    assert extract_show_cards("", "468") == []


def test_extract_show_cards_keep_all_without_category():
    """Dedicated comedy venue (no category id) -> every card is kept."""
    # The fixture's 5 cards all carry a data-show-id; with no category filter the
    # extractor returns all of them regardless of data-event-categories.
    all_cards = extract_show_cards(_EMBED)
    none_cards = extract_show_cards(_EMBED, None)
    assert all_cards == none_cards
    # Superset of the 3 category-468 cards (the 2 non-comedy cards are now kept).
    cat_ids = {sid for sid, _ in extract_show_cards(_EMBED, "468")}
    all_ids = {sid for sid, _ in all_cards}
    assert cat_ids <= all_ids
    assert len(all_ids) >= len(cat_ids)
    assert extract_show_cards("") == []


def test_extract_showtimes():
    times = extract_showtimes(_DETAIL)
    assert times == [datetime(2026, 7, 12, 19, 0)]


def test_extract_showtimes_skips_past_and_empty():
    past = (
        "<div class='showtimes_item' data-past-date='1'>"
        "Sunday, January 5, 2020 7:00 PM</div>"
    )
    assert extract_showtimes(past) == []
    assert extract_showtimes("") == []


@pytest.mark.asyncio
async def test_collect_targets_and_get_data(monkeypatch, club):
    scraper = LudusScraper(club)

    async def fake_fetch(url):
        return _DETAIL if "show_id=" in url else _EMBED

    monkeypatch.setattr(scraper, "_fetch", fake_fetch)

    targets = await scraper.collect_scraping_targets()
    # comedy_filter off → all 3 category-468 cards become detail targets.
    assert len(targets) == 3
    assert all("show_id=" in t for t in targets)

    page = await scraper.get_data(
        "https://parktheatreholland.ludus.com/index.php?show_id=200509131"
    )
    assert page is not None
    assert len(page.event_list) == 1
    ev = page.event_list[0]
    assert ev.title == "Comedian Mitch Fatel w/ Jordan Garnett"
    assert ev.start == datetime(2026, 7, 12, 19, 0)


@pytest.mark.asyncio
async def test_full_scrape_builds_shows(monkeypatch, club):
    scraper = LudusScraper(club)

    async def fake_fetch(url):
        return _DETAIL if "show_id=" in url else _EMBED

    monkeypatch.setattr(scraper, "_fetch", fake_fetch)

    shows = await scraper.scrape_async()
    # 3 comedy cards × 1 showtime each (same detail fixture).
    assert len(shows) == 3
    for show in shows:
        assert show.club_id == club.id
        assert show.date is not None
        assert show.tickets
        assert show.tickets[0].purchase_url.startswith(
            "https://parktheatreholland.ludus.com/index.php?show_id="
        )


def _dedicated_club(metadata: dict) -> Club:
    """A category-less dedicated comedy venue (ComedySportz STL style)."""
    c = Club(
        id=9200,
        name="ComedySportz St. Louis",
        address="2443 Creve Coeur Mill Rd",
        website="https://www.cszstlouis.com/",
        popularity=0,
        zip_code="63043",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Maryland Heights",
        state="MO",
    )
    c.active_scraping_source = ScrapingSource(
        id=2,
        platform="custom",
        scraper_key="ludus",
        source_url="https://hatonahatcomedy.ludus.com/",
        metadata=metadata,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def test_filter_titles_include_allowlist_keeps_only_matches():
    """include_title_patterns keeps the comedy series, drops the class — the
    ComedySportz STL case where data-event-categories is empty and the keyword
    comedy_filter would wrongly keep 'Intro to Improv' and drop 'ComedySportz'."""
    club = _dedicated_club({
        "ludus_subdomain": "hatonahatcomedy",
        "include_title_patterns": ["ComedySportz"],
    })
    scraper = LudusScraper(club)
    cards = [("200537127", "ComedySportz"), ("200514417", "Intro to Improv - 101")]
    kept = scraper._filter_titles(cards)
    assert kept == [("200537127", "ComedySportz")]


def test_filter_titles_exclude_drops_matches():
    club = _dedicated_club({
        "ludus_subdomain": "hatonahatcomedy",
        "exclude_title_patterns": ["Intro to Improv", "Workshop"],
    })
    scraper = LudusScraper(club)
    cards = [("1", "ComedySportz"), ("2", "Intro to Improv - 101"), ("3", "Improv Workshop")]
    assert scraper._filter_titles(cards) == [("1", "ComedySportz")]


def test_filter_titles_noop_without_patterns():
    """No include/exclude config -> cards pass through untouched (categorized
    mixed-use venues like Park Theatre are unchanged)."""
    club = _dedicated_club({"ludus_subdomain": "hatonahatcomedy"})
    scraper = LudusScraper(club)
    cards = [("1", "ComedySportz"), ("2", "Intro to Improv - 101")]
    assert scraper._filter_titles(cards) == cards


@pytest.mark.asyncio
async def test_collect_targets_category_less_with_allowlist(monkeypatch):
    """End-to-end: a dedicated venue with no category id + an include allowlist
    keeps only the matching card as a detail target."""
    embed = (
        '<div class="show_item" data-show-id="111" data-event-categories="">'
        '<h2 class="show_item_title">ComedySportz</h2></div>'
        '<div class="show_item" data-show-id="222" data-event-categories="">'
        '<h2 class="show_item_title">Intro to Improv - 101</h2></div>'
    )
    club = _dedicated_club({
        "ludus_subdomain": "hatonahatcomedy",
        "include_title_patterns": ["ComedySportz"],
    })
    scraper = LudusScraper(club)

    async def fake_fetch(url):
        return _DETAIL if "show_id=" in url else embed

    monkeypatch.setattr(scraper, "_fetch", fake_fetch)
    targets = await scraper.collect_scraping_targets()
    assert targets == ["https://hatonahatcomedy.ludus.com/index.php?show_id=111"]


@pytest.mark.asyncio
async def test_comedy_filter_drops_mistags_with_stubbed_handlers(monkeypatch, club):
    """With comedy_filter on, the Radiohead tribute (no comedy keyword, not a
    known comedian) is dropped while keyword/known-comedian titles survive."""
    club.active_scraping_source.metadata = {
        "ludus_subdomain": "parktheatreholland",
        "comedy_category_id": "468",
        "comedy_filter": True,
    }
    scraper = LudusScraper(club)

    async def fake_fetch(url):
        return _DETAIL if "show_id=" in url else _EMBED

    monkeypatch.setattr(scraper, "_fetch", fake_fetch)

    # Stub the DB-backed name match: Cam Bertrand resolves to a known comedian,
    # Radiohead does not. (Mitch Fatel passes the cheap keyword check first.)
    class _Comedian:
        def __init__(self, name):
            self.name = name

    def fake_name_match(name_tuples):
        out = {}
        for (title,) in name_tuples:
            if "Cam Bertrand" in title:
                out[title] = [_Comedian("Cam Bertrand")]
        return out

    monkeypatch.setattr(
        scraper._lineup_handler, "get_comedians_from_show_names", fake_name_match
    )
    monkeypatch.setattr(
        scraper._comedian_handler,
        "get_stored_popularity_by_names",
        lambda names: {n: 99.0 for n in names},
    )

    targets = await scraper.collect_scraping_targets()
    # Mitch Fatel (keyword) + Cam Bertrand (known comedian) kept; Radiohead dropped.
    assert len(targets) == 2
    kept_ids = {t.split("show_id=")[1] for t in targets}
    assert "200536480" not in kept_ids  # Radiohead tribute dropped
