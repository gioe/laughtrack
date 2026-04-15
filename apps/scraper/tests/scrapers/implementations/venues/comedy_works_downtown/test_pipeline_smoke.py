"""
Pipeline smoke tests for ComedyWorksDowntownScraper.

Exercises extract_comedian_slugs(), extract_events_from_detail(), and
ComedyWorksDowntownEvent.to_show() against sample HTML matching the
actual comedyworks.com structure.
"""

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_works_downtown import (
    ComedyWorksDowntownEvent,
    ComedyWorksDowntownShowtime,
)
from laughtrack.scrapers.implementations.venues.comedy_works_downtown.extractor import (
    ComedyWorksDowntownExtractor,
)


def _club() -> Club:
    return Club(
        id=300,
        name="Comedy Works Downtown",
        address="1226 15th St",
        website="https://www.comedyworks.com",
        scraping_url="https://www.comedyworks.com/events?downtown=1",
        popularity=0,
        zip_code="80202",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )


# ---------------------------------------------------------------------------
# Sample HTML fragments
# ---------------------------------------------------------------------------

EVENTS_LIST_HTML = """
<html><body>
<ul>
  <li class="comedian-box">
    <h2 class="comedian-box-title">
      <a href="/comedians/craig-conant">Craig Conant</a>
    </h2>
  </li>
  <li class="comedian-box">
    <h2 class="comedian-box-title">
      <a href="/comedians/nico-carney">Nico Carney</a>
    </h2>
  </li>
  <li class="comedian-box">
    <h2 class="comedian-box-title">
      <a href="/comedians/craig-conant">Craig Conant</a>
    </h2>
  </li>
  <li class="comedian-box">
    <h2 class="comedian-box-title">
      <a href="/some-other-link">No slug here</a>
    </h2>
  </li>
</ul>
</body></html>
"""

DETAIL_HTML = """
<html><body>
<div class="comedian-intro"><h1>Craig Conant</h1></div>
<div class="ticket-location">
  <p class="club-title club-downtown">Comedy Works Downtown</p>
</div>
<ul class="show-times">
  <li>
    <p class="show-day">Thursday, Jan 1 2099  7:15PM</p>
    <p class="show-meta">No Passes |     21+</p>
    <button class="seating-section-toggle">Buy Tickets</button>
    <div class="showtime-sections" id="seating-sections-19425">
      <fieldset class="ticket-select">
        <span class="product-name">General Admission</span>
        <span class="product-price">$30.00</span>
      </fieldset>
      <fieldset class="ticket-select">
        <span class="product-name">Front Row</span>
        <span class="product-price">$45.00</span>
      </fieldset>
    </div>
  </li>
  <li>
    <p class="show-day">Friday, Jan 2 2099  9:30PM</p>
    <p class="show-meta">21+</p>
    <button class="seating-section-toggle sold-out">Sold Out</button>
    <div class="showtime-sections" id="seating-sections-19426">
      <fieldset class="ticket-select sold-out">
        <span class="product-name">General Admission</span>
        <span class="product-price">$35.00</span>
      </fieldset>
    </div>
  </li>
</ul>
</body></html>
"""

DETAIL_HTML_NO_DOWNTOWN = """
<html><body>
<div class="comedian-intro"><h1>Some Comedian</h1></div>
<div class="ticket-location">
  <p class="club-title club-south">Comedy Works South</p>
</div>
<ul class="show-times">
  <li>
    <p class="show-day">Saturday, Jan 3 2099  8:00PM</p>
    <button class="seating-section-toggle">Buy Tickets</button>
  </li>
</ul>
<ul class="show-times">
  <li>
    <p class="show-day">Sunday, Jan 4 2099  7:00PM</p>
  </li>
</ul>
</body></html>
"""


# ---------------------------------------------------------------------------
# extract_comedian_slugs tests
# ---------------------------------------------------------------------------


def test_extract_comedian_slugs_returns_correct_slugs():
    """extract_comedian_slugs returns slugs from comedian-box links."""
    slugs = ComedyWorksDowntownExtractor.extract_comedian_slugs(EVENTS_LIST_HTML)

    assert "craig-conant" in slugs
    assert "nico-carney" in slugs


def test_extract_comedian_slugs_deduplicates():
    """extract_comedian_slugs deduplicates repeated comedian slugs."""
    slugs = ComedyWorksDowntownExtractor.extract_comedian_slugs(EVENTS_LIST_HTML)

    assert slugs.count("craig-conant") == 1
    assert len(slugs) == 2


def test_extract_comedian_slugs_ignores_non_comedian_links():
    """extract_comedian_slugs skips links that don't match /comedians/{slug}."""
    slugs = ComedyWorksDowntownExtractor.extract_comedian_slugs(EVENTS_LIST_HTML)

    assert all("/" not in s for s in slugs)


def test_extract_comedian_slugs_empty_html():
    """extract_comedian_slugs returns empty list for HTML with no comedian boxes."""
    slugs = ComedyWorksDowntownExtractor.extract_comedian_slugs("<html><body></body></html>")

    assert slugs == []


# ---------------------------------------------------------------------------
# extract_events_from_detail tests
# ---------------------------------------------------------------------------


