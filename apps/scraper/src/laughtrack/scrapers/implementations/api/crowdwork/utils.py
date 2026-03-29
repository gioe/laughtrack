"""
Shared utilities for Crowdwork/Fourthwall Tickets venue scrapers.
"""

from typing import Dict, List, Optional

from laughtrack.core.entities.event.philly_improv import PhillyImprovShow

# Common mapping from Rails-style timezone names to IANA equivalents.
# Venues whose Crowdwork API returns Rails names (e.g. "Central Time (US & Canada)")
# should pass this dict as ``rails_to_iana``.  Venues that already return IANA names
# (e.g. PHIT which returns "America/New_York") should pass ``rails_to_iana=None``.
RAILS_TO_IANA: Dict[str, str] = {
    "Central Time (US & Canada)": "America/Chicago",
    "Eastern Time (US & Canada)": "America/New_York",
    "Pacific Time (US & Canada)": "America/Los_Angeles",
    "Mountain Time (US & Canada)": "America/Denver",
}


def extract_performances(
    show: dict,
    default_timezone: str = "America/Chicago",
    rails_to_iana: Optional[Dict[str, str]] = None,
) -> List[PhillyImprovShow]:
    """
    Convert one Crowdwork show dict into one PhillyImprovShow per performance date.

    A single show may have multiple performance dates in its ``dates`` array.

    Args:
        show: A single show dict from the Crowdwork API ``data`` collection.
        default_timezone: IANA timezone string used when the show's ``timezone``
            field is absent.  Defaults to ``"America/Chicago"``.
        rails_to_iana: Optional mapping from Rails-style timezone names to IANA
            equivalents.  When provided, the show's ``timezone`` value is
            normalised through this mapping before use (pass ``RAILS_TO_IANA``
            for venues that return Rails names).  When ``None``, the raw value
            is used as-is (suitable for venues that already return IANA names).

    Returns:
        A list of ``PhillyImprovShow`` instances, one per performance date.
        Returns an empty list if the show has no dates.
    """
    name = show.get("name") or "Comedy Show"
    url = show.get("url") or ""

    raw_tz = show.get("timezone") or default_timezone
    if rails_to_iana is not None:
        timezone = rails_to_iana.get(raw_tz, raw_tz)
    else:
        timezone = raw_tz

    cost_obj = show.get("cost") or {}
    cost_formatted = (cost_obj.get("formatted") or "") if isinstance(cost_obj, dict) else ""

    desc_obj = show.get("description") or {}
    description = (desc_obj.get("body") or "") if isinstance(desc_obj, dict) else ""

    badges_obj = show.get("badges") or {}
    spots = (badges_obj.get("spots") or "") if isinstance(badges_obj, dict) else ""
    sold_out = spots.lower().startswith("sold out") if spots else False

    dates = show.get("dates") or []
    if not dates:
        next_date = show.get("next_date")
        if next_date:
            dates = [next_date]

    performances = []
    for date_str in dates:
        if not date_str:
            continue
        performances.append(
            PhillyImprovShow(
                name=name,
                date_str=str(date_str),
                timezone=timezone,
                url=url,
                cost_formatted=cost_formatted,
                sold_out=sold_out,
                description=description,
            )
        )

    return performances
