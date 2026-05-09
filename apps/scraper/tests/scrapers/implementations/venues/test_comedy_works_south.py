"""Regression tests for Comedy Works South location filtering."""

from laughtrack.scrapers.implementations.venues.comedy_works_south.extractor import (
    ComedyWorksSouthExtractor,
)


DETAIL_HTML = """
<html><body>
<div class="comedian-intro"><h1>South Comic</h1></div>
<div class="ticket-location">
  <p class="club-title club-downtown">Comedy Works Downtown</p>
</div>
<ul class="show-times">
  <li>
    <p class="show-day">Thursday, Jan 1 2099  7:15PM</p>
  </li>
</ul>
<div class="ticket-location">
  <p class="club-title club-south">Comedy Works South</p>
</div>
<ul class="show-times">
  <li>
    <p class="show-day">Friday, Jan 2 2099  9:30PM</p>
    <p class="show-meta">21+</p>
    <button class="seating-section-toggle">Buy Tickets</button>
    <div class="showtime-sections" id="seating-sections-20001">
      <fieldset class="ticket-select">
        <span class="product-name">General Admission</span>
        <span class="product-price">$32.00</span>
      </fieldset>
    </div>
  </li>
</ul>
</body></html>
"""


def test_extract_events_from_detail_returns_south_showtimes_only():
    events = ComedyWorksSouthExtractor.extract_events_from_detail(
        DETAIL_HTML, "south-comic"
    )

    assert len(events) == 1
    assert events[0].name == "South Comic"
    assert events[0].showtime.datetime_str == "Friday, Jan 2 2099  9:30PM"
    assert events[0].showtime.section_id == "20001"
    assert events[0].showtime.tiers[0]["price"] == 32.0
