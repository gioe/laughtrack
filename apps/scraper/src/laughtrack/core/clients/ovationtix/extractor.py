"""
Shared OvationTix extraction utilities.

Pure parsing helpers used by all OvationTix-backed venue scrapers.
No HTTP calls — all network I/O is handled by each venue's scraper.
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

import pytz

from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.models.types import JSONDict

# TypeVar for subclass construction
from typing import Type, TypeVar

_E = TypeVar("_E", bound=OvationTixEvent)

# Matches https://ci.ovationtix.com/{clientId}/production/{productionId}
PRODUCTION_URL_RE = re.compile(
    r"https://ci\.ovationtix\.com/(\d+)/production/(\d+)",
    re.IGNORECASE,
)


def extract_client_and_production_ids(html: str) -> Tuple[Optional[str], List[str]]:
    """
    Extract the OvationTix client ID and deduplicated production IDs from HTML.

    Scans for URLs matching https://ci.ovationtix.com/{clientId}/production/{productionId}.

    Returns:
        (client_id, production_ids) — client_id is None if no URLs were found.
    """
    client_id: Optional[str] = None
    seen: set = set()
    ids: List[str] = []
    for cid, prod_id in PRODUCTION_URL_RE.findall(html):
        if client_id is None:
            client_id = cid
        if prod_id not in seen:
            seen.add(prod_id)
            ids.append(prod_id)
    return client_id, ids


def extract_events_from_production(
    production_data: JSONDict,
    production_id: str,
    client_id: str,
    default_name: str = "Comedy Show",
    event_cls: Type[_E] = OvationTixEvent,  # type: ignore[assignment]
) -> List[_E]:
    """
    Build event objects from a Production/performance? API response.

    Args:
        production_data: Parsed JSON from the OvationTix production endpoint.
        production_id: The production ID string (e.g. "1068128").
        client_id: The OvationTix org/client ID (e.g. "36367").
        default_name: Fallback name if productionName and supertitle are absent.
        event_cls: Dataclass type to construct (default: OvationTixEvent).
            Must accept the same __init__ kwargs as OvationTixEvent.

    Returns:
        List of event_cls instances, one per upcoming performance.
    """
    production_name = (
        production_data.get("productionName")
        or production_data.get("supertitle")
        or default_name
    )
    description = production_data.get("description")
    performances = production_data.get("performances") or []

    events: List[_E] = []
    for perf in performances:
        perf_id = perf.get("id")
        start_date = perf.get("startDate")
        if not perf_id or not start_date:
            continue

        tickets_available = bool(perf.get("ticketsAvailable", False))
        available_to_purchase = bool(perf.get("availableToPurchaseOnWeb", False))

        event_url = (
            f"https://ci.ovationtix.com/{client_id}/production/{production_id}"
            f"?performanceId={perf_id}"
        )

        events.append(
            event_cls(
                production_id=production_id,
                performance_id=str(perf_id),
                production_name=production_name,
                start_date=start_date,
                tickets_available=tickets_available and available_to_purchase,
                event_url=event_url,
                description=description,
            )
        )

    return events


def extract_next_performance_info(
    production_response: JSONDict,
) -> Tuple[Optional[str], Optional[str]]:
    """
    From a Production(...)/performance? response, extract the next performance id
    and start date.

    Returns:
        (performance_id, start_date_str)
    """
    try:
        performance_summary = production_response.get("performanceSummary", {}) or {}
        next_performance = performance_summary.get("nextPerformance", {}) or {}
        return next_performance.get("id"), next_performance.get("startDate")
    except Exception:
        return None, None


def is_past_event(start_date_str: str, timezone: str) -> bool:
    """
    Return True if the given date string is in the past for the given timezone.

    Supports both 'YYYY-MM-DD HH:MM' and 'YYYY-MM-DDTHH:MM:SS' formats.
    """
    try:
        tz = pytz.timezone(timezone)
        dt: Optional[datetime] = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(start_date_str, fmt)
                break
            except Exception:
                continue

        if dt is None:
            return False

        event_dt = tz.localize(dt, is_dst=False)
        return event_dt < datetime.now(tz)
    except Exception:
        return False
