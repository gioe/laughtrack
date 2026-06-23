"""Tests for the opt-in title filter on TicketTailorScraper (TASK-3216).

Mixed-use Ticket Tailor venues (event halls hosting raves / DJ nights / private
parties alongside an intermittent comedy series — e.g. Continental Club Oakland)
expose every event on the same box office. The filter keeps only the comedy
shows when configured via scraping_sources.metadata:
  - include_title_patterns: keep only titles matching the comedy allowlist
  - exclude_title_patterns: drop titles matching the blocklist
Both are off by default, so existing Ticket Tailor sources are unchanged.
"""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.ticket_tailor.scraper import TicketTailorScraper


# A mixed-use box office: 1 comedy series + 4 music/party events. Each card is
# an li.events-listing__item with a single parseable date so extract_events
# yields all five before the title filter runs.
def _card(title: str, event_id: str) -> str:
    return f"""
    <li class="events-listing__item">
      <div class="event__content">
        <h3 class="event__title">
          <a href="/events/continentalclub/{event_id}" class="event__link">{title}</a>
        </h3>
        <span class="event-meta__date">Fri Jul 10, 2099 8:00 PM - 11:00 PM PDT</span>
        <span class="event-meta__location">Continental Club, 94607</span>
      </div>
    </li>
    """


_MIXED_HTML = "<html><body><ul class='events-listing__events'>" + "".join(
    [
        _card("Comedy Oakland Stand-Up Showcase", "1001"),
        _card("BABY RAVE", "1002"),
        _card("Soft 'n Spicy Rooftop Party", "1003"),
        _card("AFROBEATS UNIVERSITY: ORIENTATION WEEK", "1004"),
        _card("STUNNA GIRL & FRIENDS CONCERT", "1005"),
    ]
) + "</ul></body></html>"


def _club(metadata: dict) -> Club:
    c = Club(
        id=999,
        name="Continental Club",
        address="1658 12th St",
        website="https://oaklandcontinentalclub.com/",
        popularity=0,
        zip_code="94607",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )
    base = {"account_slug": "continentalclub", "single_venue": True}
    base.update(metadata)
    c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=c.id,
        platform="custom",
        scraper_key="ticket_tailor",
        source_url="https://www.tickettailor.com/events/continentalclub/",
        metadata=base,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


async def _scrape(club: Club):
    scraper = TicketTailorScraper(club)

    async def fake_fetch(url):
        return _MIXED_HTML

    scraper._fetch_listing = fake_fetch  # type: ignore[method-assign]
    return await scraper.scrape_async()


@pytest.mark.asyncio
async def test_no_filter_keeps_all_events():
    """Default (no filter metadata): every event flows through unchanged."""
    shows = await _scrape(_club({}))
    titles = {s.name for s in shows}
    assert len(shows) == 5
    assert "BABY RAVE" in titles
    assert "Comedy Oakland Stand-Up Showcase" in titles


@pytest.mark.asyncio
async def test_include_only_comedy():
    """Comedy allowlist keeps only the stand-up show on a mixed-use calendar."""
    shows = await _scrape(
        _club({"include_title_patterns": ["comedy", "stand[- ]?up", "showcase"]})
    )
    assert [s.name for s in shows] == ["Comedy Oakland Stand-Up Showcase"]


@pytest.mark.asyncio
async def test_exclude_drops_matches():
    """Blocklist drops the named music/party events, keeps the rest."""
    shows = await _scrape(
        _club({"exclude_title_patterns": ["rave", "rooftop party", "afrobeats", "concert"]})
    )
    assert [s.name for s in shows] == ["Comedy Oakland Stand-Up Showcase"]


@pytest.mark.asyncio
async def test_include_and_exclude_compose():
    """Include first, then exclude: an event must pass both gates."""
    shows = await _scrape(
        _club(
            {
                "include_title_patterns": ["comedy", "rave"],
                "exclude_title_patterns": ["rave"],
            }
        )
    )
    assert [s.name for s in shows] == ["Comedy Oakland Stand-Up Showcase"]
