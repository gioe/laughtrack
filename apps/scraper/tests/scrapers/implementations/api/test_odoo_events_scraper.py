import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.odoo_events.scraper import OdooEventsScraper

_FIXTURES = Path(__file__).parents[3] / "fixtures" / "html"


def _make_club() -> Club:
    club = Club(
        id=3021,
        name="Comedy Plex Comedy Club",
        address="1128 Lake St Lower Level",
        website="https://www.comedyplex.com/",
        popularity=0,
        zip_code="60301",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="odoo_events",
        source_url="https://www.comedyplex.com/event",
        external_id=None,
        metadata={"exclude_title_patterns": [r"\bclass(?:es)?\b", r"\bjazz\b"]},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _listing(page: int) -> str:
    if page == 1:
        return (_FIXTURES / "odoo_comedyplex_event_listing.html").read_text()
    next_link = ""
    links = {
        2: [("saturday-showcase-43", "Saturday Showcase"), ("adult-improv-classes-44", "Adult Improv Classes: Level 2")],
        3: [("stale-show-45", "Stale Show"), ("jazz-night-46", "WDCB Jazz @ The Plex")],
    }[page]
    cards = "\n".join(
        f"""
        <div itemscope itemtype="http://schema.org/Event">
          <a href="/event/{event_id}/register"><span itemprop="name">{name}</span></a>
        </div>
        """
        for event_id, name in links
    )
    return f"""
    <html><body>
      {cards}
      {next_link}
    </body></html>
    """


def _detail(name: str, start: str, price: str) -> str:
    return f"""
    <html><body>
      <main itemscope itemtype="http://schema.org/Event">
        <meta itemprop="startDate" content="{start}">
        <meta itemprop="endDate" content="2026-06-27T03:00:00">
        <h1 itemprop="name">{name}</h1>
        <div itemprop="description">{name} at Comedy Plex.</div>
        <div itemprop="location" itemscope itemtype="http://schema.org/Place">
          <span itemprop="name">Comedy Plex Comedy Club</span>
          <div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">
            <span itemprop="streetAddress">1128 Lake St Lower Level</span>
            <span itemprop="addressLocality">Oak Park</span>
            <span itemprop="addressRegion">IL</span>
            <span itemprop="postalCode">60301</span>
            <span itemprop="addressCountry">US</span>
          </div>
        </div>
        <div itemprop="offers" itemscope itemtype="http://schema.org/Offer">
          <meta itemprop="price" content="{price}">
          <meta itemprop="priceCurrency" content="USD">
          <link itemprop="availability" href="https://schema.org/InStock">
        </div>
      </main>
    </body></html>
    """


@pytest.mark.asyncio
async def test_odoo_events_scraper_paginates_listing_and_scrapes_microdata_details(monkeypatch):
    scraper = OdooEventsScraper(_make_club())
    fetched_urls = []

    async def fake_fetch_html(self, url):
        fetched_urls.append(url)
        if url == "https://www.comedyplex.com/event":
            return _listing(page=1)
        if url == "https://www.comedyplex.com/event/page/2?date=upcoming":
            return _listing(page=2)
        if url == "https://www.comedyplex.com/event/page/3?date=upcoming":
            return _listing(page=3)
        if url.endswith("/late-night-comedy-42/register"):
            return _detail("Late Night Comedy", "2099-06-27T01:00:00", "25.00")
        if url.endswith("/saturday-showcase-43/register"):
            return _detail("Saturday Showcase", "2099-06-28T02:00:00", "30.00")
        if url.endswith("/adult-improv-classes-44/register"):
            return _detail("Adult Improv Classes: Level 2", "2099-06-29T00:00:00", "199.00")
        if url.endswith("/stale-show-45/register"):
            return _detail("Stale Show", "2000-06-29T00:00:00", "20.00")
        if url.endswith("/jazz-night-46/register"):
            return _detail("WDCB Jazz @ The Plex", "2099-06-29T01:00:00", "20.00")
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(OdooEventsScraper, "fetch_html", fake_fetch_html, raising=False)

    shows = await scraper.scrape_async()

    assert fetched_urls == [
        "https://www.comedyplex.com/event",
        "https://www.comedyplex.com/event/page/2?date=upcoming",
        "https://www.comedyplex.com/event/page/3?date=upcoming",
        "https://www.comedyplex.com/event/adult-improv-classes-44/register",
        "https://www.comedyplex.com/event/jazz-night-46/register",
        "https://www.comedyplex.com/event/late-night-comedy-42/register",
        "https://www.comedyplex.com/event/saturday-showcase-43/register",
        "https://www.comedyplex.com/event/stale-show-45/register",
    ]
    assert [show.name for show in shows] == ["Late Night Comedy", "Saturday Showcase"]
    assert shows[0].date.isoformat() == "2099-06-26T20:00:00-05:00"
    assert shows[0].show_page_url == "https://www.comedyplex.com/event/late-night-comedy-42/register"
    assert shows[0].tickets[0].purchase_url == "https://www.comedyplex.com/event/late-night-comedy-42/register"
    assert shows[0].tickets[0].price == 25.0
