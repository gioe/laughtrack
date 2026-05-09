"""Tests for the parameterized Webflow + Tixr public day-card parser."""

from laughtrack.scrapers.implementations.api.tixr.webflow_day_card import (
    WebflowDayCardConfig,
    WebflowDayCardExtractor,
)


_BC_FRAGMENT = "tixr.com/groups/comicstripbc/events/"
_EDMONTON_FRAGMENT = "tixr.com/groups/comicstripedmonton/events/"

_BC_EVENT_URL = "https://www.tixr.com/groups/comicstripbc/events/rell-battle-174083"
_EDMONTON_EVENT_URL = (
    "https://www.tixr.com/groups/comicstripedmonton/events/sean-lecomber-185406"
)
_FOREIGN_EVENT_URL = "https://www.tixr.com/groups/someoneelse/events/foreign-1"


def _bc_html() -> str:
    return f"""<html><body>
<a class="day-card" href="{_BC_EVENT_URL}">
  <div class="event-name show">Rell Battle</div>
  <p class="event-name spaced">East Village</p>
  <div class="date">
    <p class="b-venue">May 7, 2026</p>
    <p class="b-venue">7:30 pm</p>
  </div>
</a>
<a class="day-card" href="{_FOREIGN_EVENT_URL}">
  <div class="event-name show">Foreign Group Show</div>
  <div class="date"><p class="b-venue">May 7, 2026</p><p class="b-venue">7:30 pm</p></div>
</a>
</body></html>"""


def _edmonton_html() -> str:
    return f"""<html><body>
<a class="day-card" href="{_EDMONTON_EVENT_URL}">
  <div class="event-name show">Sean Lecomber</div>
  <p class="event-name spaced">Main Stage</p>
  <div class="date">
    <p class="b-venue">June 12, 2026</p>
    <p class="b-venue">9:00 pm</p>
  </div>
</a>
<a class="day-card" href="{_FOREIGN_EVENT_URL}">
  <div class="event-name show">Foreign Group Show</div>
  <div class="date"><p class="b-venue">June 12, 2026</p><p class="b-venue">9:00 pm</p></div>
</a>
</body></html>"""


def test_webflow_day_card_parser_handles_bc_and_edmonton_configs():
    bc_events = WebflowDayCardExtractor.extract_events(
        _bc_html(),
        source_url="https://bc.houseofcomedy.net/",
        config=WebflowDayCardConfig(tixr_group_fragment=_BC_FRAGMENT),
    )
    edmonton_events = WebflowDayCardExtractor.extract_events(
        _edmonton_html(),
        source_url="https://wem.thecomicstrip.ca/",
        config=WebflowDayCardConfig(tixr_group_fragment=_EDMONTON_FRAGMENT),
    )

    assert len(bc_events) == 1
    assert bc_events[0].title == "Rell Battle"
    assert bc_events[0].date == "2026-05-07"
    assert bc_events[0].time == "7:30 PM"
    assert bc_events[0].room == "East Village"
    assert bc_events[0].ticket_url == _BC_EVENT_URL

    assert len(edmonton_events) == 1
    assert edmonton_events[0].title == "Sean Lecomber"
    assert edmonton_events[0].date == "2026-06-12"
    assert edmonton_events[0].time == "9:00 PM"
    assert edmonton_events[0].room == "Main Stage"
    assert edmonton_events[0].ticket_url == _EDMONTON_EVENT_URL

    bc_with_edmonton_config = WebflowDayCardExtractor.extract_events(
        _bc_html(),
        source_url="https://bc.houseofcomedy.net/",
        config=WebflowDayCardConfig(tixr_group_fragment=_EDMONTON_FRAGMENT),
    )
    assert bc_with_edmonton_config == []
