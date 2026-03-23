"""
SeatEngine v3 GraphQL extractor.

Converts the raw GraphQL eventsList response into a flat list of
(event, show) dicts — one per show instance — ready for the transformer.
"""

from typing import Any, Dict, List

from laughtrack.foundation.models.types import JSONDict

# Pagination note (verified 2026-03-22 via GraphQL introspection):
# The eventsList query has NO limit/offset/cursor arguments — the schema exposes
# only: endDate, search, startDate, status, talentId, venueUuid.
# The EventsList return type has no pageInfo or hasNextPage fields, only:
#   events, statuses, totalCount (totalCount returns null in practice).
# The API performs a full dump in a single response. At 147 events for The Comedy
# Studio, no truncation was observed. Pagination is not needed.
_GRAPHQL_QUERY = """
query GetEvents($venueUuid: UUID4!) {
    eventsList(venueUuid: $venueUuid) {
        events {
            uuid
            name
            status
            soldOut
            page { path }
            talents { name }
            shows {
                uuid
                startDateTime
                soldOut
                status
                inventories { uuid title name price active }
            }
        }
    }
}
"""


class SeatEngineV3Extractor:
    """Converts SeatEngine v3 GraphQL response into flat (event, show) dicts."""

    @staticmethod
    def build_query_payload(venue_uuid: str) -> Dict[str, Any]:
        return {
            "query": _GRAPHQL_QUERY,
            "variables": {"venueUuid": venue_uuid},
        }

    @staticmethod
    def flatten_events(graphql_response: JSONDict, base_url: str) -> List[JSONDict]:
        """
        Flatten GraphQL eventsList into one dict per (event, show) pair.

        Only UPCOMING shows on non-CANCELLED events are included.

        Args:
            graphql_response: The full parsed JSON from the v3 GraphQL endpoint.
            base_url: The venue's scraping_url (e.g. "https://www.thecomedystudio.com"),
                      used to construct show page URLs.

        Returns:
            List of flat dicts, each representing one Show to be scraped.
        """
        events_list = (
            graphql_response.get("data", {})
            .get("eventsList", {})
            .get("events", [])
        )
        records: List[JSONDict] = []
        for event in events_list:
            if event.get("status") in ("CANCELLED", "PAST"):
                continue
            page_path = (event.get("page") or {}).get("path", "")
            show_page_url = base_url.rstrip("/") + page_path if page_path else base_url
            talents = [t.get("name", "") for t in event.get("talents", []) if t.get("name")]

            for show in event.get("shows", []):
                if show.get("status") not in ("UPCOMING", "ON_SALE"):
                    continue
                records.append(
                    {
                        "event_uuid": event.get("uuid"),
                        "event_name": event.get("name"),
                        "show_page_url": show_page_url,
                        "show_uuid": show.get("uuid"),
                        "start_datetime": show.get("startDateTime"),
                        "sold_out": event.get("soldOut", False) or show.get("soldOut", False),
                        "show_status": show.get("status"),
                        "talents": talents,
                        "inventories": show.get("inventories", []),
                    }
                )
        return records
