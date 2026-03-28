"""
UP Comedy Club scraper (The Second City, Chicago).

UP Comedy Club is the cabaret-style room on the 3rd floor of the Second City
complex at 230 W North Ave, Chicago.  Show data is served through The Second
City's own platform API in two steps:

Step 1 — Show discovery (collect_scraping_targets):
  GET https://platform.secondcity.com/graphql
    ?query=<getShowList>&variables={"first":300,"where":{"location":["chicago"]}}

  Response: nodes[] each with { title, uri, showAttributes.venue[].name }.
  Filter for nodes whose venue list contains "UP Comedy Club".
  For each match, construct an entityResolver URL.

Step 2 — Per-show instances (get_data):
  GET https://www.secondcity.com/api/entityResolver
    ?uri=<show_uri>&isPreview=false

  Response: { patronticketData: { patronticketData: "<base64>" } }
  Base64 decodes to JSON with an "instances" array, each containing:
    - formattedDates.ISO8601  — UTC datetime string
    - purchaseUrl              — Salesforce instance ticket URL
    - soldOut                  — 0 (available) or 1 (sold out)
    - eventName                — show title

Pipeline:
  1. collect_scraping_targets() → [entityResolver URL, ...]
  2. get_data(url)              → UPComedyClubPageData with one UPComedyClubEvent
                                   per upcoming performance instance
  3. transformation_pipeline   → UPComedyClubEvent.to_show() → Show objects
"""

import base64
import json
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.up_comedy_club import UPComedyClubEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import UPComedyClubPageData
from .transformer import UPComedyClubTransformer

_GRAPHQL_URL = "https://platform.secondcity.com/graphql"
_ENTITY_RESOLVER_BASE = "https://www.secondcity.com/api/entityResolver"

_GRAPHQL_QUERY = (
    "query getShowList($first: Int, $where: RootQueryToShowConnectionWhereArgs) {"
    " shows(first: $first, where: $where) {"
    " nodes { title uri showAttributes { venue { name } } }"
    " } }"
)

_GRAPHQL_VARIABLES = json.dumps(
    {"first": 300, "where": {"location": ["chicago"]}}
)


class UPComedyClubScraper(BaseScraper):
    """Scraper for UP Comedy Club Chicago via The Second City platform API."""

    key = "up_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(UPComedyClubTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """
        Discover UP Comedy Club shows via the Second City GraphQL API.

        Queries all Chicago shows and filters for those whose venue list
        contains "UP Comedy Club".  Returns one entityResolver URL per show.
        """
        graphql_url = (
            f"{_GRAPHQL_URL}"
            f"?query={urllib.parse.quote(_GRAPHQL_QUERY)}"
            f"&operationName=getShowList"
            f"&variables={urllib.parse.quote(_GRAPHQL_VARIABLES)}"
        )

        try:
            response = await self.fetch_json(graphql_url)
        except Exception as exc:
            Logger.error(
                f"UPComedyClubScraper: GraphQL request failed: {exc}",
                self.logger_context,
            )
            return []

        if response is None:
            Logger.warn(
                "UPComedyClubScraper: empty response from GraphQL API",
                self.logger_context,
            )
            return []

        nodes = (
            response.get("data", {}).get("shows", {}).get("nodes") or []
        )

        targets: List[str] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue

            attrs = node.get("showAttributes") or {}
            venue_list = attrs.get("venue") or []
            if isinstance(venue_list, dict):
                venue_list = [venue_list]

            venue_names = [
                v.get("name", "")
                for v in venue_list
                if isinstance(v, dict)
            ]

            if not any("UP Comedy Club" in name for name in venue_names):
                continue

            uri = node.get("uri", "")
            if not uri:
                continue

            resolver_url = (
                f"{_ENTITY_RESOLVER_BASE}"
                f"?uri={urllib.parse.quote(uri)}&isPreview=false"
            )
            targets.append(resolver_url)

        Logger.info(
            f"UPComedyClubScraper: discovered {len(targets)} UP Comedy Club show(s)",
            self.logger_context,
        )
        return targets

    async def get_data(self, url: str) -> Optional[UPComedyClubPageData]:
        """
        Fetch one show's entity resolver and extract all performance instances.

        Decodes the base64 patronticketData, then iterates the instances array
        to build one UPComedyClubEvent per upcoming performance.
        """
        try:
            response = await self.fetch_json(url)
        except Exception as exc:
            Logger.error(
                f"UPComedyClubScraper: entity resolver request failed for {url}: {exc}",
                self.logger_context,
            )
            return None

        if response is None:
            Logger.warn(
                f"UPComedyClubScraper: empty response from entity resolver: {url}",
                self.logger_context,
            )
            return None

        # The API nests patronticketData twice: response["patronticketData"]["patronticketData"]
        outer = response.get("patronticketData") or {}
        encoded = outer.get("patronticketData", "") if isinstance(outer, dict) else ""

        if not encoded:
            Logger.info(
                f"UPComedyClubScraper: no patronticketData for {url}",
                self.logger_context,
            )
            return None

        try:
            decoded_bytes = base64.b64decode(encoded + "==")
            ticket_data = json.loads(decoded_bytes.decode("utf-8"))
        except Exception as exc:
            Logger.warn(
                f"UPComedyClubScraper: failed to decode patronticketData for {url}: {exc}",
                self.logger_context,
            )
            return None

        instances = ticket_data.get("instances") or []
        if not instances:
            Logger.info(
                f"UPComedyClubScraper: no instances in patronticketData for {url}",
                self.logger_context,
            )
            return None

        events: List[UPComedyClubEvent] = []
        for inst in instances:
            if not isinstance(inst, dict):
                continue

            date_utc = (inst.get("formattedDates") or {}).get("ISO8601", "")
            ticket_url = inst.get("purchaseUrl", "")
            title = inst.get("eventName", "") or ticket_data.get("name", "")
            sold_out = bool(inst.get("soldOut", 0))

            if not date_utc or not ticket_url or not title:
                continue

            try:
                instance_dt = datetime.fromisoformat(date_utc.replace("Z", "+00:00"))
            except ValueError:
                continue
            if instance_dt < datetime.now(timezone.utc):
                continue

            events.append(
                UPComedyClubEvent(
                    title=title,
                    date_utc=date_utc,
                    ticket_url=ticket_url,
                    sold_out=sold_out,
                )
            )

        if not events:
            Logger.info(
                f"UPComedyClubScraper: no valid performance instances for {url}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"UPComedyClubScraper: extracted {len(events)} performance(s) from {url}",
            self.logger_context,
        )
        return UPComedyClubPageData(event_list=events)
