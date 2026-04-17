"""
Extraction helpers for JetBook (Bubble.io) Elasticsearch msearch responses.

JetBook is a Bubble.io app. Its iframe endpoint
(https://jetbook.co/o_iframe/<venue-slug>) issues POST requests to
/elasticsearch/msearch and /elasticsearch/mget to resolve event lookup IDs.
The POST request bodies are encrypted by the Bubble client (opaque "z"
field), but the RESPONSES are plaintext JSON documents shaped like:

  {
    "responses": [
      {
        "hits": {
          "hits": [
            {
              "_id": "<bubble id>",
              "_source": {
                "name_text": "<title>",
                "parsedate_start_date": <unix ms>,
                "Slug": "<per-event slug>",
                "typevisible_option_typevisible": "visible" | "hidden",
                "visble_boolean": true,
                "ticket_page_visible_boolean": true,
                "description_text": "...",
                ...
              }
            },
            ...
          ]
        }
      },
      ...
    ]
  }

This module walks a list of such response bodies, filters to
visibly-bookable upcoming events, and returns JetBookEvent objects.
"""

from __future__ import annotations

import json
import time
from typing import Iterable, List, Optional

from laughtrack.core.entities.event.jetbook import JetBookEvent


def _is_bookable_event_source(source: dict) -> bool:
    """Return True if *source* looks like a bookable event record.

    Filters out venue/v2_venues/promocode/ticket/etc records that share the
    same msearch response, as well as events that are hidden or cannot be
    ticketed.
    """
    # Event records always carry a parsedate_start_date (Unix millis).
    if "parsedate_start_date" not in source:
        return False
    if not source.get("name_text"):
        return False
    if not source.get("Slug"):
        return False

    # Visibility flags set by the venue.
    if source.get("visble_boolean") is False:
        return False
    if source.get("ticket_page_visible_boolean") is False:
        return False
    typevisible = source.get("typevisible_option_typevisible")
    if typevisible and typevisible != "visible":
        return False

    return True


class JetBookExtractor:
    """Parses Bubble.io Elasticsearch msearch response bodies."""

    @staticmethod
    def parse_msearch_responses(
        response_bodies: Iterable[str],
        include_past: bool = False,
    ) -> List[JetBookEvent]:
        """Extract events from a collection of /elasticsearch/msearch bodies.

        Args:
            response_bodies: Raw JSON strings, one per captured msearch response.
            include_past: When False (default), events whose start time is
                already in the past are dropped.

        Returns:
            List of JetBookEvent — deduplicated by Bubble record ID (``_id``).
        """
        now_ms = int(time.time() * 1000) if not include_past else 0
        seen_ids: set[str] = set()
        events: List[JetBookEvent] = []

        for body in response_bodies:
            if not body:
                continue
            try:
                doc = json.loads(body)
            except Exception:
                continue

            for response in doc.get("responses", []):
                if not isinstance(response, dict):
                    continue
                hits_obj = response.get("hits", {})
                if not isinstance(hits_obj, dict):
                    continue
                hits = hits_obj.get("hits", [])
                if not isinstance(hits, list):
                    continue

                for hit in hits:
                    if not isinstance(hit, dict):
                        continue
                    source = hit.get("_source")
                    if not isinstance(source, dict):
                        continue

                    if not _is_bookable_event_source(source):
                        continue

                    start_ms = source.get("parsedate_start_date")
                    if not isinstance(start_ms, (int, float)):
                        continue
                    start_ms = int(start_ms)
                    if not include_past and start_ms < now_ms:
                        continue

                    record_id = hit.get("_id") or source.get("_id")
                    if not record_id or record_id in seen_ids:
                        continue
                    seen_ids.add(record_id)

                    title = str(source.get("name_text", "")).strip()
                    slug = str(source.get("Slug", "")).strip()
                    description = str(source.get("description_text", "") or "").strip()

                    events.append(
                        JetBookEvent(
                            title=title,
                            start_time_ms=start_ms,
                            slug=slug,
                            description=description,
                        )
                    )

        events.sort(key=lambda e: e.start_time_ms)
        return events

    @staticmethod
    def parse_single_response(body: str) -> List[JetBookEvent]:
        """Convenience wrapper for a single response body."""
        return JetBookExtractor.parse_msearch_responses([body])

    @staticmethod
    def build_ticket_url(slug: str) -> Optional[str]:
        """Build the per-event detail URL from a JetBook slug."""
        slug = (slug or "").strip()
        if not slug:
            return None
        return f"https://jetbook.co/e/{slug}"
