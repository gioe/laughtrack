from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.new_york_comedy_club.data import (
    NewYorkComedyClubPageData,
)
from laughtrack.scrapers.implementations.venues.new_york_comedy_club.scraper import (
    NewYorkComedyClubScraper,
)


CALENDAR_URL = "https://newyorkcomedyclub.com/calendar"


def _club() -> Club:
    club = Club(
        id=4,
        name="New York Comedy Club Upper West Side",
        address="236 W 78th St, New York, NY 10024",
        website="https://newyorkcomedyclub.com",
        popularity=0,
        zip_code="10024",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="new_york_comedy_club",
        source_url=CALENDAR_URL,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


_RENDERED_CURRENT_CARD_HTML = """
<html>
  <head>
    <title>Comedy shows for April 2026 - New York Comedy Club, New York, NY</title>
  </head>
  <body>
    <div class="row upcoming-container-list">
      <div class="col-sm-2 col-lg-1 upcoming-list-inner hidden-xs">
        <a aria-label="View Usama Siddiquee, Pat McGann, Erin Maguire, Fumi Abe"
           href="/events/usama-siddiquee-pat-mcgann-erin-maguire-fumi-abe">
          <ul class="list-unstyled text-center event-date-ul">
            <li>Thursday</li>
            <li>Apr 30th</li>
            <li>07:30PM</li>
          </ul>
        </a>
      </div>
      <div class="col-xs-12 col-sm-6 col-lg-7 upcoming-list-description calendar-upcoming-list-description">
        <ul class="list-unstyled calendar-event-details">
          <li class="scheduled-venue visible-xs upper-west-side customs">Upper West Side</li>
          <li class="scheduled-name">
            <a href="/events/usama-siddiquee-pat-mcgann-erin-maguire-fumi-abe">
              Usama Siddiquee, Pat McGann, Erin Maguire, Fumi Abe at
            </a>
            <span class="scheduled-venue hidden-xs upper-west-side customs">Upper West Side</span>
          </li>
          <li class="scheduled-description">A fast-paced showcase of top-tier comics.</li>
        </ul>
      </div>
      <div class="col-xs-12 col-sm-2 col-lg-2 upcoming-list-inner">
        <a href="/events/usama-siddiquee-pat-mcgann-erin-maguire-fumi-abe">BUY TICKETS</a>
      </div>
    </div>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_get_data_reads_current_rendered_calendar_cards(monkeypatch):
    scraper = NewYorkComedyClubScraper(_club())
    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=_RENDERED_CURRENT_CARD_HTML),
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, NewYorkComedyClubPageData)
    assert len(result.event_list) == 1

    event = result.event_list[0]
    assert event.name == "Usama Siddiquee, Pat McGann, Erin Maguire, Fumi Abe"
    assert event.start_date.isoformat() == "2026-04-30T19:30:00-04:00"
    assert event.location.address.street_address == "236 W 78th Street"
    assert [performer.name for performer in event.performers] == [
        "Usama Siddiquee",
        "Pat McGann",
        "Erin Maguire",
        "Fumi Abe",
    ]

    show = event.to_show(_club())
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == (
        "https://newyorkcomedyclub.com/events/"
        "usama-siddiquee-pat-mcgann-erin-maguire-fumi-abe"
    )
    assert show.tickets[0].price == 0.0
