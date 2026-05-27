"""VBO Tickets seat-pricing helpers for Esther's Follies.

Esther's Follies sells reserved seating across three price tiers via VBO
Tickets. The public date slider only yields numeric ``edid`` values; per-show
prices require two extra GETs against the seat-map endpoints, using a session
UUID acquired from the loadplugin endpoint (see ``scraper.py``):

  1. GET v5.0/controls/boxoffice.asp?a=load_seat_map_svg
       &eid=<EID>&edid=<numeric>&mapid=<MAP_ID>&s=<session>
     The SVG response embeds the show's per-occurrence ``eventDateId`` GUID
     inside the seat-map config's ``getseats/<GUID>`` URL, e.g.
       …/plugin/seatmap/getseats/70D33085-…-8E7ED0EA8B1D?s=…&MapID=5835

  2. GET plugin/seatmap/getseats/<GUID>?s=<session>&MapID=<MAP_ID>
     JSON ``{"Seats": [{Price, Total, Status, Section, Type, …}, …]}``:
       - ``Section`` groups seats into tiers ("Tier 1"/"Tier 2"/"Tier 3").
       - ``Price`` is the base price (30/35/40); ``Total`` adds the $5.75 VBO
         fee (35.75/40.75/45.75) and is what the seat-map legend shows buyers.
       - ``Status`` is ``A`` (available), ``S`` (sold), or other hold codes
         (e.g. ``C``); a tier is sold out only when no ``A`` seats remain.

These helpers are deliberately venue-agnostic (``eid``/``map_id`` are
parameters, no Esther's-specific constants) so a future VBO venue can lift them
unchanged; only the venue identifiers live in ``scraper.py``.
"""

import re
from typing import Any, List, Optional

from laughtrack.core.entities.event.esthers_follies import SeatTier

_VBO_BASE = "https://plugin.vbotickets.com"

# The seat-map SVG embeds the getseats URL with the per-show eventDateId GUID.
# Match it via the getseats path so we never confuse it with the session UUID
# (also a GUID) that appears elsewhere in the same response.
_GETSEATS_GUID_RE = re.compile(
    r"seatmap/getseats/"
    r"([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"
)


def seat_map_svg_url(eid: str, edid: str, map_id: str, session: str) -> str:
    """Build the VBO seat-map SVG URL for one show occurrence (numeric edid)."""
    return (
        f"{_VBO_BASE}/v5.0/controls/boxoffice.asp"
        f"?a=load_seat_map_svg&eid={eid}&edid={edid}&mapid={map_id}&s={session}"
    )


def getseats_url(guid: str, map_id: str, session: str) -> str:
    """Build the VBO getseats JSON URL for a show's eventDateId GUID."""
    return f"{_VBO_BASE}/plugin/seatmap/getseats/{guid}?s={session}&MapID={map_id}"


def extract_eventdateid_guid(svg_html: Optional[str]) -> Optional[str]:
    """Extract the per-show eventDateId GUID from the seat-map SVG response.

    Returns the GUID embedded in the seat-map config's ``getseats/<GUID>`` URL,
    or None if the response is empty or has no recognizable getseats URL.
    """
    if not svg_html:
        return None
    match = _GETSEATS_GUID_RE.search(svg_html)
    return match.group(1) if match else None


def parse_seat_tiers(payload: Any) -> List[SeatTier]:
    """Parse a VBO getseats payload into distinct price tiers.

    Groups seats by ``Section`` and, per tier, records the seat ``Total``
    (base price + $5.75 fee) and whether any seat is still available
    (``Status == 'A'``). A tier is sold out when it has no available seats.

    Tiers are returned highest-price first for deterministic ordering. Returns
    an empty list for any malformed/empty payload so callers fall back to a
    single price-unknown ticket.
    """
    if not isinstance(payload, dict):
        return []
    seats = payload.get("Seats")
    if not isinstance(seats, list) or not seats:
        return []

    # section name -> {"totals": [float], "available": int}
    grouped: dict = {}
    for seat in seats:
        if not isinstance(seat, dict):
            continue
        section = seat.get("Section")
        total = seat.get("Total")
        if not section or total is None:
            continue
        try:
            total = float(total)
        except (TypeError, ValueError):
            continue
        if total <= 0:
            continue
        bucket = grouped.setdefault(section, {"totals": [], "available": 0})
        bucket["totals"].append(total)
        if str(seat.get("Status", "")).strip().upper() == "A":
            bucket["available"] += 1

    tiers: List[SeatTier] = []
    for section, bucket in grouped.items():
        if not bucket["totals"]:
            continue
        # Each section is single-priced in practice; min() is a deterministic,
        # defensive choice if a section ever mixes totals.
        tiers.append(
            SeatTier(
                type=section,
                price=min(bucket["totals"]),
                sold_out=bucket["available"] == 0,
            )
        )

    tiers.sort(key=lambda t: t.price or 0.0, reverse=True)
    return tiers
