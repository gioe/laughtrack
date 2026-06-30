"""
Smoke tests for the Denver Comedy Lounge scraper (RiNo, Denver, CO).

The venue runs a custom Next.js site that sells shows via on-site Stripe
checkout; the venue-owned /shows page server-renders a schema.org ItemList whose
items each carry a title plus a detail URL whose slug encodes the date and start
time (e.g. /shows/friday-7pm-2099-06-26).

Verifies:
- the extractor parses ItemList items into shows, deriving date/time from the slug
- get_data() returns page data with shows / None on empty extraction
- the transformation pipeline produces Shows with tz-aware dates + one ticket each

Fixture dates use 2099 so date-aware filtering never turns these into past shows.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.denver_comedy_lounge.data import (
    DenverComedyLoungePageData,
)
from laughtrack.scrapers.implementations.venues.denver_comedy_lounge.extractor import (
    DenverComedyLoungeExtractor,
)
from laughtrack.scrapers.implementations.venues.denver_comedy_lounge.scraper import (
    DenverComedyLoungeScraper,
)

SHOWS_URL = "https://denvercomedylounge.com/shows"

# Minimal recording of the /shows ItemList JSON-LD (two of the page's items).
FIXTURE_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"EntertainmentBusiness","name":"Denver Comedy Lounge"}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"ItemList","name":"Upcoming Shows at Denver Comedy Lounge","numberOfItems":2,"itemListElement":[
  {"@type":"ListItem","position":1,"item":{"@type":"WebPage","name":"Friday Night Comedy — Jun 26","url":"https://denvercomedylounge.com/shows/friday-7pm-2099-06-26"}},
  {"@type":"ListItem","position":2,"item":{"@type":"WebPage","name":"Saturday Late Night — September 19","url":"https://denvercomedylounge.com/shows/saturday-10pm-2099-09-19"}}
]}
</script>
</head><body></body></html>
"""


def _club() -> Club:
    club = Club(
        id=999,
        name="Denver Comedy Lounge",
        address="3559 Larimer St",
        website="https://denvercomedylounge.com",
        popularity=0,
        zip_code="80205",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="denver_comedy_lounge",
        source_url=SHOWS_URL,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_extractor_parses_itemlist_into_shows():
    """Extractor derives title + date/time from each ItemList slug."""
    shows = DenverComedyLoungeExtractor.extract_shows(FIXTURE_HTML)

    assert len(shows) == 2, "Expected 2 shows from the ItemList fixture"

    by_url = {s.show_page_url: s for s in shows}
    friday = by_url["https://denvercomedylounge.com/shows/friday-7pm-2099-06-26"]
    assert friday.title == "Friday Night Comedy"  # date suffix stripped
    assert friday.datetime_str == "2099-06-26 19:00:00"  # 7pm -> 19:00

    saturday = by_url["https://denvercomedylounge.com/shows/saturday-10pm-2099-09-19"]
    assert saturday.title == "Saturday Late Night"
    assert saturday.datetime_str == "2099-09-19 22:00:00"  # 10pm -> 22:00


def test_extractor_returns_empty_without_itemlist():
    """No ItemList -> empty list (scraper surfaces an empty extraction)."""
    assert DenverComedyLoungeExtractor.extract_shows("<html></html>") == []


@pytest.mark.asyncio
async def test_collect_scraping_targets_uses_source_url():
    """collect_scraping_targets() returns the configured /shows source_url."""
    scraper = DenverComedyLoungeScraper(_club())
    assert await scraper.collect_scraping_targets() == [SHOWS_URL]


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_shows(monkeypatch):
    """get_data() returns DenverComedyLoungePageData with the extracted shows."""
    scraper = DenverComedyLoungeScraper(_club())

    async def _fake_fetch_html(url):
        return FIXTURE_HTML

    monkeypatch.setattr(scraper, "fetch_html", _fake_fetch_html)

    result = await scraper.get_data(SHOWS_URL)

    assert isinstance(result, DenverComedyLoungePageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page can't be fetched."""
    scraper = DenverComedyLoungeScraper(_club())

    async def _empty_fetch_html(url):
        return ""

    monkeypatch.setattr(scraper, "fetch_html", _empty_fetch_html)

    assert await scraper.get_data(SHOWS_URL) is None


def test_transformation_pipeline_produces_shows_with_tickets():
    """The pipeline yields tz-aware Shows, each with one fallback ticket."""
    scraper = DenverComedyLoungeScraper(_club())
    page_data = DenverComedyLoungePageData(
        event_list=DenverComedyLoungeExtractor.extract_shows(FIXTURE_HTML)
    )

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 2
    assert all(isinstance(s, Show) for s in shows)
    for show in shows:
        assert show.date is not None and show.date.tzinfo is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].purchase_url.startswith(
            "https://denvercomedylounge.com/shows/"
        )


def test_transformation_pipeline_extracts_lineup_from_comedy_special_title():
    """A detail title with an explicit Comedy Special signal creates a lineup item."""
    scraper = DenverComedyLoungeScraper(_club())
    page_data = DenverComedyLoungePageData(
        event_list=[
            DenverComedyLoungeExtractor._build_show(
                {
                    "item": {
                        "name": "Garage Sale - Korey David Comedy Special — Jul 31",
                        "url": "https://denvercomedylounge.com/shows/thursday-8pm-2099-07-31",
                    }
                }
            )
        ]
    )

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert [comedian.name for comedian in shows[0].lineup] == ["Korey David"]


# A per-show detail page: Event JSON-LD with an offers array (lowest is GA $21).
_DETAIL_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event","name":"Friday Night Comedy",
 "offers":[
   {"@type":"Offer","name":"General Admission","price":21,"priceCurrency":"USD"},
   {"@type":"Offer","name":"Front Row","price":31,"priceCurrency":"USD"}
 ]}
