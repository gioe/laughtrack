"""Tests for Go Bananas Comedy Club's custom WordPress show markup scraper."""

from datetime import date

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.go_bananas import GoBananasEvent
from laughtrack.scrapers.implementations.venues.go_bananas.data import (
    GoBananasPageData,
)
from laughtrack.scrapers.implementations.venues.go_bananas.extractor import (
    GoBananasExtractor,
)
from laughtrack.scrapers.implementations.venues.go_bananas.scraper import (
    GoBananasScraper,
)


_SOURCE_URL = "https://gobananascomedy.com"
_SAMPLE_HTML = """
<html>
  <body>
    <article class="post type-post status-publish category-shows entry">
      <div class="entry-content goba_show">
        <header class="goba-show-header">
          <div class="goba-title-card">
            <a href="https://gobananascomedy.com/main/show/tabari-mccoy-3/">
              <img class="goba-title-card__img" src="https://gobananascomedy.com/tabari.png">
            </a>
            <div class="goba-title-card__title"><table><tbody><tr><td>Tabari McCoy</td></tr></tbody></table></div>
            <div class="goba-title-card__dates"><table><tbody><tr><td>April 30 - May 2</td></tr></tbody></table></div>
          </div>
        </header>
        <div id="showtimes_div">
          <table class="goba-showtimes">
            <tbody>
              <tr class="goba-showtimes__row">
                <td class="goba-showtimes__showtime" colspan="3">Thu (April 30) <b>7:30 pm</b></td>
                <td class="goba-showtimes__age_restriction">18+</td>
              </tr>
              <tr class="goba-showtimes__row">
                <td class="goba-showtimes__showtime">Sat (May 2) <b>7:30 pm</b></td>
                <td class="goba-showtimes__price">$15.00</td>
                <td class="goba-showtimes__reservation">
                  <button class="goba-reservation-button" onclick="location.href='make-reservations?show_id=4097&amp;showtime_id=4';">Tickets</button>
                </td>
                <td class="goba-showtimes__age_restriction">21+</td>
              </tr>
              <tr class="goba-showtimes__row">
                <td class="goba-showtimes__showtime">Sat (May 2) <b>9:45 pm</b></td>
                <td class="goba-showtimes__price">$15.00</td>
                <td class="goba-showtimes__reservation">
                  <button class="goba-reservation-button" onclick="location.href='make-reservations?show_id=4097&amp;showtime_id=5';">Tickets</button>
                </td>
                <td class="goba-showtimes__age_restriction">21+</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </article>

    <article class="post type-post status-publish category-shows entry">
      <div class="entry-content goba_show">
        <header class="goba-show-header">
          <div class="goba-title-card">
            <a href="https://gobananascomedy.com/main/show/clean-up-your-act/"></a>
            <div class="goba-title-card__title"><table><tbody><tr><td>Clean Up Your Act</td></tr></tbody></table></div>
            <div class="goba-title-card__dates"><table><tbody><tr><td>May 3</td></tr></tbody></table></div>
          </div>
        </header>
        <div id="showtimes_div">
          <table class="goba-showtimes">
            <tbody>
              <tr class="goba-showtimes__row">
                <td class="goba-showtimes__showtime">Sun (May 3) <b>7:00 pm</b></td>
                <td class="goba-showtimes__price">$15.00</td>
                <td class="goba-showtimes__reservation">
                  <button class="goba-reservation-button" onclick="location.href='make-reservations?show_id=4286&amp;showtime_id=1';">Tickets</button>
                </td>
                <td class="goba-showtimes__age_restriction">18+</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </article>
  </body>
</html>
"""


def _club() -> Club:
    club = Club(
        id=574,
        name="Go Bananas Comedy Club",
        address="8410 Market Place Ln",
        website=_SOURCE_URL,
        popularity=0,
        zip_code="45242",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=570,
        club_id=club.id,
        platform="custom",
        scraper_key="go_bananas",
        source_url=_SOURCE_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_collect_scraping_targets_returns_site_root():
    scraper = GoBananasScraper(_club())

    assert scraper.collect_scraping_targets_sync() == [_SOURCE_URL]


def test_extractor_expands_ticketed_showtime_rows_and_skips_unticketed_rows():
    events = GoBananasExtractor.extract_events(
        _SAMPLE_HTML,
        source_url=_SOURCE_URL,
        today=date(2026, 5, 1),
    )

    assert [(event.title, event.date, event.time, event.price) for event in events] == [
        ("Tabari McCoy", "2026-05-02", "7:30 PM", 15.0),
        ("Tabari McCoy", "2026-05-02", "9:45 PM", 15.0),
        ("Clean Up Your Act", "2026-05-03", "7:00 PM", 15.0),
    ]
    assert events[0].ticket_url == "https://gobananascomedy.com/main/make-reservations?show_id=4097&showtime_id=4"


def test_extractor_rolls_earlier_months_to_next_year_when_needed():
    events = GoBananasExtractor.extract_events(
        _SAMPLE_HTML,
        source_url=_SOURCE_URL,
        today=date(2026, 12, 15),
    )

    assert events[0].date == "2027-05-02"


def test_extractor_returns_empty_when_show_articles_are_missing():
    events = GoBananasExtractor.extract_events(
        "<html><body><p>No shows here.</p></body></html>",
        source_url=_SOURCE_URL,
        today=date(2026, 5, 1),
    )

    assert events == []


@pytest.mark.asyncio
async def test_get_data_fetches_source_page_and_returns_page_data(monkeypatch):
    scraper = GoBananasScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        assert url == _SOURCE_URL
        return _SAMPLE_HTML

    monkeypatch.setattr(GoBananasScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(GoBananasScraper, "_today", staticmethod(lambda: date(2026, 5, 1)))

    result = await scraper.get_data(_SOURCE_URL)

    assert isinstance(result, GoBananasPageData)
    assert len(result.event_list) == 3


def test_to_show_sets_name_date_url_ticket_and_price():
    event = GoBananasEvent(
        title="Tabari McCoy",
        date="2026-05-02",
        time="7:30 PM",
        source_url="https://gobananascomedy.com/main/show/tabari-mccoy-3/",
        ticket_url="https://gobananascomedy.com/main/make-reservations?show_id=4097&showtime_id=4",
        price=15.0,
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Tabari McCoy"
    assert show.date.year == 2026
    assert show.date.month == 5
    assert show.date.day == 2
    assert show.date.hour == 19
    assert show.date.minute == 30
    assert show.show_page_url == "https://gobananascomedy.com/main/show/tabari-mccoy-3"
    assert show.tickets[0].purchase_url == "https://gobananascomedy.com/main/make-reservations?show_id=4097&showtime_id=4"
    assert show.tickets[0].price == 15.0


def test_to_show_returns_none_for_invalid_date():
    event = GoBananasEvent(
        title="Bad Event",
        date="not-a-date",
        time="7:30 PM",
        source_url=_SOURCE_URL,
        ticket_url=_SOURCE_URL,
        price=15.0,
    )

    assert event.to_show(_club()) is None
