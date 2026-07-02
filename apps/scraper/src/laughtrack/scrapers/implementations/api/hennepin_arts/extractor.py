"""Extraction helpers for Hennepin Arts."""

import re
from html import unescape
from typing import Any, Iterable, Optional

from laughtrack.core.entities.event.hennepin_arts import HennepinArtsEvent

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(value: Any) -> str:
    return " ".join(unescape(_TAG_RE.sub(" ", str(value or ""))).split())


def extract_hits(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Return Algolia hits and the reported page count from a multi-query response."""
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        return [], 0
    first = results[0]
    if not isinstance(first, dict):
        return [], 0
    hits = [hit for hit in first.get("hits", []) if isinstance(hit, dict)]
    try:
        nb_pages = int(first.get("nbPages") or 0)
    except (TypeError, ValueError):
        nb_pages = 0
    return hits, nb_pages


def slug_from_hit(hit: dict[str, Any]) -> Optional[str]:
    slug = str(hit.get("slug") or "").strip().strip("/")
    return slug or None


def _first_field_after_title(html: str, title: str) -> str:
    pattern = re.compile(
        rf'"title"\s*:\s*{re.escape(title)}\s*,\s*"([^"]+)"\s*:\s*"([^"]*)"',
        re.DOTALL,
    )
    match = pattern.search(html)
    return match.group(2) if match else ""


def _event_description(html: str) -> str:
    match = re.search(r'"description"\s*:\s*"(.+?)"\s*,\s*"artistWebsite"', html, re.DOTALL)
    return _clean(match.group(1)) if match else ""


def extract_performances_from_detail(
    html: str,
    *,
    title: str,
    slug: str,
    venue: str = "",
    base_url: str = "https://hennepinarts.org",
) -> list[HennepinArtsEvent]:
    """Extract Contentful performance entries embedded in the Nuxt payload."""
    if not html or not title or not slug:
        return []

    page_url = f"{base_url.rstrip('/')}/events/{slug.strip('/')}"
    description = _event_description(html)
    events: list[HennepinArtsEvent] = []
    seen: set[tuple[str, str]] = set()

    # The Nuxt payload is devalued: field names point at numeric array slots and
    # the actual values appear later as `"Event > ...", "YYYY-MM-DDTHH:MM",
    # "https://..."`. Keep the regex value-oriented so it survives slot churn.
    performance_re = re.compile(
        r'"(?P<label>Event\s*>\s*[^"]*?)"\s*,\s*'
        r'"(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2})"\s*,\s*'
        r'"(?P<ticket>https?://[^"]+)"',
        re.DOTALL,
    )
    for match in performance_re.finditer(html):
        label = _clean(match.group("label")).lower()
        if title.lower() not in label:
            continue
        start_date = match.group("start")
        ticket_url = match.group("ticket") or ""
        key = (start_date, ticket_url)
        if key in seen:
            continue
        seen.add(key)
        events.append(
            HennepinArtsEvent(
                title=title,
                start_date=start_date,
                show_page_url=page_url,
                ticket_url=ticket_url or None,
                venue=venue,
                description=description,
            )
        )

    # Some pages have a single event object where the performance record is not
    # prefixed with "Event >". Keep a conservative fallback for that shape.
    if not events:
        start_date = _first_field_after_title(html, "startDate")
        if start_date:
            events.append(
                HennepinArtsEvent(
                    title=title,
                    start_date=start_date,
                    show_page_url=page_url,
                    ticket_url=_first_field_after_title(html, "ticketsUrl") or None,
                    venue=venue,
                    description=description,
                )
            )

    return events


def extract_events_from_details(items: Iterable[tuple[dict[str, Any], str]]) -> list[HennepinArtsEvent]:
    events: list[HennepinArtsEvent] = []
    for hit, html in items:
        slug = slug_from_hit(hit)
        title = _clean(hit.get("name"))
        if not slug or not title:
            continue
        events.extend(
            extract_performances_from_detail(
                html,
                title=title,
                slug=slug,
                venue=_clean(hit.get("venue")),
            )
        )
    return events
