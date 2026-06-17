"""Unit tests for the generic NeonCRM extractor (TASK-2939).

The fixture is a recorded oionline.app.neoncrm.com eventList.jsp?categoryId=27
(Theater Productions) page. Each row is a
``<div class="neoncrm-event-list-event">`` with a
``<h2 class="neoncrm-event-name"><a href="...event.jsp?event={id}">NAME</a></h2>``
and a ``<div class="neoncrm-event-date">MM/DD/YYYY HH:MM PM - ... ET</div>``.
"""

import os

import pytz

from laughtrack.core.entities.event.neoncrm import NeonCRMEvent
from laughtrack.scrapers.implementations.api.neoncrm.extractor import extract_events

_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "oionline_eventlist_cat27.html"
)
_BASE = "https://oionline.app.neoncrm.com/eventList.jsp?categoryId=27"


def _load_fixture() -> str:
    with open(_FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "Oglebay Institute Towngate Theatre & Cinema"
    timezone = "America/New_York"


class TestExtractEventsFromFixture:
    def test_parses_all_event_rows(self):
        events = extract_events(_load_fixture(), _BASE)
        assert len(events) == 3

    def test_fields_and_absolute_urls(self):
        events = extract_events(_load_fixture(), _BASE)
        first = events[0]
        assert first.title  # non-empty name
        assert first.show_page_url.startswith("https://oionline.app.neoncrm.com/")
        assert "event.jsp?event=" in first.show_page_url
        # start datetime parsed off the "MM/DD/YYYY HH:MM PM - ..." range
        assert first.start_date_str == "07/16/2026 07:00 PM"

    def test_empty_html(self):
        assert extract_events("", _BASE) == []


class TestToShow:
    def test_builds_future_show_with_start_time(self):
        ev = NeonCRMEvent(
            title="Left of Centre Players Improv",
            start_date_str="07/16/2099 07:00 PM",
            show_page_url="https://oionline.app.neoncrm.com/np/clients/oionline/event.jsp?event=99999",
        )
        show = ev.to_show(_Club())
        assert show is not None
        local = show.date.astimezone(pytz.timezone("America/New_York"))
        assert (local.year, local.month, local.day, local.hour) == (2099, 7, 16, 19)
        assert show.tickets[0].purchase_url.endswith("event.jsp?event=99999")

    def test_past_show_returns_none(self):
        ev = NeonCRMEvent(
            title="Old Play",
            start_date_str="01/06/2020 07:00 PM",
            show_page_url="https://oionline.app.neoncrm.com/event.jsp?event=1",
        )
        assert ev.to_show(_Club()) is None

    def test_unparseable_date_returns_none(self):
        ev = NeonCRMEvent(
            title="Bad",
            start_date_str="next thursday",
            show_page_url="https://oionline.app.neoncrm.com/event.jsp?event=2",
        )
        assert ev.to_show(_Club()) is None
