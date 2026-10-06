"""Source-scoped, reviewed AnyRoad locations; never infer physical venues."""

import json
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger

KEY = "anyroad_venue_routes"
PINS = {
    "name": "name",
    "address": "address",
    "city": "city",
    "state": "state",
    "postal_code": "zip_code",
    "timezone": "timezone",
}


def normalized(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def positive_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


class AnyRoadVenueRouter:
    def __init__(self, club):
        self.club = club
        self.destinations = {}
        self.errors = []

    @property
    def enabled(self):
        return KEY in self.club.source_metadata

    def hold(self, message):
        self.errors.append(message)
        Logger.warn(f"AnyRoad venue routing incomplete: {message}")
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_scrape_error(f"AnyRoad venue routing incomplete: {message}")

    def configuration(self):
        config = self.club.source_metadata.get(KEY)
        source = self.club.scraping_source
        if not isinstance(config, dict) or source is None or not source.enabled:
            raise ValueError("routing configuration/source unavailable")
        if (
            not positive_id(config.get("source_id"))
            or config.get("source_id") != source.id
            or source.club_id != self.club.id
            or source.scraper_key != "anyroad"
            or not config.get("plugin_id")
            or config["plugin_id"] != self.club.source_metadata.get("plugin_id")
        ):
            raise ValueError("routing source/plugin identity mismatch")
        if not positive_id(config.get("producer_id")) or not isinstance(config.get("routes"), list):
            raise ValueError("reviewed producer and routes required")
        seen = set()
        pins_by_club = {}
        for route in config["routes"]:
            if not isinstance(route, dict) or not positive_id(route.get("club_id")):
                raise ValueError("invalid physical destination")
            location = normalized(route.get("location_info"))
            pins = tuple(normalized(route.get(field)) for field in PINS)
            if not location or not all(pins) or location in seen:
                raise ValueError("incomplete or ambiguous reviewed location")
            if route["club_id"] in pins_by_club and pins_by_club[route["club_id"]] != pins:
                raise ValueError("conflicting physical destination pins")
            ZoneInfo(route["timezone"])
            seen.add(location)
            pins_by_club[route["club_id"]] = pins
        if self.club.id not in pins_by_club:
            raise ValueError("reviewed home location required")
        return config

    def destination_ids(self):
        return sorted({route["club_id"] for route in self.configuration()["routes"]})

    def validate_identity(self, experience_id, url):
        config = self.configuration()
        parsed = urlparse(url)
        prefix = f"/i/plugin/{config['plugin_id']}/tours/"
        slug = parsed.path[len(prefix) :] if parsed.path.startswith(prefix) else ""
        if (
            not experience_id
            or parsed.scheme != "https"
            or parsed.netloc != "app.anyroad.com"
            or not slug
            or "/" in slug
            or "%" in slug
            or parsed.fragment
        ):
            raise ValueError("missing experience ID or conflicting plugin booking URL")

    def destination(self, location):
        config = self.configuration()
        key = normalized(location)
        if not key:
            self.hold("blank experience location; retaining home assignment without asserting venue identity")
            route = next(route for route in config["routes"] if route["club_id"] == self.club.id)
        else:
            route = next((route for route in config["routes"] if normalized(route["location_info"]) == key), None)
            if route is None:
                raise ValueError("explicit experience location is not reviewed")
        destination = self.destinations.get(route["club_id"])
        if destination is None or not destination.visible or destination.status != "active":
            raise ValueError("physical destination unavailable")
        for field, attribute in PINS.items():
            if normalized(getattr(destination, attribute, None)) != normalized(route[field]):
                raise ValueError(f"physical destination {field} changed")
        return destination

    def validate_detail(self, html, experience_id, location):
        soup = BeautifulSoup(html or "", "html.parser")
        about = soup.select('[data-react-class="Views.Plugins.Tours.Page.About"]')
        glance = soup.select('[data-react-class="Views.Plugins.Tours.Page.Glance"]')
        if len(about) != 1 or len(glance) != 1:
            raise ValueError("detail identity or timezone is missing/ambiguous")
        detail = json.loads(about[0].get("data-react-props", "{}"))
        timing = json.loads(glance[0].get("data-react-props", "{}"))
        if not isinstance(detail, dict) or str(detail.get("id", "")) != str(experience_id):
            raise ValueError("detail experience ID mismatch")
        if normalized(detail.get("place")) != normalized(location):
            raise ValueError("detail and list locations conflict")
        destination = self.destination(location)
        if not isinstance(timing, dict) or timing.get("tour_timezone") != destination.timezone:
            raise ValueError("detail timezone conflicts with physical destination")

    def convert(self, event):
        try:
            self.validate_identity(getattr(event, "experience_id", None), event.url)
            destination = self.destination(event.location.name)
            if event.start_date.tzinfo is None:
                raise ValueError("occurrence lacks verified local timezone")
            show = event.to_show(destination, enhanced=True)
            if show is None:
                raise ValueError("event conversion failed")
            show.room = event.location.name.strip() or None
            config = self.configuration()
            show.production_company_id = config["producer_id"]
            show.scraped_by_organizer_id = config["producer_id"]
            show.last_scraped_by = "anyroad"
            return show
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.hold(str(exc))
            return None
