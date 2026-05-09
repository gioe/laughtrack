"""Unit tests for the shared Tixologi extractor."""

import json

from laughtrack.core.clients.tixologi.extractor import (
    TixologiCmsEvent,
    TixologiExtractor,
    TixologiPartner,
)
from laughtrack.core.entities.event.tixologi import TixologiEvent


TICKET_URL = "https://www.laughfactory.club/checkout/show/abc-123-uuid"


def _show_html(date: str = "Wed\xa0Apr 10", time: str = "7:00 PM") -> str:
    return f"""<html><body>
<div class="show-sec jokes">
  <div class="shedule">
    <span class="date">{date}</span>
    <span class="timing">{time}</span>
    <div class="tickets">
      <a href="{TICKET_URL}" class="readmore-btn ticket-toggle-btn">Buy Tickets</a>
    </div>
  </div>
  <div class="show-content">
    <div class="show-top-content-sec">
      <h4>Comedy Night</h4>
      <div class="show-thumbnails-sec">
        <figure><figcaption>Jane Doe</figcaption></figure>
      </div>
    </div>
  </div>
</div>
</body></html>"""


def test_partner_api_endpoint_uses_partner_id():
    assert (
        TixologiExtractor.partner_api_endpoint(690)
        == "https://api-v2.tixologi.com/public/users/partners/690"
    )


def test_parse_partner_response_from_mapping():
    partner = TixologiExtractor.parse_partner_response(
        {"id": 690, "name": "Laugh Factory - Long Beach", "punchup_id": "partner-uuid"}
    )

    assert partner == TixologiPartner(
        partner_id=690,
        name="Laugh Factory - Long Beach",
        punchup_id="partner-uuid",
    )


def test_parse_partner_response_from_json_string():
    partner = TixologiExtractor.parse_partner_response(
        json.dumps({"partner_id": "690", "name": "Laugh Factory - Long Beach"})
    )

    assert partner == TixologiPartner(
        partner_id=690,
        name="Laugh Factory - Long Beach",
        punchup_id=None,
    )


def test_parse_partner_response_returns_none_for_malformed_payloads():
    assert TixologiExtractor.parse_partner_response("not-json") is None
    assert TixologiExtractor.parse_partner_response({"id": 690}) is None
    assert TixologiExtractor.parse_partner_response([]) is None


def test_normalize_ticket_reference_prefers_explicit_event_id():
    reference = TixologiExtractor.normalize_ticket_reference(
        " https://event.tixologi.com/event/99/tickets ",
        " 42 ",
    )

    assert reference.ticket_url == "https://event.tixologi.com/event/99/tickets"
    assert reference.event_id == "42"


def test_normalize_ticket_reference_extracts_event_tixologi_id_from_url():
    reference = TixologiExtractor.normalize_ticket_reference(
        "https://event.tixologi.com/event/99/tickets"
    )

    assert reference.event_id == "99"


def test_extract_cms_events_returns_event_shape():
    events = TixologiExtractor.extract_cms_events(_show_html())

    assert len(events) == 1
    assert isinstance(events[0], TixologiCmsEvent)
    assert events[0].title == "Comedy Night"
    assert events[0].date_str == "Apr 10"
    assert events[0].time_str == "7:00 PM"
    assert events[0].ticket_url == TICKET_URL
    assert events[0].punchup_id == "abc-123-uuid"
    assert events[0].comedians == ["Jane Doe"]


def test_extract_cms_events_handles_space_separated_weekday():
    events = TixologiExtractor.extract_cms_events(_show_html(date="Wed Apr 10"))

    assert len(events) == 1
    assert events[0].date_str == "Apr 10"


def test_extract_shows_returns_tixologi_events():
    events = TixologiExtractor.extract_shows(
        _show_html(),
        club_id=210,
        timezone="America/Los_Angeles",
    )

    assert len(events) == 1
    assert isinstance(events[0], TixologiEvent)
    assert events[0].club_id == 210
    assert events[0].timezone == "America/Los_Angeles"


def test_extract_shows_returns_empty_for_malformed_or_empty_html():
    assert TixologiExtractor.extract_shows("", club_id=210, timezone="America/Los_Angeles") == []
    assert (
        TixologiExtractor.extract_shows(
            "<html><body>No shows here</body></html>",
            club_id=210,
            timezone="America/Los_Angeles",
        )
        == []
    )
