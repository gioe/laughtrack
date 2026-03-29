"""
HTML/RSC extraction for The Comedy Corner Underground StageTime pages.

StageTime (ccu.stageti.me) is a Next.js application that uses React Server
Components (RSC) streaming. Event data is embedded in the initial HTML as
self.__next_f.push([1, "<json-string>"]) segments.

Two extraction methods:

1. extract_event_slugs(html):
   Parses the venue listing page (https://ccu.stageti.me/) and returns a list
   of unique event slugs from href="/v/ccu/e/{slug}" anchor links.

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

from laughtrack.foundation.infrastructure.logger.logger import Logger


class ComedyCornerExtractor:
    """Extracts show data from StageTime RSC-rendered HTML pages."""

    # Regex to capture the content of self.__next_f.push([1, "..."]) calls.
    # The content is a JSON-encoded string containing RSC wire format data.
    _RSC_PUSH_RE = re.compile(
        r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)',
        re.DOTALL,
    )

    @staticmethod
    def extract_event_slugs(html: str) -> List[str]:
        """
        Extract unique event slugs from the StageTime venue listing page.

        Looks for all <a href="/v/ccu/e/{slug}"> links and returns their slugs
        in order of appearance.

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

        for a in soup.find_all("a", href=re.compile(r"^/v/[^/]+/e/")):
            href = a.get("href", "")
            # href format: /v/ccu/e/{slug}
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

        Parses the RSC wire format to find:
        - The event/venue props block (contains occurrences, timezone, isOpenMic)
        - The JSON-LD block (contains performer names and ticket URL)

        Args:
            html: Raw HTML from https://ccu.stageti.me/e/{slug}

        Returns:
            dict with keys: name, slug, is_open_mic, admission_type, occurrences,
            timezone, ticket_url, performers — or None if extraction fails.
        """
        if not html:
            return None

        event_info: Optional[Dict] = None
        jsonld_info: Optional[Dict] = None

        for push_content in ComedyCornerExtractor._RSC_PUSH_RE.finditer(html):
            raw = push_content.group(1)

            try:
                decoded: str = json.loads('"' + raw + '"')
            except Exception:
                continue

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
