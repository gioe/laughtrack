import pytest

from laughtrack.scrapers.implementations.api.eventbrite.extractor import EventbriteExtractor
from laughtrack.core.entities.event.eventbrite import EventbriteEvent


def _ev(name: str = "A", url: str = "https://e/1", start: str = "2025-01-01T20:00:00Z") -> EventbriteEvent:
    return EventbriteEvent(
        name=name,
        event_url=url,
        start_date=start,
        description=None,
        location_name=None,
        location_address=None,
        performers=None,
        ticket_offers=None,
        data_source_type="api",
        _raw_json_ld=None,
        _raw_html_data=None,
    )


def test_to_page_data_wraps_list():
    events = [_ev("A"), _ev("B")]
    page = EventbriteExtractor.to_page_data(events)
    assert hasattr(page, "event_list")
    assert list(page.event_list) == events
