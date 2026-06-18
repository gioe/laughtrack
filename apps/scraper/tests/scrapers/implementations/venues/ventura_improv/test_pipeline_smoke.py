"""Pipeline smoke tests for VenturaImprovScraper / VenturaImprovExtractor.

Exercises the hand-maintained "Coming Up" block parser against a fixture
modeled on venturaimprov.com/shows, plus the VenturaImprovEvent.to_show
transformation. Date inference is exercised with an injected ``today`` so the
tests are hermetic (no time-bomb).
"""

from datetime import date

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.ventura_improv import VenturaImprovEvent
from laughtrack.scrapers.implementations.venues.ventura_improv.extractor import (
    VenturaImprovExtractor,
)

TZ = "America/Los_Angeles"


def _shows_html(title="Improv Match", date_line="FRI July 10 – 7PM", price="$10") -> str:
    """A trimmed /shows page with a single 'Coming Up' block."""
    return f"""
<html><body>
<div class="hero"><h1>Shows</h1></div>
<section class="coming-up">
  <h2>Coming Up</h2>
  <h3>{title}</h3>
  <p class="date">{date_line}</p>
  <p class="venue">NAMBA Arts, 47 S. Oak St., Ventura</p>
  <p class="desc">Two teams of improvisers battle for improv glory.</p>
  <p class="tix">Tix: {price} <span>+ fee</span> online or $15/door</p>
  <a class="btn" href="https://nambaarts.com/ventura-improv-company-34/">Tickets</a>
</section>
<section class="location">
  <h2>Location</h2>
  <p>NAMBA Performing Arts Space, 47 S. Oak Street, Ventura</p>
  <p>Tix: $99 parking</p>
</section>
</body></html>
"""


def _club() -> Club:
    c = Club(
        id=8884, name="Ventura Improv Company", address="47 S Oak St, Ventura, CA 93001",
        website="https://venturaimprov.com/", popularity=0, zip_code="93001",
        phone_number="", visible=False, timezone=TZ,
    )
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform="custom", scraper_key="ventura_improv",
        source_url="https://venturaimprov.com/shows/", external_id=None,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


# ---------------------------------------------------------------------------
# extractor
# ---------------------------------------------------------------------------


def test_extracts_single_upcoming_show():
    events = VenturaImprovExtractor.extract_shows(_shows_html(), today=date(2026, 6, 1))
    assert len(events) == 1
    e = events[0]
    assert e.name == "Improv Match"
    assert e.dt_str == "2026-07-10 19:00:00"
    assert e.price == 10.0  # lowest online price, not the $15 door or $99 parking (outside block)
    assert e.ticket_url == "https://nambaarts.com/ventura-improv-company-34/"


def test_time_with_minutes_and_full_month():
    events = VenturaImprovExtractor.extract_shows(
        _shows_html(date_line="Sat August 2 – 7:30 PM"), today=date(2026, 6, 1)
    )
    assert events[0].dt_str == "2026-08-02 19:30:00"


def test_past_date_rolls_to_next_year():
    # Page seen in December listing a January show → next year.
    events = VenturaImprovExtractor.extract_shows(
        _shows_html(date_line="FRI January 9 – 7PM"), today=date(2026, 12, 20)
    )
    assert events[0].dt_str == "2027-01-09 19:00:00"


def test_no_coming_up_block_returns_empty():
    assert VenturaImprovExtractor.extract_shows("<html><body>no block here</body></html>") == []


def test_coming_up_without_parseable_date_returns_empty():
    html = "<section><h2>Coming Up</h2><h3>TBA</h3><p>Stay tuned!</p></section>"
    assert VenturaImprovExtractor.extract_shows(html, today=date(2026, 6, 1)) == []


def test_price_unknown_when_absent():
    html = """
<section><h2>Coming Up</h2><h3>Free Jam</h3>
<p>FRI July 10 – 7PM</p><a href="https://nambaarts.com/x/">Tickets</a></section>
<section><h2>Location</h2></section>
"""
    events = VenturaImprovExtractor.extract_shows(html, today=date(2026, 6, 1))
    assert len(events) == 1 and events[0].price is None


# ---------------------------------------------------------------------------
# to_show
# ---------------------------------------------------------------------------


def test_to_show_builds_pacific_show_with_ticket():
    event = VenturaImprovEvent(
        name="Improv Match", dt_str="2026-07-10 19:00:00", price=10.0,
        ticket_url="https://nambaarts.com/ventura-improv-company-34/",
    )
    show = event.to_show(_club())
    assert show is not None
    assert show.name == "Improv Match"
    assert show.date.year == 2026 and show.date.month == 7 and show.date.day == 10
    assert show.date.hour == 19
    assert str(show.date.utcoffset()) in ("-1 day, 17:00:00",)  # PDT (-07:00)
    assert show.tickets[0].price == 10.0


def test_to_show_returns_none_on_bad_datetime():
    event = VenturaImprovEvent(name="X", dt_str="not-a-date", price=None)
    assert event.to_show(_club()) is None


def test_abbreviated_month_name_is_parsed():
    # Hand-edited page may abbreviate the month ("Jul"); must not silently drop.
    events = VenturaImprovExtractor.extract_shows(
        _shows_html(date_line="FRI Jul 10 – 7PM"), today=date(2026, 6, 1)
    )
    assert len(events) == 1
    assert events[0].dt_str == "2026-07-10 19:00:00"
