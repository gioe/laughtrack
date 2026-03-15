"""Unit tests for Club.to_tuple()."""

import pytest

from laughtrack.core.entities.club.model import Club


def _make_club(**kwargs) -> Club:
    defaults = dict(
        id=1,
        name="Test Club",
        address="123 Main St",
        website="https://testclub.com",
        scraping_url="https://testclub.com/events",
        popularity=5,
        zip_code="10001",
        phone_number="555-1234",
        visible=True,
    )
    defaults.update(kwargs)
    return Club(**defaults)


class TestClubToTuple:
    def test_includes_city_and_state_when_set(self):
        club = _make_club(city="New York", state="NY")
        t = club.to_tuple()
        assert club.city in t
        assert club.state in t

    def test_city_and_state_none_when_not_set(self):
        club = _make_club()
        t = club.to_tuple()
        # city and state are the last two elements; both default to None
        assert t[-2] is None
        assert t[-1] is None

    def test_tuple_ends_with_city_state(self):
        club = _make_club(city="Chicago", state="IL")
        t = club.to_tuple()
        assert t[-2] == "Chicago"
        assert t[-1] == "IL"
