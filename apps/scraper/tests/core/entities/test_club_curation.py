"""Admission preflight for every venue upsert, including early lookup returns."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock
import json
import pytest
from laughtrack.core.entities.club.curation import curated_venue, venue_payload
from laughtrack.core.entities.club.handler import ClubHandler

@contextmanager
def transaction():
    yield object()

@pytest.mark.parametrize("method,provider,venue", [
    ("upsert_for_eventbrite_venue","eventbrite",SimpleNamespace(id="42",name="Venue",address=None)),
    ("upsert_for_seatengine_venue","seatengine",{"id":42,"name":"Venue"}),
    ("upsert_for_seatengine_v3_venue","seatengine_v3",{"uuid":"42","name":"Venue"}),
    ("upsert_for_ticketmaster_venue","ticketmaster",{"id":"42","name":"Venue"}),
    ("upsert_discovered_venue","discovered",{"name":"Venue","address":"1 Main St"}),
])
@pytest.mark.parametrize("disposition", ["blocked","pending"])
def test_all_upserts_hold_before_legacy_matching(method,provider,venue,disposition):
    h=ClubHandler.__new__(ClubHandler)
    h.transaction=transaction
    h.execute_with_cursor=MagicMock(side_effect=[None,[{"disposition":disposition,"club_id":None}]])
    h._find_fuzzy_match_in_location=MagicMock(side_effect=AssertionError("must not reach legacy matcher"))
    assert getattr(h,method)(venue) is None
    assert "curation_observe_club" in h.execute_with_cursor.call_args_list[0].args[0]
    stored=json.loads(h.execute_with_cursor.call_args_list[0].args[1][1])
    if provider=="eventbrite":
        assert stored[0]["namespace"]=="club-provider:eventbrite_venue_id:v1"

def test_policy_failure_is_not_a_fallback_to_upsert():
    h=ClubHandler.__new__(ClubHandler)
    h.transaction=transaction
    h.execute_with_cursor=MagicMock(side_effect=RuntimeError("Policy unavailable"))
    with pytest.raises(RuntimeError,match="unavailable"):
        h.upsert_discovered_venue({"name":"Venue","address":"1 Main St"})

def test_legacy_match_to_a_different_identity_is_held():
    h=SimpleNamespace(transaction=transaction,execute_with_cursor=MagicMock(side_effect=[None,[{"disposition":"approved","club_id":20}],[{"disposition":"pending","club_id":None}]]))
    @curated_venue("discovered")
    def legacy(self,venue):
        return SimpleNamespace(id=10)
    assert legacy(h,{"name":"Same Name","address":"1 Main St"}) is None

def test_provider_ids_are_not_organizer_or_show_ids():
    p,k=venue_payload({"id":"venue-id","name":"Room","city":{"name":"Boston"},"state":{"stateCode":"MA"},"address":{"line1":"1 Main St"}},"ticketmaster")
    assert p["address"]=="1 Main St, Boston, MA"
    assert k==[{"namespace":"club-provider:ticketmaster_id:v1","scope":"global","value":"venue-id"}]


def test_country_is_preserved_from_provider_address():
    p, _ = venue_payload({"id": "venue-id", "name": "Room", "country": {"countryCode": "CA"},
                          "city": {"name": "London"}, "address": {"line1": "1 Main St"}}, "ticketmaster")
    assert p["country"] == "CA"
    p, _ = venue_payload(SimpleNamespace(id="42", name="Room", address=SimpleNamespace(
        address_1="1 Main St", city="London", region=None, country="GB")), "eventbrite")
    assert p["country"] == "GB"
