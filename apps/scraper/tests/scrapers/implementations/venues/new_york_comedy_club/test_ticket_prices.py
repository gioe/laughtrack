from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.new_york_comedy_club.scraper import (
    NewYorkComedyClubScraper,
    _cheapest_normal_offer_from_event_page,
)


CALENDAR_URL = "https://newyorkcomedyclub.com/calendar"
EVENT_URL = "https://newyorkcomedyclub.com/events/jay-jurden-mike-cannon-kaneez-surka-shane-torres-luca-ferro"


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


_EVENT_PAGE_WITH_TICKET_TIERS = f"""
<html>
  <body>
    <div class="ticket-info-row">
      <div class="ticket-name-price">
        GENERAL ADMISSION
        <span class="ticket-price-wrapper">
          <span class="ticket-price original" data-ticket="146816">$30.85</span>
        </span>
      </div>
      <div class="fee-container ticket-fee-breakdown" data-ticket="146816">
        <span class="breakdown-base-original">$25.00</span> +
        <span class="breakdown-fee-original">$5.85</span> fee
      </div>
    </div>
    <div class="ticket-info-row">
      <div class="ticket-name-price">
        PREMIUM SEATING
        <span class="ticket-price-wrapper">
          <span class="ticket-price original" data-ticket="146817">$41.72</span>
        </span>
      </div>
      <div class="fee-container ticket-fee-breakdown" data-ticket="146817">
        <span class="breakdown-base-original">$35.00</span> +
        <span class="breakdown-fee-original">$6.72</span> fee
      </div>
    </div>
    <div class="ticket-info-row">
      <div class="ticket-name-price">
        MONDAY SPECIAL OFFERS
        <span class="ticket-price-wrapper">
          <span class="ticket-price original" data-ticket="146820">$0.00</span>
        </span>
      </div>
    </div>
  </body>
</html>
"""


_CALENDAR_WITH_UNPRICED_RENDERED_CARD_AND_JSON_LD = f"""
<html>
  <head>
    <title>Comedy shows for May 2026 - New York Comedy Club, New York, NY</title>
    <script type="application/ld+json">
      {{
        "@context": "https://schema.org",
        "@type": "ComedyEvent",
        "name": "Jay Jurden, Mike Cannon, Kaneez Surka, Shane Torres, Luca Ferro",
        "startDate": "2026-05-18T22:00:00-04:00",
        "url": "{EVENT_URL}",
        "sameAs": "{EVENT_URL}",
        "location": {{
          "@type": "Place",
          "name": "New York Comedy Club Upper West Side",
          "address": {{
            "@type": "PostalAddress",
            "streetAddress": "236 W 78th Street",
            "addressLocality": "New York",
            "addressRegion": "NY",
            "postalCode": "10024",
            "addressCountry": "US"
          }}
        }},
        "performer": [
          {{"@type": "Person", "name": "Jay Jurden"}},
          {{"@type": "Person", "name": "Mike Cannon"}}
        ],
        "offers": {{
          "@type": "Offer",
          "url": "{EVENT_URL}",
          "priceCurrency": "USD",
          "price": "",
          "availability": "https://schema.org/InStock"
        }}
      }}
    </script>
  </head>
  <body>
    <div class="row upcoming-container-list">
      <div class="col-sm-2 col-lg-1 upcoming-list-inner hidden-xs">
        <a href="/events/jay-jurden-mike-cannon-kaneez-surka-shane-torres-luca-ferro">
          <ul class="list-unstyled text-center event-date-ul">
            <li>Monday</li>
            <li>May 18th</li>
            <li>10:00PM</li>
          </ul>
        </a>
      </div>
      <div class="col-xs-12 col-sm-6 col-lg-7 upcoming-list-description calendar-upcoming-list-description">
        <ul class="list-unstyled calendar-event-details">
          <li class="scheduled-venue visible-xs upper-west-side customs">Upper West Side</li>
          <li class="scheduled-name">
            <a href="/events/jay-jurden-mike-cannon-kaneez-surka-shane-torres-luca-ferro">
              Jay Jurden, Mike Cannon, Kaneez Surka, Shane Torres, Luca Ferro at
            </a>
            <span class="scheduled-venue hidden-xs upper-west-side customs">Upper West Side</span>
          </li>
          <li class="scheduled-description">A fast-paced showcase of top-tier comics.</li>
        </ul>
      </div>
    </div>
  </body>
</html>
"""


def test_event_page_ticket_tiers_ignore_special_offer_free_tier():
    offer = _cheapest_normal_offer_from_event_page(_EVENT_PAGE_WITH_TICKET_TIERS, EVENT_URL)

    assert offer is not None
    assert offer.name == "General Admission"
    assert offer.price == "25.00"
    assert offer.url == EVENT_URL


@pytest.mark.asyncio
async def test_calendar_event_uses_event_page_price_when_json_ld_price_missing(monkeypatch):
    scraper = NewYorkComedyClubScraper(_club())

    async def fake_fetch_html(url: str) -> str:
        if url == CALENDAR_URL:
            return _CALENDAR_WITH_UNPRICED_RENDERED_CARD_AND_JSON_LD
        if url == EVENT_URL:
            return _EVENT_PAGE_WITH_TICKET_TIERS
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(side_effect=fake_fetch_html))

    result = await scraper.get_data(CALENDAR_URL)

    assert result is not None
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.offers[0].price == "25.00"
    assert event.offers[0].name == "General Admission"
    show = event.to_show(_club())
    assert show.tickets[0].price == 25.0
