"""Tests for the Indy Systems (The Lyric) venue scraper."""

from datetime import datetime

import pytest

from laughtrack.app.registry import discover_scrapers
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.the_lyric.data import TheLyricPageData
from laughtrack.scrapers.implementations.venues.the_lyric.scraper import TheLyricScraper

GRAPHQL_URL = "https://www.lyriccinema.com/graphql"

# Indy returns the current+upcoming catalog as a MovieList { data[] }; a real
# venue mixes ~220 film titles in here. The fixture keeps it small: two comedy
# titles, the mixed "Open Mic" variety night (excluded by default), and a film.
_MOVIES = {
    "data": {
        "currentAndUpcomingMovies": {
            "data": [
                {"id": "20957", "name": "Lyric Comedy Show", "urlSlug": "lyric-comedy-show"},
                {
                    "id": "8103",
                    "name": "Comedy Night w/ The Comedy Brewers",
                    "urlSlug": "comedy-night-w-the-comedy-brewers",
                },
                {"id": "999", "name": "Open Mic", "urlSlug": "open-mic"},
                {"id": "111", "name": "Nosferatu", "urlSlug": "nosferatu"},
            ]
        }
    }
}

_SHOWINGS = {
    "20957": [
        {"id": "s1", "time": "2026-07-25T20:00:00-06:00"},
        {"id": "s2", "time": "2026-11-28T20:00:00-07:00"},
    ],
    "8103": [{"id": "s3", "time": "2026-08-14T20:00:00-06:00"}],
}


def _club(metadata: dict | None = None) -> Club:
    source = ScrapingSource(
        id=1,
        club_id=999,
        platform="custom",
        scraper_key="the_lyric",
        source_url=GRAPHQL_URL,
        metadata=metadata if metadata is not None else {"indy_site_id": 7},
    )
    club = Club(
        id=999,
        name="The Lyric",
        address="1209 N College Ave, Fort Collins, CO 80524",
        website="https://www.lyriccinema.com",
        popularity=0,
        zip_code="80524",
        phone_number="",
        visible=True,
        timezone="America/Denver",
        city="Fort Collins",
        state="CO",
        scraping_sources=[source],
        active_scraping_source=source,
    )
    return club


def _install_fake_post(scraper, monkeypatch, *, captured_headers=None):
    async def fake_post_json(url, data, **kwargs):
        assert url == GRAPHQL_URL
        if captured_headers is not None:
            captured_headers.append(kwargs.get("headers") or {})
        query = data.get("query", "")
        if "currentAndUpcomingMovies" in query:
            return _MOVIES
        if "publicShowingsForMovie" in query:
            movie_id = (data.get("variables") or {}).get("movieId")
            return {
                "data": {"publicShowingsForMovie": {"data": _SHOWINGS.get(movie_id, [])}}
            }
        raise AssertionError(f"unexpected query: {query[:60]}")

    monkeypatch.setattr(scraper, "post_json", fake_post_json)


def test_registry_resolves_the_lyric_key():
    """The scraper is auto-discovered by its `key` attribute."""
    assert discover_scrapers().get("the_lyric") is TheLyricScraper


@pytest.mark.asyncio
async def test_get_data_filters_comedy_and_expands_showings(monkeypatch):
    """Comedy titles expand to one event per showing; Open Mic + films are dropped."""
    scraper = TheLyricScraper(_club())
    headers = []
    _install_fake_post(scraper, monkeypatch, captured_headers=headers)

    page = await scraper.get_data(GRAPHQL_URL)

    assert isinstance(page, TheLyricPageData)
    assert len(page.event_list) == 3  # Lyric Comedy Show x2 + Comedy Brewers x1
    names = {e.name for e in page.event_list}
    assert names == {"Lyric Comedy Show", "Comedy Night w/ The Comedy Brewers"}
    assert "Open Mic" not in names and "Nosferatu" not in names
    # Tenant/scope headers are sent on every call.
    assert headers and all(h.get("site-id") == "7" for h in headers)
    assert all(h.get("client-type") == "consumer" for h in headers)


@pytest.mark.asyncio
async def test_scrape_async_produces_comedy_shows(monkeypatch):
    """End-to-end: targets -> get_data -> transformer pipeline -> Shows."""
    scraper = TheLyricScraper(_club())
    _install_fake_post(scraper, monkeypatch)

    shows = await scraper.scrape_async()

    assert len(shows) == 3
    for show in shows:
        assert show.club_id == 999
        assert isinstance(show.date, datetime)
        assert show.date.tzinfo is not None
        assert show.tickets  # every show emits >= 1 access-record ticket
        assert show.show_page_url.startswith("https://www.lyriccinema.com/movie/")


@pytest.mark.asyncio
async def test_exclude_title_patterns_metadata_override(monkeypatch):
    """metadata.exclude_title_patterns REPLACES the built-in 'Open Mic' default.

    Setting the override to ["Comedy Brewers"] drops the Comedy Brewers improv
    night (a title that is normally kept), proving the metadata list replaces —
    not merges with — the default exclusion.
    """
    scraper = TheLyricScraper(_club(metadata={"indy_site_id": 7, "exclude_title_patterns": ["Comedy Brewers"]}))
    _install_fake_post(scraper, monkeypatch)

    page = await scraper.get_data(GRAPHQL_URL)
    names = {e.name for e in page.event_list}
    assert "Comedy Night w/ The Comedy Brewers" not in names
    assert "Lyric Comedy Show" in names
