from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
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


_CALENDAR_HTML_WITH_RENDERED_CARD_AND_JSON_LD = """
<html>
  <head>
    <title>Comedy shows for May 2026 - New York Comedy Club, New York, NY</title>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "ComedyEvent",
        "name": "Next Gen Comics Mother's Day Show (ft. Kalliope Barlis)",
        "startDate": "2026-05-10T17:30:00-04:00",
        "url": "https://www.newyorkcomedyclub.com/events/next-gen-comics-mothers-day-show-1402292",
        "sameAs": "https://www.newyorkcomedyclub.com/events/next-gen-comics-mothers-day-show-1402292",
        "location": {
          "@type": "Place",
          "name": "New York Comedy Club Upper West Side",
          "address": {
            "@type": "PostalAddress",
            "streetAddress": "236 W 78th Street",
            "addressLocality": "New York",
            "addressRegion": "NY",
            "postalCode": "10024",
            "addressCountry": "US"
          }
        },
        "performer": [
          {"@type": "Person", "name": "Kalliope Barlis"}
        ],
        "offers": {
          "@type": "Offer",
          "url": "https://www.newyorkcomedyclub.com/events/next-gen-comics-mothers-day-show-1402292",
          "priceCurrency": "USD",
          "price": "15.00",
          "availability": "https://schema.org/InStock"
        }
      }
    </script>
  </head>
  <body>
    <div class="row upcoming-container-list">
      <div class="col-sm-2 col-lg-1 upcoming-list-inner hidden-xs">
        <a href="/events/next-gen-comics-mothers-day-show-1402292">
          <ul class="list-unstyled text-center event-date-ul">
            <li>Sunday</li>
            <li>May 10th</li>
            <li>05:30PM</li>
          </ul>
        </a>
      </div>
      <div class="col-xs-12 col-sm-6 col-lg-7 upcoming-list-description calendar-upcoming-list-description">
        <ul class="list-unstyled calendar-event-details">
          <li class="scheduled-venue visible-xs upper-west-side customs">Upper West Side</li>
          <li class="scheduled-name">
            <a href="/events/next-gen-comics-mothers-day-show-1402292">
              Next Gen Comics Mother's Day Show (ft. Kalliope Barlis) at
            </a>
            <span class="scheduled-venue hidden-xs upper-west-side customs">Upper West Side</span>
          </li>
          <li class="scheduled-description">A Mother's Day showcase.</li>
        </ul>
      </div>
    </div>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_get_data_enriches_rendered_card_from_matching_json_ld(monkeypatch):
    scraper = NewYorkComedyClubScraper(_club())
    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=_CALENDAR_HTML_WITH_RENDERED_CARD_AND_JSON_LD),
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert result is not None
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.name == "Next Gen Comics Mother's Day Show (ft. Kalliope Barlis)"
    assert [performer.name for performer in event.performers] == ["Kalliope Barlis"]
    assert event.offers[0].price == "15.00"
