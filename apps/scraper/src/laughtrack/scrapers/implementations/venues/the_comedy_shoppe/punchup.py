"""The Comedy Shoppe producer calendar with reviewed physical destinations."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

from laughtrack.core.clients.punchup.extractor import PunchupExtractor
from laughtrack.core.clients.punchup.inventory import extract_inventory, merge_events
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import ShoppePageData

KEY = "punchup_venue_routes"
FIELDS = ("name", "address", "city", "state", "postal_code", "country_code")


def normalized(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def positive_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


@dataclass
class RoutedShow:
    show: object

    def to_show(self, club, enhanced=True):
        return self.show


class ShoppeTransformer(DataTransformer):
    def can_transform(self, raw_data):
        return isinstance(raw_data, RoutedShow)


class ComedyShoppeScraper(BaseScraper):
    key = "the_comedy_shoppe"
    PAGE_SIZE = 20
    MAX_PAGES = 25

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.errors = []
        self.transformation_pipeline.register_transformer(ShoppeTransformer(club))

    def hold(self, reason):
        self.errors.append(reason)
        Logger.warn(f"Comedy Shoppe held: {reason}")
        diagnostics = current_diagnostics()
        if diagnostics:
            diagnostics.record_scrape_error(reason)

    def configuration(self):
        config = self.club.source_metadata.get(KEY)
        source = self.club.scraping_source
        if not isinstance(config, dict) or source is None or not source.enabled or config.get("source_id") != source.id:
            raise ValueError("Missing or mismatched reviewed source configuration")
        if not config.get("page_id") or not config.get("slug") or not positive_id(config.get("producer_id")):
            raise ValueError("Missing page or producer identity")
        if not isinstance(config.get("routes"), dict) or not config["routes"]:
            raise ValueError("Missing physical routes")
        for route in config["routes"].values():
            if not isinstance(route, dict) or not positive_id(route.get("club_id")):
                raise ValueError("Invalid physical club ID")
            if any(not normalized(route.get(k)) for k in FIELDS) or route["country_code"] != "US":
                raise ValueError("Incomplete reviewed physical address")
            ZoneInfo(route["timezone"])
        return config

    async def get_data(self, url):
        try:
            config = self.configuration()
            html = await self.fetch_html(url)
            inventory = extract_inventory(html, config["page_id"], config["slug"])
            if inventory.errors:
                raise ValueError("; ".join(inventory.errors))
            events = list(inventory.events)
            # Hydration can be only the first 20; always verify the API terminates.
            for page in range(self.MAX_PAGES):
                endpoint = "https://punchup.live/api/shows?" + urlencode(
                    dict(venuePageId=config["page_id"], limit=self.PAGE_SIZE, offset=page * self.PAGE_SIZE)
                )
                payload = await self.fetch_json(endpoint, headers={"accept": "application/json"})
                if not isinstance(payload, list):
                    raise ValueError("Incomplete PunchUp pagination")
                events.extend(payload)
                if len(payload) < self.PAGE_SIZE:
                    break
            else:
                raise ValueError("PunchUp pagination reached safety limit")
            events, errors = merge_events(events)
            for error in errors:
                self.hold(error)
            ids = sorted({r["club_id"] for r in config["routes"].values()})
            clubs = await asyncio.to_thread(ClubHandler().get_physical_clubs_by_ids, ids)
            destinations = {c.id: c for c in clubs}
            locations = {loc["id"]: loc for loc in inventory.locations}
            output = []
            excluded = self.compile_title_patterns("exclude_title_patterns")
            for event in events:
                if any(pattern.search(event.get("title") or "") for pattern in excluded):
                    diagnostics = current_diagnostics()
                    if diagnostics:
                        diagnostics.add_items_before_filter(1)
                    continue
                try:
                    show = self.route(event, config, locations, destinations)
                    if show:
                        output.append(RoutedShow(show))
                    else:
                        diagnostics = current_diagnostics()
                        if diagnostics:
                            diagnostics.add_items_before_filter(1)
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    self.hold(f"event {event.get('id')}: {exc}")
            return ShoppePageData(output)
        except Exception as exc:
            self.hold(str(exc))
            return ShoppePageData([])

    def route(self, raw, config, locations, destinations):
        if "venue_pages" in raw:
            memberships = raw["venue_pages"]
            if not isinstance(memberships, list) or not any(
                isinstance(page, dict)
                and page.get("id") == config["page_id"]
                and page.get("is_live") is True
                and page.get("show_visibility_status") == "visible"
                for page in memberships
            ):
                raise ValueError("Event is not visible on the reviewed producer page")
        loc = locations.get(raw.get("venue_id"))
        route = config["routes"].get(raw.get("venue_id"))
        if not isinstance(loc, dict) or not isinstance(route, dict):
            raise ValueError("Missing or unreviewed physical location")
        if loc.get("is_deleted") or loc.get("is_pending"):
            raise ValueError("Unavailable native location")
        for key in FIELDS:
            actual, expected = normalized(loc.get(key)), normalized(route.get(key))
            if key == "postal_code":
                actual, expected = actual[:5], expected[:5]
            if not actual or actual != expected:
                raise ValueError(f"Physical location {key} mismatch")
        if normalized(raw.get("venue")) != normalized(loc["name"]) or normalized(raw.get("location")) != normalized(
            f"{loc['city']}, {loc['state']}"
        ):
            raise ValueError("Event venue/city conflicts with physical location")
        destination = destinations.get(route["club_id"])
        if (
            destination is None
            or destination.id == self.club.id
            or not destination.visible
            or destination.status != "active"
            or destination.timezone != route["timezone"]
        ):
            raise ValueError("Verified physical destination unavailable")
        for field, attribute in (
            ("name", "name"),
            ("address", "address"),
            ("city", "city"),
            ("state", "state"),
            ("postal_code", "zip_code"),
        ):
            actual, expected = normalized(getattr(destination, attribute, None)), normalized(route[field])
            if field == "postal_code":
                actual, expected = actual[:5], expected[:5]
            if not actual or actual != expected:
                raise ValueError(f"Physical database destination {field} mismatch")
        date = datetime.fromisoformat(raw["datetime"].replace("Z", "+00:00"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo(destination.timezone))
        if date <= datetime.now(timezone.utc):
            return None
        ticket = urlsplit(raw.get("ticket_link") or "")
        if ticket.scheme != "https" or not ticket.hostname:
            raise ValueError("Missing exact public ticket URL")
        event = PunchupExtractor._build_punchup_show(raw)
        if not event:
            raise ValueError("Missing required show fields")
        # Existing conversion expects local second precision; preserve the instant
        # explicitly afterward for offset-bearing source payloads too.
        event.datetime_str = date.astimezone(ZoneInfo(destination.timezone)).strftime("%Y-%m-%dT%H:%M:%S")
        show = event.to_show(destination)
        if show is None:
            raise ValueError("Show conversion failed")
        show.date = date
        show.production_company_id = config["producer_id"]
        show.scraped_by_organizer_id = config["producer_id"]
        show.last_scraped_by = self.key
        return show

    def scrape_with_result(self):
        self.errors.clear()
        result = super().scrape_with_result()
        if self.errors:
            message = f"Comedy Shoppe inventory incomplete: {len(self.errors)} held/error items"
            result.error = f"{result.error}; {message}" if result.error else message
        return result
