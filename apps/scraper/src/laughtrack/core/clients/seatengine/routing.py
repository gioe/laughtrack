"""Source-owned, reviewed native performance routes; never infer from biographies."""

from datetime import datetime
from zoneinfo import ZoneInfo

from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger

ROUTES_KEY = "seatengine_venue_routes"


class RoutingHold(ValueError):
    """The reviewed evidence does not authorize assigning this performance."""


def record_hold(message):
    message = f"SeatEngine venue route held: {message}"
    Logger.warn(message)
    diagnostics = current_diagnostics()
    if diagnostics is not None:
        diagnostics.record_scrape_error(message)


def _positive_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def configuration(club):
    """None means ordinary venue behavior; malformed opt-ins always fail closed."""
    if ROUTES_KEY not in club.source_metadata:
        return None
    config = club.source_metadata[ROUTES_KEY]
    if not club.scraping_source or not club.scraping_source.enabled:
        raise RoutingHold("source is disabled")
    if not isinstance(config, dict) or str(config.get("account_id")) != str(club.seatengine_id):
        raise RoutingHold("configuration account does not match the source")
    if not _positive_id(config.get("producer_id")) or not isinstance(config.get("routes"), dict):
        raise RoutingHold("configuration needs a producer ID and reviewed routes")
    return config


def destination_ids(club):
    config = configuration(club)
    if config is None:
        return []
    ids = set()
    for route in config["routes"].values():
        if not isinstance(route, dict) or route.get("disposition") not in {"route", "hold"}:
            raise RoutingHold("invalid route disposition")
        if route["disposition"] == "route":
            if not _positive_id(route.get("club_id")):
                raise RoutingHold("invalid destination club ID")
            ids.add(route["club_id"])
    return sorted(ids)


def resolve(club, payload, destinations):
    config = configuration(club)
    if config is None:
        return club, None
    ident = payload.get("id")
    if not (_positive_id(ident) or (isinstance(ident, str) and ident.isdigit() and int(ident) > 0)):
        raise RoutingHold("missing valid native show ID")
    route = config["routes"].get(str(ident))
    if not isinstance(route, dict) or route.get("disposition") != "route":
        raise RoutingHold(f"account {club.seatengine_id} show {ident} lacks an approved route")
    if not isinstance(route.get("reason"), str) or not route["reason"].strip():
        raise RoutingHold(f"show {ident} lacks reviewed evidence")
    if not _positive_id(route.get("club_id")):
        raise RoutingHold(f"show {ident} has an invalid destination club ID")
    destination = destinations.get(route["club_id"])
    if destination is None or destination.id != route["club_id"]:
        raise RoutingHold(f"show {ident} destination unavailable")
    if not destination.visible or not destination.timezone:
        raise RoutingHold(f"show {ident} destination is hidden or lacks a timezone")
    try:
        zone = ZoneInfo(destination.timezone)
        observed = datetime.fromisoformat(payload["start_date_time"].replace("Z", "+00:00"))
        expected = datetime.fromisoformat(route["start_date_time"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RoutingHold(f"show {ident} has an invalid reviewed occurrence/timezone") from exc
    if (observed.tzinfo is None) != (expected.tzinfo is None) or observed != expected:
        raise RoutingHold(f"show {ident} occurrence changed")
    if (
        observed.tzinfo is None
        and observed.replace(tzinfo=zone, fold=0).utcoffset() != observed.replace(tzinfo=zone, fold=1).utcoffset()
    ):
        raise RoutingHold(f"show {ident} wall time is ambiguous or nonexistent; review an explicit offset")
    return destination, config["producer_id"]
