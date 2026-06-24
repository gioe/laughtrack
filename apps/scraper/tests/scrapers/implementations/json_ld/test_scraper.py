"""Tests for the shared JsonLdScraper.

The scraper itself is a thin wrapper around EventExtractor (covered in
test_event_extractor.py). The behavior unique to the scraper class is the
optional ``location_name_filter`` metadata key, which lets a single
multi-venue calendar page be reused by per-venue clubs without a bespoke
scraper subclass (see TASK-2068).
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.json_ld.data import JsonLdPageData
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper


def _wrap_ldjson(obj) -> str:
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


def _multi_venue_html() -> str:
    """Two events at different venues on a single calendar page."""
    river_event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Friday Headliner",
        "startDate": "2099-06-05T20:00:00-04:00",
        "url": "https://example.com/events/friday",
        "location": {
            "@type": "Place",
            "name": "River: A Waterfront Restaurant and Bar",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "1 Riverside Dr",
                "addressLocality": "Wethersfield",
                "addressRegion": "CT",
                "postalCode": "06109",
                "addressCountry": "US",
            },
        },
    }
    other_venue_event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Saturday Showcase",
        "startDate": "2099-06-06T20:00:00-04:00",
        "url": "https://example.com/events/saturday",
        "location": {
            "@type": "Place",
            "name": "Some Other Venue",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "55 Elm St",
                "addressLocality": "Hartford",
                "addressRegion": "CT",
                "postalCode": "06103",
                "addressCountry": "US",
            },
        },
    }
    return f"<html><head>{_wrap_ldjson([river_event, other_venue_event])}</head></html>"


def _calendar_with_detail_urls() -> str:
    calendar_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Event",
                "name": "Calendar Comic",
                "startDate": "2099-06-05T20:00:00-04:00",
                "url": "https://ticketweb.com/calendar-placeholder",
                "sameAs": "https://levity.example.com/comic/calendar-comic",
                "location": {"name": "Levity Example", "address": "1 Main"},
            },
            {
                "@type": "ComedyEvent",
                "name": "Other Comic",
                "startDate": "2099-06-06T20:00:00-04:00",
                "url": "https://ticketweb.com/calendar-placeholder-2",
                "sameAs": "https://levity.example.com/comic/other-comic",
                "location": {"name": "Levity Example", "address": "1 Main"},
            },
        ],
    }
    return f"<html><head>{_wrap_ldjson(calendar_graph)}</head></html>"


def _collection_page_with_detail_urls() -> str:
    collection_page = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Upcoming Events | Uptown Theater",
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "url": "/events/tracy-morgan"},
                {"@type": "ListItem", "url": "https://www.uptownpvd.com/events/late-show"},
            ],
        },
    }
    return f"<html><head>{_wrap_ldjson(collection_page)}</head></html>"


def _tickettailor_listing(page: int) -> str:
    next_link = (
        '<a href="/events/westrivercomedyclub?page=2" aria-label="next">Next</a>'
        if page == 1
        else ""
    )
    event_id = "2196315" if page == 1 else "2160756"
    return f"""
    <html><body>
      <a href="/events/westrivercomedyclub/{event_id}">Details</a>
      <a href="/events/westrivercomedyclub/{event_id}">Duplicate</a>
      <a href="/events/westrivercomedyclub/{event_id}/select-date?modal_widget=true">Select date</a>
      {next_link}
    </body></html>
    """


def _detail_html(name: str, ticket_url: str) -> str:
    event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": name,
        "startDate": "2099-06-05T20:00:00-04:00",
        "url": ticket_url,
        "location": {"name": "Levity Example", "address": "1 Main"},
        "offers": {
            "@type": "Offer",
            "url": ticket_url,
            "price": "25",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
        },
    }
    return f"<html><head>{_wrap_ldjson(event)}</head></html>"


def _make_club(metadata: dict | None = None) -> Club:
    club = Club(
        id=1350,
        name="Brew HaHa Comedy at River",
        address="1 Riverside Dr",
        website="https://comedycraftbeer.com",
        popularity=0,
        zip_code="06109",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="json_ld",
        source_url="https://comedycraftbeer.com/calendar",
        external_id=None,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


class TestDetailFetch:
    """Verify metadata-driven two-pass JSON-LD detail page scraping."""

    @pytest.mark.asyncio
    async def test_detail_fetch_harvests_urls_and_rewrites_show_page_url(self, monkeypatch):
        detail_html = {
            "https://levity.example.com/comic/calendar-comic": _detail_html(
                "Calendar Comic Late",
                "https://ticketweb.com/calendar-comic-late",
            ),
            "https://levity.example.com/comic/other-comic": _detail_html(
                "Other Comic Early",
                "https://ticketweb.com/other-comic-early",
            ),
        }
        club = _make_club(metadata={
            "detail_fetch": {
                "url_field": "sameAs",
                "set_same_as_to_detail_url": True,
            },
        })
        scraper = JsonLdScraper(club)
        fetched_urls = []

        async def fake_fetch_html(self, url):
            fetched_urls.append(url)
            if url == "https://comedycraftbeer.com/calendar":
                return _calendar_with_detail_urls()
            return detail_html[url]

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        shows = await scraper.scrape_async()

        assert fetched_urls == [
            "https://comedycraftbeer.com/calendar",
            "https://levity.example.com/comic/calendar-comic",
            "https://levity.example.com/comic/other-comic",
        ]
        assert sorted(show.name for show in shows) == [
            "Calendar Comic Late",
            "Other Comic Early",
        ]
        assert sorted(show.show_page_url for show in shows) == [
            "https://levity.example.com/comic/calendar-comic",
            "https://levity.example.com/comic/other-comic",
        ]
        assert sorted(show.tickets[0].purchase_url for show in shows) == [
            "https://ticketweb.com/calendar-comic-late",
            "https://ticketweb.com/other-comic-early",
        ]

    @pytest.mark.asyncio
    async def test_detail_fetch_harvests_collection_page_urls(self, monkeypatch):
        detail_html = {
            "https://comedycraftbeer.com/events/tracy-morgan": _detail_html(
                "Tracy Morgan",
                "https://www.uptownpvd.com/events/tracy-morgan",
            ),
            "https://www.uptownpvd.com/events/late-show": _detail_html(
                "Late Show",
                "https://www.uptownpvd.com/events/late-show",
            ),
        }
        club = _make_club(metadata={
            "detail_fetch": {
                "listing_type": "CollectionPage",
                "url_path": "mainEntity.itemListElement[].url",
            },
        })
        scraper = JsonLdScraper(club)
        fetched_urls = []

        async def fake_fetch_html(self, url):
            fetched_urls.append(url)
            if url == "https://comedycraftbeer.com/calendar":
                return _collection_page_with_detail_urls()
            return detail_html[url]

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        shows = await scraper.scrape_async()

        assert fetched_urls == [
            "https://comedycraftbeer.com/calendar",
            "https://comedycraftbeer.com/events/tracy-morgan",
            "https://www.uptownpvd.com/events/late-show",
        ]
        assert sorted(show.name for show in shows) == ["Late Show", "Tracy Morgan"]
        assert sorted(show.show_page_url for show in shows) == [
            "https://www.uptownpvd.com/events/late-show",
            "https://www.uptownpvd.com/events/tracy-morgan",
        ]

    @pytest.mark.asyncio
    async def test_force_js_rendering_routes_detail_fetches_through_playwright(self, monkeypatch):
        club = _make_club(metadata={
            "force_js_rendering": True,
            "detail_fetch": {
                "url_field": "sameAs",
            },
        })
        scraper = JsonLdScraper(club)
        playwright_urls = []

        async def fail_plain_fetch(self, url):
            raise AssertionError(f"plain fetch_html should not be used for {url}")

        async def fake_playwright_fetch(self, url):
            playwright_urls.append(url)
            if url == "https://comedycraftbeer.com/calendar":
                return _calendar_with_detail_urls()
            return _detail_html("JS Detail", url)

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fail_plain_fetch, raising=False)
        monkeypatch.setattr(JsonLdScraper, "_fetch_html_with_js", fake_playwright_fetch, raising=False)

        shows = await scraper.scrape_async()

        assert playwright_urls == [
            "https://comedycraftbeer.com/calendar",
            "https://levity.example.com/comic/calendar-comic",
            "https://levity.example.com/comic/other-comic",
        ]
        assert sorted(show.name for show in shows) == ["JS Detail", "JS Detail"]

    @pytest.mark.asyncio
    async def test_detail_fetch_harvests_anchor_urls_across_listing_pagination(self, monkeypatch):
        club = _make_club(metadata={
            "force_js_rendering": True,
            "detail_fetch": {
                "url_path_prefix": "/events/westrivercomedyclub/",
                "exclude_url_path_suffixes": ["/select-date"],
                "pagination": {
                    "enabled": True,
                    "max_pages": 10,
                },
            },
        })
        club.active_scraping_source.source_url = "https://www.tickettailor.com/events/westrivercomedyclub"
        scraper = JsonLdScraper(club)
        fetched_urls = []

        async def fake_playwright_fetch(self, url):
            fetched_urls.append(url)
            if url == "https://www.tickettailor.com/events/westrivercomedyclub":
                return _tickettailor_listing(page=1)
            if url == "https://www.tickettailor.com/events/westrivercomedyclub?page=2":
                return _tickettailor_listing(page=2)
            event_name = "First TicketTailor Show" if url.endswith("/2196315") else "Second TicketTailor Show"
            return _detail_html(event_name, url)

        monkeypatch.setattr(JsonLdScraper, "_fetch_html_with_js", fake_playwright_fetch, raising=False)

        shows = await scraper.scrape_async()

        assert fetched_urls == [
            "https://www.tickettailor.com/events/westrivercomedyclub",
            "https://www.tickettailor.com/events/westrivercomedyclub?page=2",
            "https://www.tickettailor.com/events/westrivercomedyclub/2160756",
            "https://www.tickettailor.com/events/westrivercomedyclub/2196315",
        ]
        assert sorted(show.name for show in shows) == [
            "First TicketTailor Show",
            "Second TicketTailor Show",
        ]


class TestLocationNameFilter:
    """Verify the location_name_filter metadata key narrows multi-venue calendar pages."""

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_events(self, monkeypatch):
        scraper = JsonLdScraper(_make_club())

        async def fake_fetch_html(self, url):
            return _multi_venue_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert isinstance(result, JsonLdPageData)
        names = sorted(e.name for e in result.event_list)
        assert names == ["Friday Headliner", "Saturday Showcase"]

    @pytest.mark.asyncio
    async def test_filter_keeps_only_matching_location(self, monkeypatch):
        scraper = JsonLdScraper(_make_club(metadata={
            "location_name_filter": "River: A Waterfront Restaurant and Bar",
        }))

        async def fake_fetch_html(self, url):
            return _multi_venue_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert isinstance(result, JsonLdPageData)
        assert [e.name for e in result.event_list] == ["Friday Headliner"]
        assert result.event_list[0].location.name == "River: A Waterfront Restaurant and Bar"

    @pytest.mark.asyncio
    async def test_filter_with_no_matches_returns_none(self, monkeypatch):
        scraper = JsonLdScraper(_make_club(metadata={
            "location_name_filter": "Venue That Does Not Exist On This Page",
        }))

        async def fake_fetch_html(self, url):
            return _multi_venue_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert result is None

    @pytest.mark.asyncio
    async def test_filter_excludes_events_with_empty_location_name(self, monkeypatch):
        """Events whose Place has an empty location.name (e.g. JSON-LD that omitted
        Place.name and fell back to event.name being empty too) must not match a
        non-empty filter — `"X" in ""` is False, but the `if e.location and` guard
        is the safety net if a future change makes Place.name optional/None.
        """
        nameless_event = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "",
            "startDate": "2099-07-04T20:00:00-04:00",
            "url": "https://example.com/events/nameless",
            "location": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "1 Riverside Dr",
                    "addressLocality": "Wethersfield",
                    "addressRegion": "CT",
                    "postalCode": "06109",
                    "addressCountry": "US",
                },
            },
        }
        html = f"<html><head>{_wrap_ldjson([nameless_event])}</head></html>"

        scraper = JsonLdScraper(_make_club(metadata={
            "location_name_filter": "River: A Waterfront Restaurant and Bar",
        }))

        async def fake_fetch_html(self, url):
            return html

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://comedycraftbeer.com/calendar")
        assert result is None


def _mixed_use_html() -> str:
    """A music show and a comedy show on one calendar page (Cole's Bar shape)."""
    music_event = {
        "@context": "https://schema.org",
        "@type": "MusicEvent",
        "name": "Sun Not Yellow, Disaster Kid, Dogcatcher",
        "description": "Live indie rock at Cole's Bar.",
        "startDate": "2099-06-19T20:00:00-05:00",
        "url": "https://colesbarchicago.com/shows/sun-not-yellow",
        "location": {"@type": "Place", "name": "Cole's Bar"},
    }
    comedy_event = {
        "@context": "https://schema.org",
        "@type": "MusicEvent",
        "name": "Comedy Open Mic",
        "description": "Cole's WORLD FAMOUS Comedy Open Mic established 2009!!!",
        "startDate": "2099-06-24T20:00:00-05:00",
        "url": "https://colesbarchicago.com/shows/comedy-open-mic",
        "location": {"@type": "Place", "name": "Cole's Bar"},
    }
    return f"<html><head>{_wrap_ldjson([music_event, comedy_event])}</head></html>"


class TestComedyFilter:
    """Verify the comedy_filter metadata key drops non-comedy events at mixed-use venues."""

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_events(self, monkeypatch):
        scraper = JsonLdScraper(_make_club())

        async def fake_fetch_html(self, url):
            return _mixed_use_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://colesbarchicago.com/")
        assert isinstance(result, JsonLdPageData)
        assert len(result.event_list) == 2

    @pytest.mark.asyncio
    async def test_filter_keeps_only_comedy_events(self, monkeypatch):
        scraper = JsonLdScraper(_make_club(metadata={"comedy_filter": True}))

        async def fake_fetch_html(self, url):
            return _mixed_use_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://colesbarchicago.com/")
        assert isinstance(result, JsonLdPageData)
        assert [e.name for e in result.event_list] == ["Comedy Open Mic"]

    @pytest.mark.asyncio
    async def test_filter_false_returns_all_events(self, monkeypatch):
        """comedy_filter must be a real bool read: an explicit `false` must NOT
        enable the filter (regression — metadata_value() would stringify it to
        the truthy "False")."""
        scraper = JsonLdScraper(_make_club(metadata={"comedy_filter": False}))

        async def fake_fetch_html(self, url):
            return _mixed_use_html()

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://colesbarchicago.com/")
        assert isinstance(result, JsonLdPageData)
        assert len(result.event_list) == 2

    @pytest.mark.asyncio
    async def test_filter_with_no_comedy_returns_none(self, monkeypatch):
        music_only = {
            "@context": "https://schema.org",
            "@type": "MusicEvent",
            "name": "Some Band, Another Band",
            "description": "Live music only.",
            "startDate": "2099-08-01T20:00:00-05:00",
            "url": "https://colesbarchicago.com/shows/some-band",
            "location": {"@type": "Place", "name": "Cole's Bar"},
        }
        html = f"<html><head>{_wrap_ldjson([music_only])}</head></html>"
        scraper = JsonLdScraper(_make_club(metadata={"comedy_filter": True}))

        async def fake_fetch_html(self, url):
            return html

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://colesbarchicago.com/")
        assert result is None

    @pytest.mark.asyncio
    async def test_filter_keeps_name_only_comedian_title(self, monkeypatch):
        """A name-only stand-up title (no comedy keyword) is kept via the shared
        select_comedy_titles known-comedian heuristic — the path a multi-use
        Ticketor venue like Fox Theater Salinas relies on. The DB-backed lookup
        is stubbed so the test stays unit-level."""
        music_event = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Capybara Rave",
            "description": "",
            "startDate": "2099-06-26T20:00:00-08:00",
            "url": "https://www.tickets831.com/tickets/capybara-rave",
            "location": {"@type": "Place", "name": "SALINAS FOX THEATER"},
        }
        comedy_event = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Richard Villa",
            "description": "",
            "startDate": "2099-07-24T21:00:00-08:00",
            "url": "https://www.tickets831.com/tickets/richard-villa",
            "location": {"@type": "Place", "name": "SALINAS FOX THEATER"},
        }
        html = f"<html><head>{_wrap_ldjson([music_event, comedy_event])}</head></html>"
        scraper = JsonLdScraper(_make_club(metadata={"comedy_filter": True}))

        async def fake_fetch_html(self, url):
            return html

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)
        # Stub the DB-backed selection: keyword check already drops the rave;
        # the comedian title is kept as if a stored comedian matched above floor.
        monkeypatch.setattr(
            "laughtrack.scrapers.implementations.json_ld.scraper.select_comedy_titles",
            lambda titles, **kwargs: {t for t in titles if t == "Richard Villa"},
        )

        result = await scraper.get_data("https://www.tickets831.com/")
        assert isinstance(result, JsonLdPageData)
        assert [e.name for e in result.event_list] == ["Richard Villa"]

    @pytest.mark.asyncio
    async def test_filter_allowlist_path_runs_real_heuristic(self, monkeypatch):
        """End-to-end coverage of the _filter_comedy glue (descriptions dict,
        executor offload, kept re-selection) against the REAL select_comedy_titles
        via its allowlist branch — which short-circuits before any DB call, so no
        lineup/comedian handler stubbing is needed. Exercises the same
        comedy_title_allowlist config Fox Theater Salinas uses for the Uncle Louie
        comedy duo (a local act with no comedy keyword and not in the comedians DB)."""
        music_event = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Capybara Rave",
            "description": "",
            "startDate": "2099-06-26T20:00:00-08:00",
            "url": "https://www.tickets831.com/tickets/capybara-rave",
            "location": {"@type": "Place", "name": "SALINAS FOX THEATER"},
        }
        comedy_event = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "The Uncle Louie Variety Show",
            "description": "",
            "startDate": "2099-07-25T19:30:00-08:00",
            "url": "https://www.tickets831.com/tickets/the-uncle-louie-variety-show",
            "location": {"@type": "Place", "name": "SALINAS FOX THEATER"},
        }
        html = f"<html><head>{_wrap_ldjson([music_event, comedy_event])}</head></html>"
        scraper = JsonLdScraper(
            _make_club(
                metadata={
                    "comedy_filter": True,
                    "comedy_title_allowlist": ["uncle louie", "variety show"],
                }
            )
        )

        async def fake_fetch_html(self, url):
            return html

        monkeypatch.setattr(JsonLdScraper, "fetch_html", fake_fetch_html, raising=False)

        result = await scraper.get_data("https://www.tickets831.com/")
        assert isinstance(result, JsonLdPageData)
        assert [e.name for e in result.event_list] == ["The Uncle Louie Variety Show"]
