from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.friendlysky import FriendlySkyEvent


def _club() -> Club:
    return Club(
        id=407,
        name="Delirious Comedy Club",
        address="450 Fremont St, Las Vegas, NV 89101",
        website="https://deliriouscomedyclub.com",
        popularity=0,
        zip_code="89101",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _event(**overrides) -> FriendlySkyEvent:
    values = {
        "hash_id": "ABC123",
        "name": "Comedian One, Comedian Two",
        "beg_date": "2026-07-23",
        "beg_time": "20:00",
        "venue_name": "Delirious Comedy Club",
        "status": "Y",
        "url_name": "delirious-comedy-club",
        "hash_event_id": "EKR",
        "base_url": "https://tickets.deliriouscomedyclub.com",
    }
    values.update(overrides)
    return FriendlySkyEvent(**values)


def test_to_show_builds_direct_purchase_url_from_url_name_and_hash_event_id():
    show = _event().to_show(_club())

    assert show is not None
    expected = (
        "https://tickets.deliriouscomedyclub.com"
        "/event/delirious-comedy-club/tickets/seg?e=EKR"
    )
    assert show.show_page_url == expected
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == expected


def test_to_show_does_not_use_calendar_url_when_url_name_present():
    show = _event().to_show(_club())

    assert show is not None
    purchase_url = show.tickets[0].purchase_url
    # The bare /event?e=<hashEventId>&g=<hashId> calendar form is the bug we fixed.
    assert "event?e=" not in purchase_url
    assert "&g=" not in purchase_url


def test_to_show_falls_back_to_calendar_url_when_url_name_missing():
    show = _event(url_name="").to_show(_club())

    assert show is not None
    expected = "https://tickets.deliriouscomedyclub.com/event?e=EKR&g=ABC123"
    assert show.show_page_url == expected
    assert show.tickets[0].purchase_url == expected
