"""Producer query scoping and native occurrence integrity."""

import json
from copy import deepcopy

import pytest

from laughtrack.core.clients.punchup.inventory import extract_inventory, merge_events
from tests.scrapers.implementations.venues.the_comedy_shoppe.test_punchup_routing import PAGE, PROJECTION, html


def test_unrelated_query_cannot_supply_locations_or_shows():
    text = html().replace("venueShows", "unrelatedShows")
    with pytest.raises(ValueError, match="Missing source-bound"):
        extract_inventory(text, PAGE, "comedyshoppe")


def test_non_show_carousel_and_duplicate_entries_are_not_extra_events():
    result = extract_inventory(html(), PAGE, "comedyshoppe")
    assert len(result.events) == 24 and not result.errors
    assert len({e["id"] for e in result.events}) == 24


def test_same_id_different_ticket_or_destination_is_held():
    original = PROJECTION["events"][0]
    for field in ("ticket_link", "venue_id", "datetime"):
        altered = dict(original, **{field: "different"})
        events, errors = merge_events([original, altered, original])
        assert not events and errors


def test_fragments_with_unrelated_valid_json_are_not_treated_as_inventory():
    payload = (
        "<script>self.__next_f.push([1," + json.dumps("1:" + json.dumps({"data": PROJECTION["events"]})) + "])</script>"
    )
    with pytest.raises(ValueError):
        extract_inventory(payload, PAGE, "comedyshoppe")


def test_missing_native_identity_is_not_silently_dropped():
    raw = deepcopy(PROJECTION["events"])
    raw[0].pop("id")
    result = extract_inventory(html(raw), PAGE, "comedyshoppe")
    assert result.errors and len(result.events) == 23
