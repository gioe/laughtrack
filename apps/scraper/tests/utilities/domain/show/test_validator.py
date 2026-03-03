import re
from datetime import datetime, timedelta

import pytest

from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.validator import ShowValidator


def make_valid_show(**overrides) -> Show:
    base = dict(
        name="Valid Show",
        club_id=1,
        date=datetime.now() + timedelta(days=1),
        show_page_url="https://example.com/show/123",
        lineup=[],
        tickets=[],
        description="",
        room="Main Room",
    )
    base.update(overrides)
    return Show.create(**base)


def test_validate_shows_valid_returns_one_and_no_errors(caplog):
    caplog.clear()
    show = make_valid_show()
    valid, errors = ShowValidator.validate_shows([show])
    assert len(valid) == 1
    assert errors == []


def test_invalid_show_page_url_logs_offender_and_returns_error(caplog):
    caplog.clear()
    show = make_valid_show(show_page_url="not-a-url")

    valid, errors = ShowValidator.validate_shows([show])

    # No valid shows and one error message
    assert len(valid) == 0
    assert any("Show page URL must be a valid URL format" in e for e in errors)

    # Warning log should include our standardized message
    messages = "\n".join(r.message for r in caplog.records)
    assert "Validation failed for show_page_url" in messages


def test_missing_name_logs_and_errors(caplog):
    caplog.clear()
    show = make_valid_show(name="")

    valid, errors = ShowValidator.validate_shows([show])
    assert len(valid) == 0
    assert any("Show name" in e for e in errors)
    messages = "\n".join(r.message for r in caplog.records)
    assert "Validation failed for name" in messages


def test_ticket_invalid_purchase_url_logs_and_errors(caplog):
    caplog.clear()
    bad_ticket = Ticket(price=10.0, purchase_url="not-a-url", type="GA")
    show = make_valid_show(tickets=[bad_ticket])

    valid, errors = ShowValidator.validate_shows([show])
    # Show still considered invalid due to ticket issues
    assert len(valid) == 0
    assert any("purchase URL must be a valid URL format" in e for e in errors)
    messages = "\n".join(r.message for r in caplog.records)
    assert "Validation failed for tickets" in messages
