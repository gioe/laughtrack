"""Unit tests for RodneyEventTransformer.transform_to_show and can_transform."""

from datetime import datetime
from unittest.mock import patch

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.venues.rodneys.transformer import RodneyEventTransformer


def _club() -> Club:
    return Club(
        id=42,
        name="Rodney's Comedy Club",
        address="311 W 35th St, New York, NY 10001",
        website="https://rodneyscomedyclub.com",
        scraping_url="https://rodneyscomedyclub.com",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _transformer() -> RodneyEventTransformer:
    return RodneyEventTransformer(_club())


def _event(**overrides) -> RodneyEvent:
    defaults = dict(
        id="evt-1",
        title="Headliner Night",
        date_time=datetime(2026, 6, 15, 20, 0, 0),
        source_url="https://rodneyscomedyclub.com/events/1",
        source_type="html",
        performers=["Alice Smith", "Bob Jones"],
        ticket_info={"price": "20.00", "purchase_url": "https://tickets.example.com/1"},
    )
    defaults.update(overrides)
    return RodneyEvent(**defaults)


# ---------------------------------------------------------------------------
# transform_to_show — happy path
# ---------------------------------------------------------------------------

def test_transform_to_show_returns_show_with_correct_name():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.name == "Headliner Night"


def test_transform_to_show_returns_show_with_timezone_aware_date():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.date.tzinfo is not None


def test_transform_to_show_returns_show_with_correct_lineup():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    names = [c.name for c in show.lineup]
    assert names == ["Alice Smith", "Bob Jones"]


def test_transform_to_show_returns_show_with_tickets():
    show = _transformer().transform_to_show(
        _event(
            source_type="html",
            ticket_info={"price": "25.00", "purchase_url": "https://buy.example.com/t"},
        )
    )
    assert show is not None
    assert len(show.tickets) == 1
    ticket = show.tickets[0]
    assert isinstance(ticket, Ticket)
    assert ticket.price == 25.0
    assert ticket.purchase_url == "https://buy.example.com/t"


def test_transform_to_show_club_id_and_timezone_set():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.club_id == 42
    assert show.timezone == "America/New_York"


# ---------------------------------------------------------------------------
# transform_to_show — date_time is None
# ---------------------------------------------------------------------------

def test_transform_to_show_returns_none_when_date_time_is_none():
    event = _event(date_time=None)
    assert _transformer().transform_to_show(event) is None


# ---------------------------------------------------------------------------
# transform_to_show — parse failure (DateTimeUtils raises)
# ---------------------------------------------------------------------------

def test_transform_to_show_returns_none_when_date_unparseable():
    with patch(
        "laughtrack.scrapers.implementations.venues.rodneys.transformer.DateTimeUtils.parse_datetime_with_timezone",
        side_effect=ValueError("bad date"),
    ):
        assert _transformer().transform_to_show(_event()) is None


# ---------------------------------------------------------------------------
# can_transform
# ---------------------------------------------------------------------------

def test_can_transform_returns_true_for_valid_rodney_event():
    assert _transformer().can_transform(_event()) is True


def test_can_transform_returns_false_for_non_rodney_event():
    assert _transformer().can_transform("not a RodneyEvent") is False


def test_can_transform_returns_false_for_plain_dict():
    assert _transformer().can_transform({"title": "Show", "date_time": datetime.now()}) is False


def test_can_transform_returns_false_when_date_time_is_none():
    assert _transformer().can_transform(_event(date_time=None)) is False


def test_can_transform_returns_false_when_title_is_empty():
    assert _transformer().can_transform(_event(title="")) is False


# ---------------------------------------------------------------------------
# transform_to_show — eventbrite ticket extraction
# ---------------------------------------------------------------------------


def test_transform_to_show_eventbrite_min_max_returns_two_tickets():
    show = _transformer().transform_to_show(
        _event(
            source_type="eventbrite",
            ticket_info={
                "min_price": "15.00",
                "max_price": "40.00",
                "purchase_url": "https://eventbrite.com/e/123",
            },
        )
    )
    assert show is not None
    assert len(show.tickets) == 2
    types = {t.type for t in show.tickets}
    assert types == {"Starting at", "Up to"}
    prices = {t.type: t.price for t in show.tickets}
    assert prices["Starting at"] == 15.0
    assert prices["Up to"] == 40.0


def test_transform_to_show_eventbrite_equal_min_max_returns_one_ticket():
    show = _transformer().transform_to_show(
        _event(
            source_type="eventbrite",
            ticket_info={
                "min_price": "25.00",
                "max_price": "25.00",
                "purchase_url": "https://eventbrite.com/e/456",
            },
        )
    )
    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].type == "Starting at"
    assert show.tickets[0].price == 25.0


# ---------------------------------------------------------------------------
# transform_to_show — 22rams ticket extraction
# ---------------------------------------------------------------------------


def test_transform_to_show_22rams_returns_correct_prices_and_purchase_url():
    show = _transformer().transform_to_show(
        _event(
            source_type="22rams",
            ticket_info={
                "min_price": "10.00",
                "max_price": "30.00",
                "purchase_url": "https://22rams.com/events/789",
            },
        )
    )
    assert show is not None
    assert len(show.tickets) == 2
    prices = {t.type: t.price for t in show.tickets}
    assert prices["Starting at"] == 10.0
    assert prices["Up to"] == 30.0
    for ticket in show.tickets:
        assert ticket.purchase_url == "https://22rams.com/events/789"
