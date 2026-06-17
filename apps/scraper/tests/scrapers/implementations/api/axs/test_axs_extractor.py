"""Unit tests for the AXS-skinned venue homepage extractor (TASK-2929).

The fixture is a recorded agoracleveland.com homepage. Its event cards are
royalSlider ``rsCaption`` blocks: ``<h3><a>NAME</a></h3>``, a date ``<h4>``
(``Tue, Jun 16, 2026``), an ``<h4 class="event_venue">`` room label, and an
``axs.com/...?skin=agora`` ticket link.
"""

import os

import pytz

from laughtrack.core.entities.event.axs import AXSEvent
from laughtrack.scrapers.implementations.api.axs.extractor import extract_events

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "agora_homepage.html")


def _load_fixture() -> str:
    with open(_FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class _Club:
    id = 1
    name = "Agora Theater & Ballroom"
    timezone = "America/New_York"

    def metadata_value(self, key):
        return None


class TestExtractEventsFromFixture:
    def test_parses_all_event_cards(self):
        events = extract_events(_load_fixture())
        # The recorded homepage carries 20 event cards.
        assert len(events) == 20

    def test_each_event_has_required_fields(self):
        for ev in extract_events(_load_fixture()):
            assert ev.title
            assert ev.date_str
            assert ev.show_page_url.startswith("http")
            # Every card on this venue links to an AXS ticket URL.
            assert ev.ticket_url and "axs.com/events/" in ev.ticket_url

    def test_captures_comedy_among_concerts(self):
        titles = {e.title for e in extract_events(_load_fixture())}
        assert "Ilana Glazer Live!" in titles  # comedy headliner

    def test_show_page_url_is_venue_detail_not_axs(self):
        ev = next(e for e in extract_events(_load_fixture()) if e.title == "Ilana Glazer Live!")
        assert "agoracleveland.com/events/detail/" in ev.show_page_url
        assert "axs.com" in (ev.ticket_url or "")

    def test_empty_html(self):
        assert extract_events("") == []


class TestToShow:
    def test_builds_future_show_with_default_time(self):
        ev = AXSEvent(
            title="Ilana Glazer Live!",
            date_str="Sat, Jun 16, 2099",
            show_page_url="https://www.agoracleveland.com/events/detail/1351305",
            ticket_url="https://www.axs.com/events/1351305/ilana-glazer-live-tickets?skin=agora",
        )
        show = ev.to_show(_Club())
        assert show is not None
        assert show.name == "Ilana Glazer Live!"
        local = show.date.astimezone(pytz.timezone("America/New_York"))
        assert (local.year, local.hour, local.minute) == (2099, 19, 0)  # default 19:00
        assert show.tickets[0].purchase_url.startswith("https://www.axs.com/")

    def test_default_show_time_override(self):
        class _ClubAt8(_Club):
            def metadata_value(self, key):
                return "20:30" if key == "default_show_time" else None

        ev = AXSEvent(
            title="Late Show",
            date_str="Sat, Jun 16, 2099",
            show_page_url="https://www.agoracleveland.com/events/detail/1",
        )
        show = ev.to_show(_ClubAt8())
        local = show.date.astimezone(pytz.timezone("America/New_York"))
        assert (local.hour, local.minute) == (20, 30)

    def test_ticket_falls_back_to_page_url(self):
        ev = AXSEvent(
            title="No Ticket Link",
            date_str="Sat, Jun 16, 2099",
            show_page_url="https://www.agoracleveland.com/events/detail/2",
            ticket_url=None,
        )
        show = ev.to_show(_Club())
        assert show.tickets[0].purchase_url == "https://www.agoracleveland.com/events/detail/2"

    def test_past_show_returns_none(self):
        ev = AXSEvent(
            title="Old Show",
            date_str="Mon, Jan 06, 2020",
            show_page_url="https://www.agoracleveland.com/events/detail/3",
        )
        assert ev.to_show(_Club()) is None

    def test_unparseable_date_returns_none(self):
        ev = AXSEvent(
            title="Bad Date",
            date_str="sometime next year",
            show_page_url="https://www.agoracleveland.com/events/detail/4",
        )
        assert ev.to_show(_Club()) is None
