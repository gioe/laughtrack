def test_etix_event_to_show_uses_explicit_ticket_prices():
    from laughtrack.core.entities.club.model import Club
    from laughtrack.core.entities.event.etix import EtixEvent

    club = Club(
        id=1,
        name="Etix Test Club",
        address="1 Test St",
        website="https://example.com",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    event = EtixEvent(
        title="Paid Etix Show",
        start_date="2099-05-08T20:00:00",
        time_str="Show at 8:00 PM",
        ticket_url="https://www.etix.com/ticket/p/12345/paid-show",
        ticket_price=35.0,
    )

    show = event.to_show(club)

    assert show is not None
    assert show.tickets[0].price == 35.0
