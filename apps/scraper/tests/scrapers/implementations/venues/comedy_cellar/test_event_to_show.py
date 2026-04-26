from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.comedy_cellar import ComedyCellarEvent
from laughtrack.foundation.models.api.comedy_cellar.models import ShowInfoData


def _club():
    _c = Club(id=1, name='Comedy Cellar', address='', website='https://www.comedycellar.com', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.comedycellar.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


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


def _make_event(soldout: bool) -> ComedyCellarEvent:
    return ComedyCellarEvent(
        show_id=999,
        date_key="2025-06-01",
        api_time="20:00:00",
        show_name="Sunday Show",
        description=None,
        note=None,
        room_id=1,
        room_name=None,
        timestamp=1748800000,
        ticket_link="https://www.comedycellar.com/reservations-newyork/?showid=999",
        ticket_data=ShowInfoData(id=999, time="20:00:00", description="", cover=25, soldout=soldout),
        html_container="<div></div>",
        lineup_names=[],
    )


def test_sold_out_false_propagated():
    show = _make_event(soldout=False).to_show(_club(), enhanced=False)
    assert show is not None
    assert show.tickets
    assert show.tickets[0].sold_out is False


def test_sold_out_true_propagated():
    show = _make_event(soldout=True).to_show(_club(), enhanced=False)
    assert show is not None
    assert show.tickets
    assert show.tickets[0].sold_out is True
