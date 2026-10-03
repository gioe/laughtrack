"""Allocation recovery through the real resolver-to-Show conversion path."""

import base64
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from laughtrack.scrapers.implementations.venues.up_comedy_club import scraper as module
from .test_pipeline_smoke import _club, _make_instance


def instance():
    value = _make_instance(name="", sold_out="False")
    value.update(onSale=True, saleState="onSale")
    value["allocations"] = [{
        "id": "allocation", "instanceId": value["id"], "name": "Premium",
        "soldOut": "False", "levels": [{
            "name": "Premium", "price": "30.10", "fee": "2.20", "allocationId": "allocation",
        }],
    }]
    return value


async def convert(monkeypatch, instances, room="UP Comedy Club - Chicago", **extra):
    decoded = {"address": room, "instances": instances, **extra}
    async def fetch(self, url):
        return {"patronticketData": {"patronticketData": base64.b64encode(
            json.dumps(decoded).encode()).decode()}}
    monkeypatch.setattr(module.UPComedyClubScraper, "fetch_json", fetch)
    club = _club()
    data = await module.UPComedyClubScraper(club).get_data("https://www.secondcity.com/api/entityResolver")
    assert data is not None
    return data.event_list, [event.to_show(club, enhanced=False) for event in data.event_list]


@pytest.mark.asyncio
async def test_numeric_units_explicit_fees_and_string_false(monkeypatch):
    events, shows = await convert(monkeypatch, [instance()])
    ticket = shows[0].tickets[0]
    assert (ticket.type, ticket.price, ticket.sold_out) == ("Premium", 32.3, False)
    assert (events[0].currency, events[0].sale_state) == ("USD", "on_sale")


@pytest.mark.asyncio
@pytest.mark.parametrize("price,fee,expected", [
    (0, "0", 0.0), (None, 0, None), ("", 0, None), (True, 0, None),
    (-1, 0, None), ("NaN", 0, None), ("Infinity", 0, None),
    (30, None, None), (30, "bad", None), (30, -1, None),
])
async def test_unknown_is_not_free(monkeypatch, price, fee, expected):
    value = instance()
    value["allocations"][0]["levels"][0].update(price=price, fee=fee)
    _, shows = await convert(monkeypatch, [value])
    assert shows[0].tickets[0].price == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("changes,state,sold_out,price", [
    ({"soldOut": "True"}, "sold_out", True, 32.3),
    ({"soldOut": 1}, "sold_out", True, 32.3),
    ({"onSale": "False", "saleStatus": "On Sale"}, "unavailable", False, None),
    ({"saleState": "notAvailable", "saleStatus": "On Sale"}, "unavailable", False, None),
    ({"onSale": None, "saleState": None}, "unknown", False, None),
])
async def test_sale_states(monkeypatch, changes, state, sold_out, price):
    value = instance()
    value.update(changes)
    events, shows = await convert(monkeypatch, [value])
    assert events[0].sale_state == state
    assert shows[0].tickets[0].sold_out is sold_out
    assert shows[0].tickets[0].price == price


@pytest.mark.asyncio
async def test_sold_out_allocation_and_unique_names(monkeypatch):
    value = instance()
    other = copy.deepcopy(value["allocations"][0])
    other.update(soldOut="True")
    value["allocations"].append(other)
    _, shows = await convert(monkeypatch, [value])
    tickets = shows[0].tickets
    assert len({ticket.type for ticket in tickets}) == 2
    assert [ticket.sold_out for ticket in tickets] == [False, True]


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["instance_id", "allocation_id", "room", "date", "currency", "host"])
async def test_mismatched_identity_never_carries_price(monkeypatch, mutation):
    value = instance()
    room = "UP Comedy Club - Chicago"
    if mutation == "instance_id":
        value["allocations"][0]["instanceId"] = "other-performance"
    elif mutation == "allocation_id":
        value["allocations"][0]["levels"][0]["allocationId"] = "other-allocation"
    elif mutation == "room":
        room = "e.t.c. Theater - Chicago"
    elif mutation == "date":
        value["name"] = "Thursday, May 28, 2026, at 7:00 PM"
    elif mutation == "currency":
        value["currency"] = "CAD"
    else:
        value["purchaseUrl"] = "https://ca.tickets.secondcity.com/checkout/another"
    _, shows = await convert(monkeypatch, [value], room=room)
    assert all(ticket.price is None for ticket in shows[0].tickets)


@pytest.mark.asyncio
@pytest.mark.parametrize("allocations", [None, {}, "bad", [None], [{"levels": "bad"}]])
async def test_bad_allocations_leave_unknown_fallback(monkeypatch, allocations):
    value = instance()
    value["allocations"] = allocations
    _, shows = await convert(monkeypatch, [value])
    assert shows[0].tickets[0].price is None


@pytest.mark.asyncio
async def test_same_title_and_url_do_not_share_performance_prices(monkeypatch):
    first = instance()
    second = copy.deepcopy(first)
    second["id"] = "second"
    second["formattedDates"]["ISO8601"] = "2099-01-02T00:00:00Z"
    second["allocations"][0]["instanceId"] = "second"
    second["allocations"][0]["levels"][0]["price"] = 50
    _, shows = await convert(monkeypatch, [first, second])
    assert [show.tickets[0].price for show in shows] == [32.3, 52.2]
    assert shows[0].date != shows[1].date


@pytest.mark.asyncio
async def test_retained_three_tiers_recover_without_price_scaling(monkeypatch):
    root = next(path for path in Path(__file__).parents if (path / "pyproject.toml").exists())
    data = json.loads((root / "docs/audits/2026-09-27-price-extraction/platforms/updecoded3.json").read_text())
    class FrozenDate(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 27, tzinfo=timezone.utc)
    monkeypatch.setattr(module, "datetime", FrozenDate)
    _, shows = await convert(monkeypatch, data["instances"], room=data["address"])
    assert [(t.type, t.price, t.sold_out) for t in shows[0].tickets] == [
        ("General Admission", 65, False), ("Premium", 85, False), ("Value", 45, False),
    ]
