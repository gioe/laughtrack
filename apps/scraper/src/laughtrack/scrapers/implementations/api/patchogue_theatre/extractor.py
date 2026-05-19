"""
Patchogue Theatre extractor utilities.

Two pure helpers used by ``PatchogueTheatreScraper``:

1. ``extract_performance_ids`` — pulls every OvationTix ``performance/<id>``
   link out of the Bowery Presents Patchogue listing HTML. Also recognises
   the ``production/<prodId>?performanceId=<perfId>`` form so the same
   helper covers any future Bowery URL shape change.

2. ``event_from_performance_response`` — turns a single ``Performance(<id>)``
   API response into an :class:`OvationTixEvent`. Unlike the production-list
   flow (where one Production yields N performances), Bowery surfaces the
   performance ID directly, so we hit the per-performance endpoint and get
   production identity, start date, sections, and availability in one call.

3. ``is_comedy_relevant`` — narrow text heuristic for filtering Patchogue's
   multi-purpose calendar down to comedy. Matches on
   ``comedian``/``stand-up``/``comic`` (and HTML-tag-stripped variants);
   intentionally rejects bare ``comedy`` so musical theatre productions
   (e.g. "Little Shop of Horrors" — a black-comedy musical) do not slip
   through.
"""

from __future__ import annotations

import html as html_unescape
import re
from typing import List, Optional

from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.foundation.models.types import JSONDict


_PERFORMANCE_URL_RE = re.compile(
    r"ci\.ovationtix\.com/(\d+)/performance/(\d+)",
    re.IGNORECASE,
)
_PRODUCTION_PERFORMANCE_URL_RE = re.compile(
    r"ci\.ovationtix\.com/(\d+)/production/\d+\?[^\"'<>\s]*performanceId=(\d+)",
    re.IGNORECASE,
)

_COMEDY_MARKERS = (
    re.compile(r"\bcomedian(s)?\b", re.IGNORECASE),
    re.compile(r"\bstand[-\s]?up\b", re.IGNORECASE),
    re.compile(r"\bcomic(s)?\b", re.IGNORECASE),
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def extract_performance_ids(html: str, client_id: Optional[str] = None) -> List[str]:
    """Return deduplicated performance IDs from the Bowery listing HTML.

    Order is preserved (first occurrence wins) so callers that fan-out
    pricing fetches honour the page's visual ordering.

    When ``client_id`` is provided, only links carrying that client ID are
    accepted; this prevents a future Bowery layout (which already promotes
    other venues on adjacent panels) from leaking foreign performances into
    Patchogue's scrape.
    """
    seen: set = set()
    ids: List[str] = []

    def _add(cid: str, perf_id: str) -> None:
        if client_id is not None and cid != str(client_id):
            return
        if perf_id in seen:
            return
        seen.add(perf_id)
        ids.append(perf_id)

    for cid, perf_id in _PERFORMANCE_URL_RE.findall(html):
        _add(cid, perf_id)
    for cid, perf_id in _PRODUCTION_PERFORMANCE_URL_RE.findall(html):
        _add(cid, perf_id)
    return ids


def event_from_performance_response(
    performance_data: JSONDict,
    client_id: str,
    default_name: str = "Comedy Show",
) -> Optional[OvationTixEvent]:
    """Build an ``OvationTixEvent`` from a ``Performance(<id>)`` API payload.

    Returns ``None`` when the payload is missing the identifiers required to
    deep-link back to OvationTix (production id, performance id, start date).
    Sections and availability are forwarded verbatim so the same
    ``OvationTixEvent.to_show`` path used by the production-list flow can
    extract per-tier pricing.
    """
    if not isinstance(performance_data, dict):
        return None

    production = performance_data.get("production") or {}
    if not isinstance(production, dict):
        return None

    perf_id = performance_data.get("id")
    production_id = production.get("id")
    start_date = performance_data.get("startDate")
    if perf_id is None or production_id is None or not start_date:
        return None

    production_name = (
        production.get("productionName")
        or production.get("supertitle")
        or default_name
    )

    tickets_available = bool(performance_data.get("ticketsAvailable", False))
    available_to_purchase = bool(performance_data.get("availableToPurchaseOnWeb", False))
    sections = performance_data.get("sections") or []
    if not isinstance(sections, list):
        sections = []

    event_url = (
        f"https://ci.ovationtix.com/{client_id}/production/{production_id}"
        f"?performanceId={perf_id}"
    )

    return OvationTixEvent(
        production_id=str(production_id),
        performance_id=str(perf_id),
        production_name=production_name,
        start_date=start_date,
        tickets_available=tickets_available and available_to_purchase,
        event_url=event_url,
        description=production.get("description"),
        sections=sections,
    )


def is_comedy_relevant(production_name: Optional[str], description: Optional[str]) -> bool:
    """Return ``True`` when production text carries an unambiguous stand-up
    signal.

    Patchogue's calendar mixes stand-up tours (Leslie Jones, Ben Bankas) with
    musicals (Little Shop of Horrors), concerts (Blue Öyster Cult), and
    Christian rock (Amy Grant). A bare ``comedy`` keyword catches the musical,
    so we deliberately require the stronger stand-up vocabulary.
    """
    parts: List[str] = []
    if production_name:
        parts.append(production_name)
    if description:
        parts.append(_HTML_TAG_RE.sub(" ", html_unescape.unescape(description)))
    haystack = " ".join(parts)
    if not haystack.strip():
        return False
    return any(marker.search(haystack) for marker in _COMEDY_MARKERS)