def test_extract_events_from_detail_returns_downtown_showtimes():
    """extract_events_from_detail returns one event per Downtown showtime."""
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(DETAIL_HTML, "craig-conant")

    assert len(events) == 2
    assert all(e.name == "Craig Conant" for e in events)
    assert all(e.slug == "craig-conant" for e in events)


def test_extract_events_from_detail_extracts_pricing():
    """extract_events_from_detail captures ticket tiers and prices."""
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(DETAIL_HTML, "craig-conant")

    first = events[0]
    assert len(first.showtime.tiers) == 2
    assert first.showtime.tiers[0]["name"] == "General Admission"
    assert first.showtime.tiers[0]["price"] == 30.0
    assert first.showtime.tiers[1]["name"] == "Front Row"
    assert first.showtime.tiers[1]["price"] == 45.0


def test_extract_events_from_detail_detects_sold_out():
    """extract_events_from_detail detects sold-out status on showtimes and tiers."""
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(DETAIL_HTML, "craig-conant")

    assert events[0].showtime.sold_out is False
    assert events[1].showtime.sold_out is True
    assert events[1].showtime.tiers[0]["sold_out"] is True


def test_extract_events_from_detail_extracts_age_restriction():
    """extract_events_from_detail captures age restriction from show-meta."""
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(DETAIL_HTML, "craig-conant")

    assert events[0].showtime.age_restriction == "21+"


def test_extract_events_from_detail_skips_non_downtown():
    """extract_events_from_detail returns empty for a South-only comedian page."""
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(
        DETAIL_HTML_NO_DOWNTOWN, "some-comedian"
    )

    assert events == []


def test_extract_events_from_detail_extracts_section_id():
    """extract_events_from_detail captures section IDs from the seating div."""
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(DETAIL_HTML, "craig-conant")

    assert events[0].showtime.section_id == "19425"
    assert events[1].showtime.section_id == "19426"


def test_extract_events_from_detail_falls_back_name_from_slug():
    """extract_events_from_detail falls back to slug-based name when h1 is missing."""
    html = """
    <html><body>
    <ul class="show-times">
      <li>
        <p class="show-day">Thursday, Jan 1 2099  7:00PM</p>
      </li>
    </ul>
    </body></html>
    """
    events = ComedyWorksDowntownExtractor.extract_events_from_detail(html, "craig-conant")

    assert len(events) == 1
    assert events[0].name == "Craig Conant"


# ---------------------------------------------------------------------------
# ComedyWorksDowntownEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    slug="craig-conant",
    name="Craig Conant",
    datetime_str="Thursday, Jan 1 2099  7:15PM",
    age_restriction="21+",
    sold_out=False,
    tiers=None,
    section_id="19425",
) -> ComedyWorksDowntownEvent:
    return ComedyWorksDowntownEvent(
        slug=slug,
        name=name,
        showtime=ComedyWorksDowntownShowtime(
            datetime_str=datetime_str,
            age_restriction=age_restriction,
            sold_out=sold_out,
            tiers=tiers if tiers is not None else [{"name": "General Admission", "price": 30.0, "sold_out": False}],
            section_id=section_id,
        ),
    )


def test_to_show_returns_show_with_correct_date_and_name():
    """to_show() produces a Show with the correct date and name."""
    event = _make_event()
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Craig Conant"
    assert show.date.year == 2099
    assert show.date.month == 1
    assert show.date.day == 1


def test_to_show_builds_tickets_from_tiers():
    """to_show() creates one Ticket per tier with correct price and type."""
    event = _make_event(tiers=[
        {"name": "General Admission", "price": 30.0, "sold_out": False},
        {"name": "Front Row", "price": 45.0, "sold_out": False},
    ])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 2
    assert show.tickets[0].price == 30.0
    assert show.tickets[0].type == "General Admission"
    assert show.tickets[1].price == 45.0
    assert show.tickets[1].type == "Front Row"


def test_to_show_creates_fallback_ticket_when_no_tiers():
    """to_show() creates a fallback ticket when tiers list is empty."""
    event = _make_event(tiers=[])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert "comedyworks.com" in show.tickets[0].purchase_url


def test_to_show_sets_sold_out_on_tier_tickets():
    """to_show() propagates sold_out from individual tiers to tickets."""
    event = _make_event(tiers=[
        {"name": "General Admission", "price": 35.0, "sold_out": True},
    ])
    show = event.to_show(_club())

    assert show is not None
    assert show.tickets[0].sold_out is True


def test_to_show_fallback_ticket_uses_overall_sold_out():
    """to_show() passes overall sold_out to fallback ticket when no tiers exist."""
    event = _make_event(tiers=[], sold_out=True)
    show = event.to_show(_club())

    assert show is not None
    assert show.tickets[0].sold_out is True


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when datetime_str cannot be parsed."""
    event = _make_event(datetime_str="not-a-date")
    show = event.to_show(_club())

    assert show is None


def test_to_show_includes_age_restriction_in_description():
    """to_show() includes age restriction in the show description."""
    event = _make_event(age_restriction="21+")
    show = event.to_show(_club())

    assert show is not None
    assert "21+" in (show.description or "")


def test_to_show_sets_ticket_purchase_url():
    """to_show() sets the ticket purchase URL to the comedian's page."""
    event = _make_event(slug="craig-conant")
    show = event.to_show(_club())

    assert show is not None
    assert all(
        t.purchase_url == "https://www.comedyworks.com/comedians/craig-conant"
        for t in show.tickets
    )
