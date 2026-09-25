"""Real ThunderTix offset/display shapes, verified against merchant detail JSON-LD."""

from datetime import timezone

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.thundertix import ThunderTixPerformance


def club(zone):
    return Club(
        id=11600,
        name="Visani",
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone=zone,
    )


def event(start, display):
    payload = {
        "event_id": 263214,
        "performance_id": 3249140,
        "title": "One Funny Lisa Marie",
        "start": start,
        "truncated_url": "/events/263214",
        "order_products_url": "/orders/new?event_id=263214&performance_id=3249140",
    }
    if display is not None:
        payload["time_with_timezone"] = display
    return ThunderTixPerformance.from_api_response(payload, "https://visanientertainmentinc.thundertix.com")


@pytest.mark.parametrize(
    "start,display,zone,expected",
    [
        (
            "2026-09-25 19:00:00 -0500",
            "Fri - Sep 25, 2026 - 7:00pm EDT",
            "America/New_York",
            "2026-09-25T23:00:00+00:00",
        ),
        (
            "2026-11-03 19:30:00 -0600",
            "Tue - Nov  3, 2026 - 7:30pm EST",
            "America/New_York",
            "2026-11-04T00:30:00+00:00",
        ),
        (
            "2026-09-25 19:00:00 -0500",
            "Fri - Sep 25, 2026 - 7:00pm CDT",
            "America/Chicago",
            "2026-09-26T00:00:00+00:00",
        ),
    ],
)
def test_verified_display_wall_clock_overrides_wrong_numeric_offset(start, display, zone, expected):
    performance = event(start, display)
    show = performance.to_show(club(zone), enhanced=False)
    assert show is not None
    assert show.date.astimezone(timezone.utc).isoformat() == expected
    assert show.date.hour == 19
    assert getattr(show.date.tzinfo, "zone", None) == zone
    assert performance.time_with_timezone == display
    assert show.name == performance.title


@pytest.mark.parametrize(
    "display",
    [
        "not a date",
        "Fri - Sep 25, 2026 - 7:00pm PST",
        "Fri - Sep 25, 2026 - 7:00pm EST",
        "Sat - Sep 25, 2026 - 7:00pm EDT",
        "Fri - Sep 25, 2026 - 25:00pm EDT",
    ],
)
def test_malformed_or_conflicting_display_does_not_fabricate_showtime(display):
    with pytest.raises(ValueError):
        event("2026-09-25 19:00:00 -0500", display).to_show(club("America/New_York"), enhanced=False)


def test_absent_display_preserves_existing_offset_instant():
    show = event("2026-09-25 19:00:00 -0500", None).to_show(club("America/New_York"), enhanced=False)
    assert show.date.astimezone(timezone.utc).isoformat() == "2026-09-26T00:00:00+00:00"


def test_display_requires_known_club_timezone():
    with pytest.raises(ValueError):
        event("2026-09-25 19:00:00 -0500", "Fri - Sep 25, 2026 - 7:00pm EDT").to_show(club(None), enhanced=False)
