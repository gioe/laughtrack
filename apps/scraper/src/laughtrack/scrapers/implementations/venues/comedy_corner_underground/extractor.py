"""
HTML/RSC extraction for The Comedy Corner Underground StageTime pages.

StageTime (ccu.stageti.me) is a Next.js application that uses React Server
Components (RSC) streaming. Event data is embedded in the initial HTML as
self.__next_f.push([1, "<json-string>"]) segments.

Two extraction methods:

1. extract_event_slugs(html):
   Parses the venue listing page (https://ccu.stageti.me/) and returns a list
   of unique event slugs from event anchor links. StageTime serves these as
   either bare href="/e/{slug}" links (current) or legacy
   href="/v/{venue}/e/{slug}" links — both are accepted.

2. extract_event_data(html):
   Parses an individual event page (https://ccu.stageti.me/e/{slug}) and
   returns a dict with:
     - name: str
     - slug: str
     - is_open_mic: bool
     - admission_type: str ("paid", "free", "no_advance_sales")
     - occurrences: list[str]  (UTC ISO timestamps, published only)
     - timezone: str
     - ticket_url: str
     - performers: list[str]
"""

import json
import re

from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.clients.rsc.extractor import (
    extract_balanced,
    extract_push_payloads,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ComedyCornerExtractor:
    """Extracts show data from StageTime RSC-rendered HTML pages."""

    @staticmethod
    def extract_event_slugs(html: str) -> List[str]:
        """
        Extract unique event slugs from the StageTime venue listing page.

        Looks for all event anchor links — both the current bare
        href="/e/{slug}" form and the legacy href="/v/{venue}/e/{slug}" form —
        and returns their slugs in order of appearance.

        Args:
            html: Raw HTML from https://ccu.stageti.me/

        Returns:
            List of unique slug strings (e.g. ["jeremiah-coughlan", "pearl-rose"])
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        slugs: List[str] = []
        seen: set = set()

        # Match any event link ending in /e/{slug}: the current bare
        # "/e/{slug}" form and the legacy "/v/{venue}/e/{slug}" form both
        # qualify, while non-event links (e.g. /v/ccu/mic/1/signup, /v/ccu/tickets)
        # do not. StageTime dropped the /v/{venue} prefix from listing-page
        # event anchors, which silently zeroed out slug extraction (TASK-3332).
        for a in soup.find_all("a", href=re.compile(r"/e/[^/]+/?$")):
            href = a.get("href", "")
            # href format: /e/{slug} or legacy /v/{venue}/e/{slug}
            parts = href.split("/e/", 1)
            if len(parts) < 2:
                continue
            slug = parts[1].strip("/")
            if slug and slug not in seen:
                seen.add(slug)
                slugs.append(slug)

        return slugs

    @staticmethod
    def extract_event_data(html: str) -> Optional[Dict]:
        """
        Extract structured event data from a StageTime individual event page.

        Two parsing strategies are attempted, in order:
        1. ComedyEvent JSON-LD (current): StageTime now streams the schema.org
           ComedyEvent block as a deferred RSC text chunk ("T<len>,[{...}]"),
           referenced from the inline <script type="application/ld+json"> via a
           "$<id>" placeholder. Each array entry is one occurrence and carries
           name, startDate (UTC), performer, and offers.url (ticket URL).
        2. Legacy event/venue props block (older StageTime builds): the RSC tree
           embedded an {event, venue} object with event.occurrences[].

        Args:
            html: Raw HTML from https://ccu.stageti.me/e/{slug}

        Returns:
            dict with keys: name, slug, is_open_mic, admission_type, occurrences,
            timezone, ticket_url, performers — or None if extraction fails.
        """
        if not html:
            return None

        jsonld_event = ComedyCornerExtractor._extract_event_from_comedy_event_jsonld(html)
        if jsonld_event is not None:
            return jsonld_event

        event_info: Optional[Dict] = None
        jsonld_info: Optional[Dict] = None

        for decoded in extract_push_payloads(html):
            # Each push may contain multiple RSC chunks separated by newlines
            for line in decoded.strip().split("\n"):
                if not line.strip():
                    continue

                # Strip RSC chunk ID prefix (e.g. "1c:", "1d:") to get JSON
                json_match = re.match(r"^[0-9a-f]+:(\[.+\])$", line, re.DOTALL)
                if not json_match:
                    continue

                try:
                    arr = json.loads(json_match.group(1))
                except Exception:
                    continue

                if not isinstance(arr, list) or len(arr) < 4:
                    continue

                props = arr[3]
                if not isinstance(props, dict):
                    continue

                # Check for event/venue props block:
                # Structure: ["$", "div", null, {children: ["$", "$Lxx", null, {event: {...}, venue: {...}}]}]
                children = props.get("children", [])
                if (
                    isinstance(children, list)
                    and len(children) >= 4
                    and isinstance(children[3], dict)
                ):
                    child_props = children[3]
                    if (
                        "event" in child_props
                        and "venue" in child_props
                        and "occurrences" in child_props.get("event", {})
                    ):
                        event_info = {
                            "event": child_props["event"],
                            "venue": child_props["venue"],
                        }

                # Check for JSON-LD block:
                # Structure: ["$", "$Lxx", null, {"id": "event-jsonld", ..., "dangerouslySetInnerHTML": {"__html": "..."}}]
                if props.get("id") == "event-jsonld":
                    raw_html = (
                        props.get("dangerouslySetInnerHTML", {}).get("__html", "")
                    )
                    if raw_html:
                        try:
                            jsonld_info = json.loads(raw_html)
                        except Exception:
                            Logger.debug(
                                "ComedyCornerExtractor: failed to parse JSON-LD __html"
                            )

        if event_info is None:
            return None

        event = event_info.get("event", {})
        venue = event_info.get("venue", {})

        # Extract performers from JSON-LD
        performers: List[str] = []
        ticket_url = ""
        if jsonld_info:
            for p in jsonld_info.get("performer", []):
                if isinstance(p, dict) and p.get("name"):
                    performers.append(p["name"])
            offers = jsonld_info.get("offers", {})
            if isinstance(offers, dict):
                ticket_url = offers.get("url", "")
            elif isinstance(offers, list) and offers:
                ticket_url = offers[0].get("url", "") if isinstance(offers[0], dict) else ""

        # Fallback ticket URL from slug
        if not ticket_url:
            slug = event.get("slug", "")
            if slug:
                ticket_url = f"https://ccu.stageti.me/v/ccu/e/{slug}"

        # Extract published (non-sold-out) occurrences
        occurrences: List[str] = [
            occ["startTime"]
            for occ in event.get("occurrences", [])
            if isinstance(occ, dict)
            and occ.get("status") == "published"
            and occ.get("startTime")
        ]

        return {
            "name": event.get("name", ""),
            "slug": event.get("slug", ""),
            "is_open_mic": event.get("isOpenMic", False),
            "admission_type": event.get("admissionType", ""),
            "occurrences": occurrences,
            "timezone": venue.get("timezone", "America/Chicago"),
            "ticket_url": ticket_url,
            "performers": performers,
        }

    @staticmethod
    def _extract_event_from_comedy_event_jsonld(html: str) -> Optional[Dict]:
        """
        Build event data from the schema.org ComedyEvent JSON-LD payload.

        StageTime streams the ComedyEvent JSON-LD as a deferred RSC *text* chunk
        of the form ``T<hexlen>,[{...ComedyEvent...}]``. Each array entry is one
        occurrence; entries without a startDate (e.g. unpublished/sold-out
        placeholders) are skipped. Returns the same dict shape as
        ``extract_event_data`` or None when no ComedyEvent JSON-LD is present.

        The RSC flight string is concatenated across all ``__next_f.push`` calls
        before parsing: a single text chunk can contain literal newlines and can
        span multiple push payloads, so the array is located by its ``T<hexlen>,``
        marker and balanced-extracted rather than split line-by-line.
        """
        flight = "".join(extract_push_payloads(html))
        if "ComedyEvent" not in flight:
            return None

        events: List[Dict] = []
        # Deferred text chunks open with "T<hexlen>,[" — balanced-extract each
        # array and keep the ones that actually carry ComedyEvent JSON-LD.
        for marker in re.finditer(r"T[0-9a-f]+,(\[)", flight):
            array_json = extract_balanced(flight, marker.start(1), "[", "]")
            if not array_json or "ComedyEvent" not in array_json:
                continue
            try:
                payload = json.loads(array_json)
            except (json.JSONDecodeError, ValueError):
                continue
            items = payload if isinstance(payload, list) else [payload]
            events.extend(
                item
                for item in items
                if isinstance(item, dict) and item.get("@type") == "ComedyEvent"
            )

        if not events:
            return None

        name = ""
        occurrences: List[str] = []
        performers: List[str] = []
        seen_performers: set = set()
        ticket_url = ""

        for event in events:
            if not name and event.get("name"):
                name = event["name"]

            start_date = event.get("startDate")
            if start_date:
                occurrences.append(start_date)

            for performer in event.get("performer", []) or []:
                if isinstance(performer, dict):
                    performer_name = performer.get("name")
                    if performer_name and performer_name not in seen_performers:
                        seen_performers.add(performer_name)
                        performers.append(performer_name)

            if not ticket_url:
                offers = event.get("offers")
                if isinstance(offers, dict):
                    ticket_url = offers.get("url", "")
                elif isinstance(offers, list) and offers and isinstance(offers[0], dict):
                    ticket_url = offers[0].get("url", "")

        if not occurrences:
            return None

        return {
            "name": name,
            "slug": "",
            "is_open_mic": False,
            "admission_type": "",
            "occurrences": occurrences,
            "timezone": "America/Chicago",
            "ticket_url": ticket_url,
            "performers": performers,
        }
