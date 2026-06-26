"""Unit tests for the generic Arts-People (Neon One) scraper (TASK-3419).

Fixtures are recorded ``app.arts-people.com`` pages for Jesters Dinner Theatre
(org slug ``jest``):
  - ``jest_ticketing_list.html`` — ``index.php?ticketing=jest`` listing two
    current productions (the musical "Brigadoon" + "Front deRanged Improv
    Comedy") as rows in ``table.htable_front_page``.
  - ``jest_show_comedy.html`` — ``index.php?show=39668`` for the comedy show,
    whose ``#TBLperformances`` table lists one dated performance link
    ("Sat, Jul 11th, 2026 at 7:30 pm").
"""

import os

import pytz

from laughtrack.core.entities.event.arts_people import ArtsPeopleEvent
from laughtrack.scrapers.implementations.api.arts_people.extractor import (
    extract_performances,
    extract_show_links,
)

_FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures")
_LIST_URL = "https://app.arts-people.com/index.php?ticketing=jest"
_SHOW_URL = "https://app.arts-people.com/index.php?show=39668"


def _load(name: str) -> str:
    with open(os.path.join(_FIXDIR, name), encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "Jesters Dinner Theatre"
    timezone = "America/Denver"


class TestExtractShowLinks:
    def test_parses_both_productions(self):
        pairs = extract_show_links(_load("jest_ticketing_list.html"), _LIST_URL)
        titles = {t for t, _ in pairs}
        assert "Brigadoon" in titles
        assert "Front deRanged Improv Comedy" in titles
        assert len(pairs) == 2

    def test_detail_urls_absolute_and_carry_show_id(self):
        pairs = dict(
            (t, u) for t, u in extract_show_links(_load("jest_ticketing_list.html"), _LIST_URL)
        )
        comedy_url = pairs["Front deRanged Improv Comedy"]
        assert comedy_url.startswith("https://app.arts-people.com/")
        assert "show=39668" in comedy_url

    def test_empty_html(self):
        assert extract_show_links("", _LIST_URL) == []


class TestExtractPerformances:
    def test_parses_dated_performances_with_title(self):
        events = extract_performances(_load("jest_show_comedy.html"), _SHOW_URL)
        assert len(events) >= 1
        first = events[0]
        assert first.title == "Front deRanged Improv Comedy"
        assert "Jul 11th, 2026 at 7:30 pm" in first.date_str
        assert first.show_page_url == _SHOW_URL

    def test_no_performance_table(self):
        assert extract_performances("<html><body>nope</body></html>", _SHOW_URL) == []


class TestToShow:
    def test_builds_future_show_with_localized_time(self):
        ev = ArtsPeopleEvent(
            title="Front deRanged Improv Comedy",
            date_str="Sat, Jul 11th, 2099 at 7:30 pm",
            show_page_url=_SHOW_URL,
        )
        show = ev.to_show(_Club())
        assert show is not None
        local = show.date.astimezone(pytz.timezone("America/Denver"))
        assert (local.year, local.month, local.day, local.hour, local.minute) == (
            2099, 7, 11, 19, 30,
        )
        assert show.tickets[0].purchase_url == _SHOW_URL

    def test_full_month_name_parses(self):
        ev = ArtsPeopleEvent(
            title="Comedy Night",
            date_str="July 11th, 2099 at 8:00 pm",
            show_page_url=_SHOW_URL,
        )
        assert ev.to_show(_Club()) is not None

    def test_past_show_returns_none(self):
        ev = ArtsPeopleEvent(
            title="Old Improv",
            date_str="Sat, Jan 4th, 2020 at 7:30 pm",
            show_page_url=_SHOW_URL,
        )
        assert ev.to_show(_Club()) is None

    def test_unparseable_date_returns_none(self):
        ev = ArtsPeopleEvent(
            title="Bad", date_str="next thursday", show_page_url=_SHOW_URL
        )
        assert ev.to_show(_Club()) is None


from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.arts_people.scraper import ArtsPeopleScraper


def _make_scraper(metadata=None, source_url=_LIST_URL):
    src = ScrapingSource(
        platform="custom", scraper_key="arts_people", source_url=source_url,
        priority=0, enabled=True, id=1, club_id=999, metadata=metadata or {},
    )
    club = Club(
        id=999, name="Jesters Dinner Theatre", address="224 Main St",
        website="https://jesterstheatre.com/", popularity=0, zip_code="80501",
        phone_number="", visible=True, timezone="America/Denver",
        city="Longmont", state="CO",
        scraping_sources=[src], active_scraping_source=src,
    )
    return ArtsPeopleScraper(club)


class TestCollectScrapingTargetsFilter:
    async def test_include_filter_keeps_only_comedy(self, monkeypatch):
        scraper = _make_scraper(
            metadata={"include_title_patterns": ["comedy", "improv", "stand[ -]?up"]}
        )

        async def fake_fetch(url):
            return _load("jest_ticketing_list.html")

        monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
        targets = await scraper.collect_scraping_targets()
        assert len(targets) == 1
        assert "show=39668" in targets[0]

    async def test_no_filter_keeps_all_productions(self, monkeypatch):
        scraper = _make_scraper(metadata={})

        async def fake_fetch(url):
            return _load("jest_ticketing_list.html")

        monkeypatch.setattr(scraper, "fetch_html", fake_fetch)
        targets = await scraper.collect_scraping_targets()
        assert len(targets) == 2

    async def test_no_source_url_returns_empty(self):
        scraper = _make_scraper(metadata={}, source_url="")
        assert await scraper.collect_scraping_targets() == []