</script>
</head><body></body></html>
"""


def test_extract_offer_price_returns_lowest_positive_offer():
    """The lowest positive Offer price is the representative ticket price."""
    assert DenverComedyLoungeExtractor.extract_offer_price(_DETAIL_HTML) == 21.0


def test_extract_offer_price_none_without_offers():
    """A detail page without offers (e.g. the ItemList page) yields None."""
    assert DenverComedyLoungeExtractor.extract_offer_price(FIXTURE_HTML) is None
    assert DenverComedyLoungeExtractor.extract_offer_price("") is None


def test_extract_offer_price_zero_only_offers_is_free():
    """Offers that all parse to 0 mean an explicitly free show (0.0, not None)."""
    free_html = """
    <html><head><script type="application/ld+json">
    {"@type":"Event","offers":[{"@type":"Offer","price":0,"priceCurrency":"USD"}]}
    </script></head><body></body></html>
    """
    assert DenverComedyLoungeExtractor.extract_offer_price(free_html) == 0.0


@pytest.mark.asyncio
async def test_get_data_hydrates_price_from_detail_pages(monkeypatch):
    """get_data() fetches each detail page and attaches its Offer price."""
    scraper = DenverComedyLoungeScraper(_club())

    async def _dispatch_fetch_html(url):
        # Listing URL → ItemList page; per-show detail URLs → Event w/ offers.
        return FIXTURE_HTML if url == SHOWS_URL else _DETAIL_HTML

    monkeypatch.setattr(scraper, "fetch_html", _dispatch_fetch_html)

    result = await scraper.get_data(SHOWS_URL)

    assert result is not None
    assert len(result.event_list) == 2
    assert all(show.price == 21.0 for show in result.event_list)

    # Price flows through to the ticket.
    shows = scraper.transformation_pipeline.transform(result)
    assert all(show.tickets[0].price == 21.0 for show in shows)


@pytest.mark.asyncio
async def test_get_data_leaves_price_none_when_detail_fetch_fails(monkeypatch):
    """A failing detail fetch leaves price None without dropping the show."""
    scraper = DenverComedyLoungeScraper(_club())

    async def _failing_detail_fetch(url):
        if url == SHOWS_URL:
            return FIXTURE_HTML
        raise RuntimeError("boom")

    monkeypatch.setattr(scraper, "fetch_html", _failing_detail_fetch)

    result = await scraper.get_data(SHOWS_URL)

    assert result is not None
    assert len(result.event_list) == 2
    assert all(show.price is None for show in result.event_list)
