from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_cellar import ComedyCellarEvent
from laughtrack.foundation.models.api.comedy_cellar.models import ShowInfoData


def _club():
    return Club(
        id=1,
        name="Comedy Cellar",
        address="",
        website="https://www.comedycellar.com",
        scraping_url="https://www.comedycellar.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )


def test_event_to_show_maps_room_and_lineup():
    ev = ComedyCellarEvent(
        show_id=1705434000,
        date_key="2025-01-10",
        api_time="22:00:00",
        show_name="Late Show",
        description="desc",
        note=None,
        room_id=1,
        room_name=None,  # should map from id
        timestamp=1705434000,
        ticket_link="https://www.comedycellar.com/reservations-newyork/?showid=1705434000",
        ticket_data=ShowInfoData(id=999, time="22:00:00", description="Late Show", roomId=1, timestamp=1705434000, cover=25),
        html_container="<div></div>",
        lineup_names=["Comic A", "Comic B"],
    )

    show = ev.to_show(_club(), enhanced=False)
    assert show is not None
    assert show.name == "Late Show"
    assert show.room == "MacDougal St."
    assert show.lineup and len(show.lineup) == 2
    assert show.show_page_url.endswith("showid=1705434000")
