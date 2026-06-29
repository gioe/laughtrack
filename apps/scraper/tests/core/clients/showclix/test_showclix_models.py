"""Unit tests for ShowclixEventData.from_dict parsing.

Regression coverage for the GA-only response shape: the Showclix seated-events
API serialises *empty* collections as JSON arrays (``[]``) rather than objects
(``{}``). GA-only events carry no seating sections, so ``event_sections`` and
``sections`` come back as empty lists — the parser used to call ``.items()`` on
them and raise ``'list' object has no attribute 'items'``, dropping the price
for every GA event (observed live across The Comedy Store's calendar).
"""

import pytest

from laughtrack.core.clients.showclix.models import ShowclixEventData


def _base_payload() -> dict:
    """A minimal-but-complete seated-events payload with one GA price level."""
    return {
        "event_id": "10335534",
        "event": "Bobby Lee & Friends",
        "venue": {
            "venue_id": "30111",
            "venue_name": "The Comedy Store",
            "address": "8433 W Sunset Blvd",
            "city": "West Hollywood",
            "state": "CA",
            "zip": "90069",
        },
        "purchase_limit": 8,
        "decimals": 2,
        "getDefaultName": "General Admission",
        "all_levels": {
            "1": {
                "level_id": "1",
                "level": "GA Single Ticket",
                "inventory": 100,
                "price": "25.00",
                "active": True,
                "online_service_fee": "5.00",
            }
        },
        "seatedPriceLevelFees": {},
        "allowOrphanSeats": True,
        "orphanSeatMessage": "",
        "seatedLevels": [],
        # GA-only events return these as empty *lists*, not dicts.
        "event_sections": [],
        "sections": [],
        "remaining_by_level": {"1": 50},
        "held_by_level": {"1": 0},
        "total_by_level": {"1": 100},
        "section_price_levels": {},
        "products": {},
        "product_map": {},
        "disclose_fee": True,
        "fee_verbiage": "",
        "forceConsecutiveSeats": False,
        "forceConsecutiveSeatsMessage": "",
    }


class TestShowclixFromDict:
    def test_ga_only_event_with_list_sections_parses(self):
        """event_sections / sections as [] must not raise and must keep the price."""
        event = ShowclixEventData.from_dict(_base_payload())

        assert event.event_sections == {}
        assert event.sections == {}
        assert event.get_primary_price() == "25.00"

    def test_all_levels_as_empty_list_degrades_to_no_price(self):
        """If all_levels itself comes back as [] there is simply no price."""
        payload = _base_payload()
        payload["all_levels"] = []

        event = ShowclixEventData.from_dict(payload)

        assert event.all_levels == {}
        assert event.get_primary_price() is None

    def test_seated_event_with_dict_sections_still_parses(self):
        """Dict-shaped sections (seated events) keep working unchanged."""
        payload = _base_payload()
        payload["event_sections"] = {
            "501": {
                "arbitrary_id": "501",
                "event_id": "10335534",
                "section_id": "9",
                "price": "30.00",
                "description": "Main Room",
                "rank": 1,
                "general_admission": False,
            }
        }
        payload["sections"] = {
            "9": {"section_id": "9", "venue_id": "30111", "section": "Main Room", "rank": 1}
        }

        event = ShowclixEventData.from_dict(payload)

        assert len(event.event_sections) == 1
        assert len(event.sections) == 1
        assert event.get_primary_price() == "25.00"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
