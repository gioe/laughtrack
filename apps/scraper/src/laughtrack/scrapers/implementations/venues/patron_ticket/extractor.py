"""Salesforce PatronTicket auth-config extractor and fetchEvents response parser.

PatronTicket sites render a small SPA that loads its Visualforce Remoting auth
context (per-method CSRF + JWT authorization + namespace + version) inline in the
page HTML and then calls the apexremote endpoint with that context. This module
extracts the context from the page HTML and parses the fetchEvents API response
into PatronTicketEvent objects, filtered by configured Salesforce venue IDs and
event category.
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from laughtrack.core.entities.event.patron_ticket import PatronTicketEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Per-method auth config block inlined in the PatronTicket page HTML.
_FETCH_EVENTS_CONFIG_RE = re.compile(
    r'fetchEvents","len":(\d+),"ns":"([^"]+)","ver":([\d.]+),'
    r'"csrf":"([^"]+)","authorization":"([^"]+)"'
)
_VID_RE = re.compile(r'"vid":"([^"]+)"')


class PatronTicketExtractor:
    """Parse PatronTicket fetchEvents API responses into PatronTicketEvent objects.

    The extraction flow:
      1. Parse the ticket page HTML to extract per-method auth config.
      2. Call fetchEvents via Visualforce Remoting (handled by the scraper).
      3. Filter events by category (configurable) at any of the configured
         Salesforce venue IDs (single value or list).
      4. Flatten event → instance pairs into PatronTicketEvent objects.
    """

    @staticmethod
    def extract_auth_config(html: str) -> Optional[Dict[str, Any]]:
        """Extract fetchEvents auth config from the ticket page HTML.

        Returns a dict with keys: len, ns, ver, csrf, authorization, vid — or None
        if either the per-method block or the visualforce session VID is absent
        from the page (typically signals a transient render failure upstream).
        """
        match = _FETCH_EVENTS_CONFIG_RE.search(html)
        if not match:
            return None

        vid_match = _VID_RE.search(html)
        if not vid_match:
            return None

        return {
            "len": int(match.group(1)),
            "ns": match.group(2),
            "ver": int(float(match.group(3))),
            "csrf": match.group(4),
            "authorization": match.group(5),
            "vid": vid_match.group(1),
        }

    @staticmethod
    def extract_events(
        api_response: Any,
        venue_ids: Sequence[str],
        categories: Iterable[str] = ("Comedy",),
        name_strip_suffixes: Optional[Sequence[str]] = None,
        logger_context: Optional[dict] = None,
    ) -> List[PatronTicketEvent]:
        """Parse the fetchEvents API response into comedy events at the given venues.

        Args:
            api_response: Parsed JSON from the Visualforce Remoting response.
            venue_ids: Salesforce venue IDs to filter instances on. Required —
                an empty sequence yields no events.
            categories: Event category tags to keep. An event is kept if any of
                these tokens equals one of the semicolon-separated tokens on its
                ``category`` field after per-token whitespace stripping (so the
                default ``"Comedy"`` filter matches ``"Comedy"`` and
                ``"Comedy;Stand-Up"`` but NOT ``"Tragicomedy"`` or
                ``"Comedy Music Festival"``). Pass an empty iterable (or a
                sentinel with the empty string) to disable category filtering.
            name_strip_suffixes: Trailing strings to peel off the show name when
                converting to a Show (forwarded to the PatronTicketEvent).
            logger_context: Optional logging context dict.

        Returns:
            List of PatronTicketEvent objects (may be empty).
        """
        ctx = logger_context or {}
        suffix_list = list(name_strip_suffixes or [])

        if not isinstance(api_response, list) or not api_response:
            Logger.warn("PatronTicketExtractor: empty or invalid API response", ctx)
            return []

        entry = api_response[0]
        if entry.get("statusCode") != 200:
            Logger.warn(
                f"PatronTicketExtractor: API returned status {entry.get('statusCode')}: "
                f"{(entry.get('message') or '')[:200]}",
                ctx,
            )
            return []

        events_data = entry.get("result", [])
        if not isinstance(events_data, list):
            Logger.warn("PatronTicketExtractor: result is not a list", ctx)
            return []

        venue_id_set = set(venue_ids)
        if not venue_id_set:
            Logger.warn("PatronTicketExtractor: no venue_ids configured — yielding 0 events", ctx)
            return []

        category_tokens = {c.strip() for c in categories if c and c.strip()}
        category_filter_enabled = bool(category_tokens)

        result: List[PatronTicketEvent] = []
        seen: set = set()

        for event in events_data:
            event_categories = event.get("category", "") or ""

            if category_filter_enabled:
                event_token_set = {
                    chunk.strip()
                    for chunk in event_categories.split(";")
                    if chunk.strip()
                }
                if category_tokens.isdisjoint(event_token_set):
                    continue

            event_name = event.get("name", "")
            description = event.get("detail", "")

            instances = event.get("instances") or []
            for instance in instances:
                if instance.get("venueId") not in venue_id_set:
                    continue

                instance_id = instance.get("id", "")
                if not instance_id or instance_id in seen:
                    continue
                seen.add(instance_id)

                formatted = instance.get("formattedDates", {}) or {}
                epoch_ms = formatted.get("ISO8601")
                if not epoch_ms:
                    Logger.warn(
                        f"PatronTicketExtractor: missing epoch for instance {instance_id}",
                        ctx,
                    )
                    continue

                result.append(
                    PatronTicketEvent(
                        event_name=event_name,
                        instance_name=instance.get("name", ""),
                        instance_id=instance_id,
                        epoch_ms=int(epoch_ms),
                        date_str=formatted.get("LONG_MONTH_DAY_YEAR", ""),
                        time_str=formatted.get("TIME_STRING", ""),
                        purchase_url=instance.get("purchaseUrl", ""),
                        sold_out=bool(instance.get("soldOut", False)),
                        description=description,
                        categories=event_categories,
                        name_strip_suffixes=suffix_list,
                    )
                )

        Logger.info(
            f"PatronTicketExtractor: extracted {len(result)} events at {len(venue_id_set)} venue(s)",
            ctx,
        )
        return result
