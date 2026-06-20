"""Tests for the TicketsCandy scraper.

Covers the two-hop venue crawl (listing -> per-show sub-pages -> TicketsCandy
event links), JSON-LD parsing reuse, and the two timezone/data fixes:
the mislabeled +00:00 offset and the unreliable startDate time component
(corrected from the authoritative title clock time).
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticketscandy.scraper import (
    TicketsCandyScraper,
)

_LISTING = "https://www.funnypharmcomedy.com/shows/"
_SUBPAGE = "https://www.funnypharmcomedy.com/shows/dale-jones/"
_TC_GOOD = "https://ticketscandy.com/e/funny-pharm-dale-jones-friday-july-10th-730pm-18324"
_TC_BAD = "https://ticketscandy.com/e/funny-pharm-jaron-myers-friday-july-24th-730pm-18294"


def _make_club(metadata=None) -> Club:
    club = Club(
        id=1400,
        name="Funny Pharm Comedy Club",
        address="1100 Chicago Ave, Goshen, IN 46528",
        website="https://www.funnypharmcomedy.com",
        popularity=0,
        zip_code="46528",
        phone_number="",
        visible=True,
        timezone="America/Indiana/Indianapolis",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="ticketscandy",
        source_url=_LISTING,
        external_id=None,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _event_ldjson(name: str, start_date: str, url: str) -> str:
    event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": name,
        "url": url,
        "startDate": start_date,
        "location": {
            "@type": "Place",
            "name": "Funny Pharm Comedy Club",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "1100 Chicago Ave, Goshen, IN 46528, USA",
                "addressRegion": "Indiana",
                "postalCode": "46528",
            },
        },
        "offers": {"@type": "Offer", "price": "25.00", "priceCurrency": "USD", "url": url},
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(event)}</script></head></html>'


_PAGES = {
    _LISTING: f'<html><body><a href="/shows/dale-jones/">Dale Jones</a></body></html>',
    _SUBPAGE: f'<html><body>Tickets: <a href="{_TC_GOOD}">Fri</a> <a href="{_TC_BAD}">Sat</a></body></html>',
    # Good event: startDate time matches the title (7:30 PM == 19:30).
    _TC_GOOD: _event_ldjson(
        "Funny Pharm Comedy Club Presents: Dale Jones (Friday, July 10th - 7:30PM)",
        "2026-07-10T19:30:00+00:00",
        _TC_GOOD,
    ),
    # Bad event: startDate time is wrong (07:00) but the title says 7:30PM.
    _TC_BAD: _event_ldjson(
        "Funny Pharm Comedy Club Presents: Jaron Myers (Friday, July 24th - 7:30PM)",
        "2026-07-24T07:00:00+00:00",
        _TC_BAD,
    ),
}


def _install_fetch(monkeypatch, pages=None):
    pages = pages if pages is not None else _PAGES

    async def fake_fetch_html(self, url):
        # URLUtils.normalize_url may strip a trailing slash; match either form
        # the way a real server would.
        return pages.get(url) or pages.get(url + "/") or pages.get(url.rstrip("/"))

    monkeypatch.setattr(TicketsCandyScraper, "fetch_html", fake_fetch_html, raising=False)


class TestTicketsCandyScraper:
    @pytest.mark.asyncio
    async def test_two_hop_discovery_yields_both_events(self, monkeypatch):
        _install_fetch(monkeypatch)
        shows = await TicketsCandyScraper(
            _make_club(metadata={"detail_link_prefix": "/shows/"})
        ).scrape_async()
        assert len(shows) == 2
        assert {s.date.date().isoformat() for s in shows} == {"2026-07-10", "2026-07-24"}

    @pytest.mark.asyncio
    async def test_offset_relabeled_to_club_timezone(self, monkeypatch):
        """The mislabeled +00:00 wall-clock is localized to the club tz (EDT),
        not treated as UTC."""
        _install_fetch(monkeypatch)
        shows = await TicketsCandyScraper(
            _make_club(metadata={"detail_link_prefix": "/shows/"})
        ).scrape_async()
        good = next(s for s in shows if s.date.date().isoformat() == "2026-07-10")
        assert good.date.hour == 19 and good.date.minute == 30
        assert good.date.utcoffset().total_seconds() == -4 * 3600  # EDT, not UTC

    @pytest.mark.asyncio
    async def test_title_time_overrides_bad_startdate(self, monkeypatch):
        """When the JSON-LD startDate time (07:00) disagrees with the title
        (7:30PM), the title wins."""
        _install_fetch(monkeypatch)
        shows = await TicketsCandyScraper(
            _make_club(metadata={"detail_link_prefix": "/shows/"})
        ).scrape_async()
        bad = next(s for s in shows if s.date.date().isoformat() == "2026-07-24")
        assert bad.date.hour == 19 and bad.date.minute == 30

    @pytest.mark.asyncio
    async def test_show_page_url_points_to_venue_subpage(self, monkeypatch):
        """show_page_url should be the venue's own page (sameAs), not the
        TicketsCandy ticket link."""
        _install_fetch(monkeypatch)
        shows = await TicketsCandyScraper(
            _make_club(metadata={"detail_link_prefix": "/shows/"})
        ).scrape_async()
        # show_page_url -> the venue's own page (trailing slash normalized away);
        # the ticket purchase URL stays the TicketsCandy link.
        assert all(s.show_page_url.rstrip("/") == _SUBPAGE.rstrip("/") for s in shows)
        assert all("ticketscandy.com" in s.tickets[0].purchase_url for s in shows)

    @pytest.mark.asyncio
    async def test_no_ticketscandy_links_returns_empty(self, monkeypatch):
        _install_fetch(monkeypatch, pages={_LISTING: "<html><body>no links</body></html>"})
        shows = await TicketsCandyScraper(
            _make_club(metadata={"detail_link_prefix": "/shows/"})
        ).scrape_async()
        assert shows == []
