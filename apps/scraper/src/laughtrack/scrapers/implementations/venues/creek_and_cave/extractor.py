"""Creek and Cave event extractor for Punchup/Next.js calendar pages."""

import dataclasses
import json

from typing import Any, Dict, List, Optional, Tuple

from laughtrack.core.clients.punchup.extractor import PunchupExtractor
from laughtrack.core.clients.rsc.extractor import extract_push_payloads
from laughtrack.core.clients.tixologi.extractor import TixologiExtractor
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .data import CreekAndCaveShow

_SHOWS_KEY = '"shows":'


class CreekAndCaveEventExtractor:
    """Parse The Creek and The Cave's calendar page into CreekAndCaveShow objects.

    The venue rebuilt its site on the Punchup platform (Next.js App Router).
    The /calendar page server-renders the full upcoming-event list (~200 rows;
    the homepage only embeds ~25) inside ``self.__next_f.push([1, "..."])``
    streaming script chunks. Unlike the venuePageCarousel/venueShows React
    Query caches the shared :class:`PunchupExtractor` targets, the full list
    is passed as a ``"shows": [...]`` component prop in the RSC payload::

        ["$","$L19",null,{"shows":[
          {
            "id": "b87b52de-...",                    # uuid
            "title": "Word Up! Open Mic",
            "datetime": "2026-06-11T23:55:00",       # NAIVE local (club tz)
            "ticket_link": "https://event.tixologi.com/event/12297/tickets",
            "tixologi_event_id": "12297",
            "is_sold_out": false,
            "metadata_text": "FREE! ...",
            "vip_ticket_link": null,
            "show_comedians": [{"display_name": "...", "ordering": 0, ...}],
            ...                                       # venue, location, flags, ...
          }, ...
        ]}]

    Extraction strategy:
      1. Decode every push payload, scan for ``"shows":`` arrays whose rows
         look like event dicts (``ticket_link`` + ``datetime`` keys), and
         dedupe across payloads (the same row can appear in more than one
         chunk — e.g. both the component prop and a query-cache entry).
      2. Fall back to the shared :class:`PunchupExtractor` (carousel /
         venueShows query caches) if no component-prop rows are found, so a
         site-side data relayout degrades to the ~25-row embed instead of 0.
    """

    @staticmethod
    def extract_shows(html_content: str) -> List[CreekAndCaveShow]:
        """Extract show rows from the calendar page HTML.

        Args:
            html_content: Raw HTML content of the /calendar page.

        Returns:
            List of :class:`CreekAndCaveShow` objects, empty list if none found.
        """
        if not html_content:
            return []

        try:
            shows = CreekAndCaveEventExtractor._extract_from_component_props(html_content)
            if shows:
                return shows

            # Fallback: the dehydrated React Query caches (carousel/venueShows)
            # still carry a partial (~25 row) listing the shared extractor knows.
            # Drop link-less rows here too — the primary path requires
            # ticket_link, and a show without one would violate the
            # one-ticket-per-show invariant this extractor guarantees.
            punchup_shows = PunchupExtractor.extract_shows(html_content)
            return [
                CreekAndCaveShow(**{f.name: getattr(s, f.name) for f in dataclasses.fields(s)})
                for s in punchup_shows
                if s.ticket_link
            ]
        except Exception as e:
            Logger.error(f"CreekAndCaveEventExtractor: error extracting shows from HTML: {e}")
            return []

    @staticmethod
    def _extract_from_component_props(html_content: str) -> List[CreekAndCaveShow]:
        """Scan decoded push payloads for ``"shows": [...]`` event arrays."""
        shows: List[CreekAndCaveShow] = []
        seen: set = set()

        for payload in extract_push_payloads(html_content):
            for row in CreekAndCaveEventExtractor._find_event_rows(payload):
                key = CreekAndCaveEventExtractor._dedupe_key(row)
                if key in seen:
                    continue
                seen.add(key)

                show = CreekAndCaveEventExtractor._build_show(row)
                if show:
                    shows.append(show)

        return shows

    @staticmethod
    def _find_event_rows(payload: str) -> List[Dict[str, Any]]:
        """Find every ``"shows":`` array in a decoded payload and keep event rows.

        A row qualifies as an event when it is a dict carrying the event
        signature keys (``ticket_link`` and ``datetime``); other ``"shows"``
        arrays in the payload (unrelated props) are skipped by this filter.
        """
        rows: List[Dict[str, Any]] = []
        decoder = json.JSONDecoder()

        search_from = 0
        while True:
            key_idx = payload.find(_SHOWS_KEY, search_from)
            if key_idx < 0:
                break
            search_from = key_idx + len(_SHOWS_KEY)

            # Only accept an array that immediately follows the key (modulo
            # whitespace) — an unbounded find("[") could jump past a non-array
            # value (or a key occurrence inside string content) and decode an
            # unrelated array elsewhere in the payload.
            arr_start = search_from
            while arr_start < len(payload) and payload[arr_start] in " \t\r\n":
                arr_start += 1
            if arr_start >= len(payload) or payload[arr_start] != "[":
                continue

            try:
                value, _end = decoder.raw_decode(payload, arr_start)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(value, list):
                continue

            rows.extend(
                row
                for row in value
                if isinstance(row, dict) and "ticket_link" in row and "datetime" in row
            )

        return rows

    @staticmethod
    def _dedupe_key(row: Dict[str, Any]) -> Tuple:
        """Identity key for a raw event row (uuid id, else title+datetime)."""
        row_id = row.get("id")
        if row_id:
            return ("id", row_id)
        return ("title-dt", row.get("title"), row.get("datetime"))

    @staticmethod
    def _build_show(row: Dict[str, Any]) -> Optional[CreekAndCaveShow]:
        """Build a CreekAndCaveShow from a raw event row dict.

        Mirrors ``PunchupExtractor._build_punchup_show`` validation: rows
        missing a title or datetime are skipped here, and rows whose datetime
        later fails to parse are dropped by ``to_show()`` (returns None) —
        matching the old S3 extractor, which skipped rows missing date/url
        but left past-dated rows to the downstream pipeline's date filter.
        A ticket link is also required so every emitted Show carries at least
        one Ticket (the old extractor likewise skipped link-less rows).
        """
        title = (row.get("title") or "").strip()
        datetime_str = (row.get("datetime") or "").strip()
        ticket_link = (row.get("ticket_link") or "").strip()

        if not title or not datetime_str or not ticket_link:
            Logger.warn(
                "CreekAndCaveEventExtractor: skipping row missing "
                f"title/datetime/ticket_link (title={title!r}, datetime={datetime_str!r})"
            )
            return None

        ticket_reference = TixologiExtractor.normalize_ticket_reference(
            ticket_link,
            row.get("tixologi_event_id"),
        )
        return CreekAndCaveShow(
            id=row.get("id", ""),
            title=title,
            datetime_str=datetime_str,
            ticket_link=ticket_reference.ticket_url or ticket_link,
            tixologi_event_id=ticket_reference.event_id,
            is_sold_out=bool(row.get("is_sold_out", False)),
            metadata_text=row.get("metadata_text") or None,
            show_comedians=row.get("show_comedians") or [],
            vip_ticket_link=(row.get("vip_ticket_link") or "").strip() or None,
        )


__all__ = ["CreekAndCaveEventExtractor"]
