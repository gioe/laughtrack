"""Unit tests for GothamEventTransformer.transform_to_show() protocol compliance.

Ensures that GothamEventTransformer.transform_to_show(event) calls
GothamEvent.to_show(club, enhanced=True) without raising a TypeError
(i.e., respects the ShowConvertible protocol signature).
"""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.gotham.transformer import GothamEventTransformer


def _club() -> Club:
    _c = Club(id=2, name='Gotham Comedy Club', address='208 W 23rd St, New York, NY 10011', website='https://www.gothamcomedy.com', popularity=80, zip_code='10011', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.gothamcomedy.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _event(**overrides) -> GothamEvent:
    defaults = dict(
        id="evt-1",
        name="Jerry Seinfeld",
        date="2026-06-15",
        hours=20,
        minutes=0,
    )
    defaults.update(overrides)
    return GothamEvent(**defaults)


def _transformer() -> GothamEventTransformer:
    return GothamEventTransformer(_club())


# ---------------------------------------------------------------------------
# transform_to_show — protocol compliance (the regression this test prevents)
# ---------------------------------------------------------------------------


def test_transform_to_show_returns_show_object():
    """GothamEventTransformer.transform_to_show must not raise TypeError.

    Regression: GothamEvent.to_show() was missing the 'enhanced' param required
    by the ShowConvertible protocol — DataTransformer.transform_to_show calls
    raw_data.to_show(club, enhanced=True).
    """
    show = _transformer().transform_to_show(_event())
    assert isinstance(show, Show)


def test_transform_to_show_club_id_matches():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.club_id == 2


def test_transform_to_show_date_is_timezone_aware():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.date.tzinfo is not None


def test_transform_to_show_name_matches_event():
    show = _transformer().transform_to_show(_event())
    assert show is not None
    assert show.name == "Jerry Seinfeld"


# ---------------------------------------------------------------------------
# transform_to_show — degenerate inputs
# ---------------------------------------------------------------------------


def test_transform_to_show_returns_none_for_missing_name():
    show = _transformer().transform_to_show(_event(name=""))
    assert show is None


def test_transform_to_show_returns_none_for_missing_date():
    show = _transformer().transform_to_show(_event(date=""))
    assert show is None


# ---------------------------------------------------------------------------
# can_transform
# ---------------------------------------------------------------------------


def test_can_transform_returns_true_for_gotham_event():
    assert _transformer().can_transform(_event()) is True


def test_can_transform_returns_false_for_non_gotham_event():
    assert _transformer().can_transform("not a GothamEvent") is False
