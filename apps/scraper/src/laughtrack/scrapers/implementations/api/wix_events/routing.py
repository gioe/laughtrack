"""Reviewed source-scoped Wix physical locations; no name-only inference."""

import re
from datetime import datetime

from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger

KEY = "wix_venue_routes"
FIELDS = ("name", "country", "state", "city", "street_number", "street_name", "postal_code")


def normalized(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def positive_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def signature(location):
    if not isinstance(location, dict) or any(not normalized(location.get(field)) for field in FIELDS):
        raise ValueError("location needs a complete reviewed address and name")
    postal = normalized(location["postal_code"])
    if not re.fullmatch(r"\d{5}(?:-\d{4})?", postal) or normalized(location["country"]) != "us":
        raise ValueError("location needs an explicit US postal identity")
    if not isinstance(location.get("street_apt", ""), str):
        raise ValueError("invalid suite identity")
    return tuple(normalized(location[field]) if field != "postal_code" else postal[:5] for field in FIELDS) + (
        normalized(location.get("street_apt", "")),
    )


class WixVenueRouter:
    def __init__(self, club):
        self.club = club
        self.destinations = {}
        self.errors = []

    @property
    def enabled(self):
        return KEY in self.club.source_metadata

    def hold(self, message):
        self.errors.append(message)
        Logger.warn(f"Wix venue routing held: {message}")
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_scrape_error(f"Wix venue routing held: {message}")

    def configuration(self):
        config = self.club.source_metadata.get(KEY)
        source = self.club.scraping_source
        if not isinstance(config, dict) or source is None or not source.enabled:
            raise ValueError("routing source is disabled or configuration invalid")
        if config.get("source_id") != source.id or config.get("component_id") != self.club.wix_comp_id:
            raise ValueError("routing source/component mismatch")
        if not positive_id(config.get("producer_id")) or not isinstance(config.get("routes"), list):
            raise ValueError("routing requires a producer ID and reviewed locations")
        seen = set()
        for route in config["routes"]:
            if not isinstance(route, dict) or not positive_id(route.get("club_id")):
                raise ValueError("invalid destination club ID")
            key = signature(route.get("location"))
            if key in seen:
                raise ValueError("multiple routes claim the same physical location")
            seen.add(key)
        return config

    def destination_ids(self):
        return sorted({route["club_id"] for route in self.configuration()["routes"]})

    def convert(self, event, enhanced=True):
        if not self.enabled:
            return event.to_show(self.club, enhanced=enhanced)
        try:
            config = self.configuration()
            loc = event.location
            if not isinstance(loc, dict) or loc.get("tbd") is True or loc.get("type", 0) != 0:
                raise ValueError("event location is unknown or not physical")
            address = loc.get("fullAddress") or {}
            street = address.get("streetAddress") or {}
            if (
                loc.get("address")
                and address.get("formattedAddress")
                and normalized(loc["address"]) != normalized(address["formattedAddress"])
            ):
                raise ValueError("event address fields conflict")
            key = signature(
                dict(
                    name=loc.get("name"),
                    country=address.get("country"),
                    state=address.get("subdivision"),
                    city=address.get("city"),
                    street_number=street.get("number"),
                    street_name=street.get("name"),
                    street_apt=street.get("apt", ""),
                    postal_code=address.get("postalCode"),
                )
            )
            route = next((route for route in config["routes"] if signature(route["location"]) == key), None)
            if route is None:
                raise ValueError("event physical location is not reviewed")
            destination = self.destinations.get(route["club_id"])
            if destination is None or not destination.visible or destination.status != "active":
                raise ValueError("physical destination unavailable")
            date = datetime.fromisoformat(event.scheduling["config"]["startDate"].replace("Z", "+00:00"))
            if date.tzinfo is None or not event.id or not event.slug:
                raise ValueError("event lacks an exact occurrence or source identity")
            show = event.to_show(self.club, enhanced=enhanced, venue_club=destination)
            if show is None:
                raise ValueError("event conversion failed")
            show.production_company_id = config["producer_id"]
            show.scraped_by_organizer_id = config["producer_id"]
            show.last_scraped_by = "wix_events"
            return show
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.hold(f"event {event.id}: {exc}")
            return None
