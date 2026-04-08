"""The Lost Church event extractor for the PatronTicket fetchEvents API response."""

import re
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.lost_church import LostChurchEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Salesforce venue ID for The Lost Church San Francisco
_SF_VENUE_ID = "a0T6A000002eYckUAE"

# Regex to extract per-method auth config from the page HTML.
# Each Visualforce Remote method has its own csrf, authorization, namespace, and version.
_FETCH_EVENTS_CONFIG_RE = re.compile(
    r'fetchEvents","len":(\d+),"ns":"([^"]+)","ver":([\d.]+),'
    r'"csrf":"([^"]+)","authorization":"([^"]+)"'
)


class LostChurchEventExtractor:
    """Parse PatronTicket fetchEvents API response into LostChurchEvent objects.

    The extraction flow:
      1. Parse the ticket page HTML to extract per-method auth config
      2. Call fetchEvents via Visualforce Remoting
      3. Filter events to Comedy category at the SF venue
      4. Flatten event → instance pairs into LostChurchEvent objects
    """

    @staticmethod
    def extract_auth_config(html: str) -> Optional[Dict[str, Any]]:
        """Extract the fetchEvents method auth config from the ticket page HTML.

        Args:
            html: Raw HTML from the PatronTicket ticket page.

        Returns:
            Dict with keys: len, ns, ver, csrf, authorization, vid — or None.
        """
        match = _FETCH_EVENTS_CONFIG_RE.search(html)
        if not match:
            return None

        vid_match = re.search(r'"vid":"([^"]+)"', html)
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
        api_response: Any, logger_context: Optional[dict] = None
    ) -> List[LostChurchEvent]:
        """Parse the fetchEvents API response into comedy events at the SF venue.

        Args:
            api_response: Parsed JSON from the Visualforce Remoting response.
            logger_context: Optional logging context dict.

        Returns:
            List of LostChurchEvent objects (may be empty).
        """
        ctx = logger_context or {}

        if not isinstance(api_response, list) or not api_response:
            Logger.warn("LostChurchExtractor: empty or invalid API response", ctx)
            return []

        entry = api_response[0]
        if entry.get("statusCode") != 200:
            Logger.warn(
                f"LostChurchExtractor: API returned status {entry.get('statusCode')}: "
                f"{entry.get('message', '')[:200]}",
                ctx,
            )
            return []

        events_data = entry.get("result", [])
        if not isinstance(events_data, list):
            Logger.warn("LostChurchExtractor: result is not a list", ctx)
            return []

        result: List[LostChurchEvent] = []
        seen: set = set()

        for event in events_data:
            categories = event.get("category", "")
            if "Comedy" not in categories:
                continue

            event_name = event.get("name", "")
            description = event.get("detail", "")

            for instance in event.get("instances", []):
                # Filter to SF venue only
                if instance.get("venueId") != _SF_VENUE_ID:
                    continue

                instance_id = instance.get("id", "")
                if not instance_id or instance_id in seen:
                    continue
                seen.add(instance_id)

                formatted = instance.get("formattedDates", {})
                epoch_ms = formatted.get("ISO8601")
                if not epoch_ms:
                    Logger.warn(
                        f"LostChurchExtractor: missing epoch for instance {instance_id}",
                        ctx,
                    )
                    continue

                result.append(
                    LostChurchEvent(
                        event_name=event_name,
                        instance_name=instance.get("name", ""),
                        instance_id=instance_id,
                        epoch_ms=int(epoch_ms),
                        date_str=formatted.get("LONG_MONTH_DAY_YEAR", ""),
                        time_str=formatted.get("TIME_STRING", ""),
                        purchase_url=instance.get("purchaseUrl", ""),
                        sold_out=bool(instance.get("soldOut", False)),
                        description=description,
                        categories=categories,
                    )
                )

        Logger.info(
            f"LostChurchExtractor: extracted {len(result)} comedy events at SF venue",
            ctx,
        )
        return result
