from datetime import datetime, timedelta, timezone

from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.validator import ShowValidator


def make_show(date: datetime) -> Show:
    return Show.create(
        name="Valid Show",
        club_id=1,
        date=date,
        show_page_url="https://example.com/show/123",
        lineup=[],
        tickets=[],
        description="",
        room="Main Room",
    )


def test_show_date_validator_allows_dates_inside_eighteen_month_window():
    show = make_show(datetime.now(timezone.utc) + timedelta(days=540))

    valid, errors = ShowValidator.validate_shows([show])

    assert valid == [show]
    assert errors == []


def test_show_date_validator_rejects_dates_beyond_eighteen_month_window():
    show = make_show(datetime.now(timezone.utc) + timedelta(days=560))

    valid, errors = ShowValidator.validate_shows([show])

    assert valid == []
    assert len(errors) == 1
    assert "more than 18 months in the future" in errors[0]
