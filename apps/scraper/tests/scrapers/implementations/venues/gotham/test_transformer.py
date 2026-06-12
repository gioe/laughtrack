"""Unit tests for GothamEventTransformer.transform_to_show() protocol compliance.

Ensures that GothamEventTransformer.transform_to_show(event) calls
GothamFeedEvent.to_show(club, enhanced=True) without raising a TypeError
(i.e., respects the ShowConvertible protocol signature).

Fixture dates use far-future years (2099) per project convention so date
filtering never turns these tests into time-bombs.
"""

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.gotham.transformer import GothamEventTransformer


def _club() -> Club:
    _c = Club(id=2, name='Gotham Comedy Club', address='208 W 23rd St, New York, NY 10011', website='https://www.gothamcomedyclub.com', popularity=80, zip_code='10011', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.gothamcomedyclub.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _event(**overrides) -> GothamFeedEvent:
    defaults = dict(
        id="6a286dd29da8c9c14b299e74",
        name="The Gotham All-Stars",
        start="2099-06-20T20:00:00-04:00",
        event_id="10378853",
        slug="the-gotham-all-stars2526rbueuau",
        category="Stand-up Comedy Shows",
    )
    defaults.update(overrides)
    return GothamFeedEvent(**defaults)


def _transformer() -> GothamEventTransformer:
    return GothamEventTransformer(_club())


# ---------------------------------------------------------------------------
# transform_to_show — protocol compliance (the regression this test prevents)
# ---------------------------------------------------------------------------


def test_transform_to_show_returns_show_object():
    """GothamEventTransformer.transform_to_show must not raise TypeError.

    Regression: to_show() must accept the 'enhanced' param required by the
    ShowConvertible protocol — DataTransformer.transform_to_show calls
    raw_data.to_show(club, enhanced=True).
    """
    show = _transformer().transform_to_show(_event())
    assert isinstance(show, Show)


def test_transform_to_show_club_id_matches():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.club_id == 2


def test_transform_to_show_date_preserves_feed_offset():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.date.tzinfo is not None
    assert show.date.utcoffset().total_seconds() == -4 * 3600
    assert (show.date.year, show.date.hour, show.date.minute) == (2099, 20, 0)


def test_transform_to_show_name_matches_event():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.name == "The Gotham All-Stars"


def test_transform_to_show_ticket_links_showclix_event_page():
    """Every show emits at least 1 ticket (project invariant)."""
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert len(show.tickets) >= 1
    assert show.tickets[0].purchase_url == "https://www.showclix.com/event/the-gotham-all-stars2526rbueuau"


def test_transform_to_show_emits_ticket_even_without_slug():
    show = _transformer().transform_to_show(_event(slug=None))
    assert show is not None
    assert len(show.tickets) >= 1
    assert show.tickets[0].purchase_url


def test_transform_to_show_carries_enriched_ticket_data():
    show = _transformer().transform_to_show(_event(price=32.0, sold_out=True))
    assert show is not None
    assert show.tickets[0].price == 32.0
    assert show.tickets[0].sold_out is True


def test_transform_to_show_extracts_vintage_lounge_room():
    show = _transformer().transform_to_show(
        _event(name="American Comedy Institute Show (Vintage Lounge)")
    )
    assert show is not None
    assert show.room == "The Vintage Lounge"


def test_transform_to_show_defaults_to_main_room():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.room == "Main Room"


# ---------------------------------------------------------------------------
# transform_to_show — degenerate inputs
# ---------------------------------------------------------------------------


def test_transform_to_show_returns_none_for_missing_name():
    show = _transformer().transform_to_show(_event(name=""))
    assert show is None


def test_transform_to_show_returns_none_for_unparseable_start():
    show = _transformer().transform_to_show(_event(start="TBD"))
    assert show is None


# ---------------------------------------------------------------------------
# can_transform
# ---------------------------------------------------------------------------


def test_can_transform_returns_true_for_gotham_feed_event():
    assert _transformer().can_transform(_event()) is True


def test_can_transform_returns_false_for_non_gotham_event():
    assert _transformer().can_transform("not a GothamFeedEvent") is False
