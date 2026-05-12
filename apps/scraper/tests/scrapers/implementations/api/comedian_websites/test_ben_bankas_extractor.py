from __future__ import annotations

from datetime import datetime, timezone

from laughtrack.scrapers.implementations.api.comedian_websites.extractors import registry as registry_mod
from laughtrack.scrapers.implementations.api.comedian_websites.extractors.registry import (
    BenBankasExtractor,
    get_extractor_for_url,
)


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 5, 12, tzinfo=timezone.utc)


def test_ben_bankas_extractor_parses_visible_tour_table_rows(monkeypatch):
    monkeypatch.setattr(registry_mod, "datetime", _FrozenDateTime)

    html = """
    <table class="eventTable">
      <tr class="eventRow">
        <td class="displayblock gigDate">Fri, May 15th</td>
        <td class="displayblock td_show">
          <a href="https://indianapolis.heliumcomedy.com/events/ben-bankas-700">Helium Indianapolis @ 7:00 PM</a>
        </td>
        <td class="displayblock location_space">
          <img alt="US flag" src="/flag-us.png"> Indianapolis, IN
        </td>
        <td class="displayblock ticket_link"><a href="https://tickets.example/ben-bankas">Tickets</a></td>
      </tr>
      <tr class="eventRow">
        <td class="displayblock gigDate">Sat, Sep 12th</td>
        <td class="displayblock td_show">Deerfoot Inn &amp; Casino @ 7:00 PM</td>
        <td class="displayblock location_space"><img alt="Canada flag"> Calgary, AB</td>
        <td class="displayblock ticket_link">Sold Out</td>
      </tr>
    </table>
    """

    events = BenBankasExtractor().extract_events(html, "https://benbankas.com/")

    assert len(events) == 2
    assert events[0].venue_name == "Helium Indianapolis"
    assert events[0].city == "Indianapolis"
    assert events[0].region == "IN"
    assert events[0].country == "US"
    assert events[0].start_date.year == 2026
    assert events[0].start_date.month == 5
    assert events[0].start_date.day == 15
    assert events[0].start_date.hour == 19
    assert events[0].start_date.tzinfo == timezone.utc
    assert events[0].ticket_url == "https://indianapolis.heliumcomedy.com/events/ben-bankas-700"
    assert events[1].venue_name == "Deerfoot Inn & Casino"
    assert events[1].country == "CA"


def test_registry_selects_ben_bankas_by_hostname():
    extractor = get_extractor_for_url("https://www.benbankas.com/")

    assert isinstance(extractor, BenBankasExtractor)
