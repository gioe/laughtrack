from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ovationtix import OvationTixEvent


def _club() -> Club:
    return Club(
        id=1056,
        name="Side Splitters Comedy Club",
        address="12938 N Dale Mabry Hwy, Tampa, FL 33618",
        website="https://sidesplitterscomedy.com",
        popularity=0,
        zip_code="33618",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _event(**overrides) -> OvationTixEvent:
    values = {
        "production_id": "1093071",
        "performance_id": "11719480",
        "production_name": "Mark Normand",
        "start_date": "2026-07-23 19:00",
        "tickets_available": False,
        "event_url": "https://ci.ovationtix.com/35578/production/1093071?performanceId=11719480",
        "sections": [],
    }
    values.update(overrides)
    return OvationTixEvent(**values)


def test_to_show_uses_fallback_ticket_when_performance_has_no_tiers():
    show = _event().to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    ticket = show.tickets[0]
    assert ticket.type == "General Admission"
    assert ticket.purchase_url == "https://ci.ovationtix.com/35578/production/1093071?performanceId=11719480"
    assert ticket.sold_out is True


def test_to_show_preserves_ovationtix_ticket_tiers_when_present():
    show = _event(
        tickets_available=True,
        sections=[
            {
                "ticketGroupName": "Showroom | Lower Level",
                "ticketTypeViews": [
                    {"name": "Lower Level", "price": 25.0},
                    {"name": "VIP", "price": 40.0},
                ],
            }
        ],
    ).to_show(_club())

    assert show is not None
    assert [ticket.type for ticket in show.tickets] == [
        "Showroom | Lower Level - Lower Level",
        "Showroom | Lower Level - VIP",
    ]
    assert [ticket.price for ticket in show.tickets] == [25.0, 40.0]
    assert all(ticket.sold_out is False for ticket in show.tickets)
