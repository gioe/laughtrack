"""Unit tests for the generic BookTix extractor (TASK-2922).

Fixtures mirror the verified live DOM of makeshift.booktix.com:
- box office home links productions as ``/dept/main/e/{code}``
- each production page has an ``<h3 class="text-2xl font-bold ...">`` name,
  one or more "Sat Jun 20 2026 - 7:00 PM" showtimes, and a ``$N`` price.
"""

from datetime import datetime

import pytz

from laughtrack.core.entities.event.booktix import BookTixEvent
from laughtrack.scrapers.implementations.api.booktix.extractor import (
    extract_event_urls,
    extract_events,
)

BASE_URL = "https://makeshift.booktix.com"

HOME_HTML = """
<html><body>
  <a href="/dept/main/e/MMG" class="event">My Murder Game</a>
  <a href="/dept/main/e/PNRJune">PNR Improv</a>
  <a href="/dept/main/e/Tomatoes">Tomatoes</a>
  <a href="/dept/main/e/MMG">My Murder Game (dup link)</a>
  <a href="/dept/main/e/TWG">The Wedding Guests</a>
</body></html>
"""

# Single-showtime production (PNR Improv)
PNR_HTML = """
<html><body>
  <div><img src="https://booktix.com/org/328/shows/x.png" class="bg-cover"></div>
  <h3 class="text-2xl font-bold mb-6">Point of No Return Improv Comedy</h3>
  <h6 class="font-medium"></h6>
  <div class="showtime">Sat Jun 20 2026 - 7:00 PM</div>
  <div class="price">$8</div>
</body></html>
"""

# Multi-showtime production (My Murder Game) with repeated price tokens
MMG_HTML = """
<html><body>
  <h3 class="text-2xl font-bold mb-6">My Murder Game</h3>
  <div>Sat Jun 13 2026 - 7:00 PM</div>
  <div>Sun Jun 14 2026 - 2:00 PM</div>
  <div>Fri Jun 19 2026 - 7:00 PM</div>
  <div>Sat Jun 20 2026 - 2:00 PM</div>
  <div>Sun Jun 21 2026 - 2:00 PM</div>
  <span>$10</span><span>$10</span>
</body></html>
"""


class TestExtractEventUrls:
    def test_returns_absolute_deduped_urls_in_order(self):
        urls = extract_event_urls(HOME_HTML, BASE_URL)
        assert urls == [
            "https://makeshift.booktix.com/dept/main/e/MMG",
            "https://makeshift.booktix.com/dept/main/e/PNRJune",
            "https://makeshift.booktix.com/dept/main/e/Tomatoes",
            "https://makeshift.booktix.com/dept/main/e/TWG",
        ]

    def test_empty_html(self):
        assert extract_event_urls("", BASE_URL) == []


class TestExtractEvents:
    def test_single_showtime(self):
        url = "https://makeshift.booktix.com/dept/main/e/PNRJune"
        events = extract_events(PNR_HTML, url)
        assert len(events) == 1
        ev = events[0]
        assert ev.title == "Point of No Return Improv Comedy"
        assert ev.start_date_str == "Sat Jun 20 2026 - 7:00 PM"
        assert ev.ticket_url == url
        assert ev.price == 8.0

    def test_multi_showtime_one_event_per_showtime(self):
        url = "https://makeshift.booktix.com/dept/main/e/MMG"
        events = extract_events(MMG_HTML, url)
        assert len(events) == 5
        assert all(e.title == "My Murder Game" for e in events)
        assert all(e.price == 10.0 for e in events)
        assert "Fri Jun 19 2026 - 7:00 PM" in {e.start_date_str for e in events}

    def test_no_name_returns_empty(self):
        assert extract_events("<html><body><div>Sat Jun 20 2026 - 7:00 PM</div></body></html>", "u") == []

    def test_no_showtimes_returns_empty(self):
        html = '<h3 class="text-2xl font-bold">A Show</h3>'
        assert extract_events(html, "u") == []


class _Club:
    id = 1
    name = "Makeshift Theater"
    timezone = "America/New_York"


class TestToShow:
    def test_builds_show_with_localized_date(self):
        ev = BookTixEvent(
            title="Point of No Return Improv Comedy",
            start_date_str="Sat Jun 20 2026 - 7:00 PM",
            ticket_url="https://makeshift.booktix.com/dept/main/e/PNRJune",
            price=8.0,
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == "Point of No Return Improv Comedy"
        # 7:00 PM America/New_York on 2026-06-20
        expected = pytz.timezone("America/New_York").localize(datetime(2026, 6, 20, 19, 0))
        assert show.date == expected
        assert show.show_page_url == "https://makeshift.booktix.com/dept/main/e/PNRJune"

    def test_unparseable_date_returns_none(self):
        ev = BookTixEvent(title="X", start_date_str="not a date", ticket_url="u")
        assert ev.to_show(_Club()) is None
