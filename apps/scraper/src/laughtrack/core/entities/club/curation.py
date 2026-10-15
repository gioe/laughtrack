"""Shared venue admission before legacy matching/upsert paths.

Identity is provider/location scoped. Visibility and scrape configuration are
not approval evidence. Database triggers independently recheck durable writes.
"""
import json
from functools import wraps


def venue_payload(venue, provider):
    def field(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
    name = field(venue, "name", "") or ""
    address = field(venue, "address", "") or ""
    city, state = field(venue, "city"), field(venue, "state")
    if isinstance(city, dict):
        city = city.get("name")
    if isinstance(state, dict):
        state = state.get("stateCode")
    if not isinstance(address, str):
        city = city or field(address, "city")
        state = state or field(address, "region")
        street = field(address, "address_1") or field(address, "line1", "")
        address = ", ".join(str(x) for x in (street, city, state) if x)
    if not city or not state:
        from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address
        parsed_city, parsed_state = parse_city_state_from_address(address)
        city, state = city or parsed_city, state or parsed_state
    payload = {"name": name, "address": address, "city": city, "state": state,
               "website": field(venue, "website", "") or "",
               "google_place_id": field(venue, "google_place_id") or field(venue, "place_id")}
    source_id = field(venue, "uuid" if provider == "seatengine_v3" else "id")
    key_field = "eventbrite_venue_id" if provider == "eventbrite" else provider + "_id"
    keys = [] if provider == "discovered" or not source_id else [{
        "namespace": "club-provider:" + key_field + ":v1", "scope": "global", "value": str(source_id),
    }]
    return payload, keys


def curated_venue(provider):
    def decorate(fn):
        @wraps(fn)
        def wrapped(self, venue, *args, **kwargs):
            if not venue:
                return None
            payload, keys = venue_payload(venue, provider)
            if not str(payload.get("name") or "").strip():
                return None
            with self.transaction() as conn:
                self.execute_with_cursor(
                    "SELECT curation_observe_club(%s::jsonb,%s::jsonb)",
                    (json.dumps(payload), json.dumps(keys)), conn=conn,
                )
                decisions = self.execute_with_cursor(
                    "SELECT * FROM curation_club_policy(%s::jsonb,%s::jsonb)",
                    (json.dumps(payload), json.dumps(keys)), conn=conn, return_results=True,
                )
            if not decisions or decisions[0]["disposition"] != "approved":
                return None
            result = fn(self, venue, *args, **kwargs)
            if result is None:
                return None
            payload["id"] = result.id
            decisions = self.execute_with_cursor(
                "SELECT * FROM curation_club_policy(%s::jsonb,%s::jsonb)",
                (json.dumps(payload), json.dumps(keys)), return_results=True,
            )
            if not decisions or decisions[0]["disposition"] != "approved" or decisions[0]["club_id"] != result.id:
                return None
            return result
        return wrapped
    return decorate
