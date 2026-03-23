"""Unit tests for SeatEngineV3EventTransformer."""

from unittest.mock import MagicMock

import pytest

from laughtrack.scrapers.implementations.api.seatengine_v3.transformer import (
    SeatEngineV3EventTransformer,
)


def _make_club(timezone: str = "America/New_York") -> MagicMock:
    club = MagicMock()
    club.id = 144
    club.name = "The Comedy Studio"
    club.timezone = timezone
    return club


def _make_record(
    name: str = "Test Show",
    start_datetime: str = "2026-04-01T20:00:00",
    talents: list | None = None,
    inventories: list | None = None,
    sold_out: bool = False,
    show_page_url: str = "https://www.thecomedystudio.com/events/test-show",
) -> dict:
    return {
        "event_name": name,
        "start_datetime": start_datetime,
        "show_page_url": show_page_url,
        "talents": talents or [],
        "inventories": inventories or [],
        "sold_out": sold_out,
    }


def _make_inventory(
    title: str = "General Admission",
    price: int = 2000,
    active: bool = True,
) -> dict:
    return {"uuid": "inv-1", "title": title, "name": title, "price": price, "active": active}


class TestCanTransform:
    def test_valid_record_accepted(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        assert transformer.can_transform(_make_record())

    def test_missing_event_name_rejected(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record()
        del record["event_name"]
        assert not transformer.can_transform(record)

    def test_missing_start_datetime_rejected(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record()
        del record["start_datetime"]
        assert not transformer.can_transform(record)

    def test_non_dict_rejected(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        assert not transformer.can_transform("not a dict")
        assert not transformer.can_transform(None)
        assert not transformer.can_transform([])


class TestTransformToShow:
    def test_basic_show_created(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        show = transformer.transform_to_show(_make_record(name="Comedy Night"))
        assert show is not None
        assert show.name == "Comedy Night"
        assert show.club_id == 144

    def test_lineup_populated_from_talents(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record(talents=["Alice Smith", "Bob Jones"])
        show = transformer.transform_to_show(record)
        assert show is not None
        names = [c.name for c in show.lineup]
        assert "Alice Smith" in names
        assert "Bob Jones" in names

    def test_empty_talents_yields_empty_lineup(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        show = transformer.transform_to_show(_make_record(talents=[]))
        assert show is not None
        assert show.lineup == []

    def test_show_page_url_set(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        url = "https://www.thecomedystudio.com/events/some-show"
        show = transformer.transform_to_show(_make_record(show_page_url=url))
        assert show is not None
        assert show.show_page_url == url


class TestBuildTickets:
    def test_price_converted_from_cents_to_dollars(self):
        """SeatEngine v3 returns prices in cents; transformer divides by 100."""
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record(inventories=[_make_inventory(price=2000)])
        show = transformer.transform_to_show(record)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == pytest.approx(20.0)

    def test_free_show_zero_price(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record(inventories=[_make_inventory(price=0)])
        show = transformer.transform_to_show(record)
        assert show is not None
        assert show.tickets[0].price == pytest.approx(0.0)

    def test_inactive_inventory_excluded(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        inventories = [
            _make_inventory(title="Active", price=1500, active=True),
            _make_inventory(title="Inactive", price=500, active=False),
        ]
        record = _make_record(inventories=inventories)
        show = transformer.transform_to_show(record)
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].price == pytest.approx(15.0)

    def test_sold_out_propagated_to_tickets(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record(
            inventories=[_make_inventory(price=2600)],
            sold_out=True,
        )
        show = transformer.transform_to_show(record)
        assert show is not None
        assert show.tickets[0].sold_out is True

    def test_not_sold_out(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record(
            inventories=[_make_inventory(price=2600)],
            sold_out=False,
        )
        show = transformer.transform_to_show(record)
        assert show is not None
        assert show.tickets[0].sold_out is False

    def test_title_used_as_ticket_type(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        record = _make_record(inventories=[_make_inventory(title="VIP")])
        show = transformer.transform_to_show(record)
        assert show is not None
        assert show.tickets[0].type == "VIP"

    def test_fallback_to_general_admission_when_no_title(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        inv = {"uuid": "inv-1", "title": None, "name": None, "price": 1000, "active": True}
        record = _make_record(inventories=[inv])
        show = transformer.transform_to_show(record)
        assert show is not None
        assert show.tickets[0].type == "General Admission"

    def test_no_inventories_yields_no_tickets(self):
        transformer = SeatEngineV3EventTransformer(_make_club())
        show = transformer.transform_to_show(_make_record(inventories=[]))
        assert show is not None
        assert show.tickets == []
