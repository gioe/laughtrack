"""Coral Gables Comedy Club event extractor for Square Online products API."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.coral_gables_comedy_club import (
    CoralGablesComedyClubEvent,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger

_AMP_SPLIT_RE = re.compile(r"\s*&\s*")


class CoralGablesComedyClubEventExtractor:
    """Parse Square Online products API JSON into event objects.

    The API returns products of type ``event`` with show details nested under
    ``product_type_details``:

    .. code-block:: json

        {
          "data": [
            {
              "name": "Larry Reeb & Dan Turco",
              "product_type_details": {
                "start_date": "2026-04-11",
                "start_time": "8:00 PM"
              },
              "site_link": "product/larry-reeb-dan-turco/18",
              "price": {"regular": 2500, ...},
              "badges": {"out_of_stock": false}
            }
          ]
        }
    """

    @staticmethod
    def parse_products(
        data: Any, logger_context: Optional[Dict] = None
    ) -> List[CoralGablesComedyClubEvent]:
        """Parse a Square Online products API response into event objects."""
        ctx = logger_context or {}
        events: List[CoralGablesComedyClubEvent] = []

        if not isinstance(data, dict):
            Logger.warn(
                f"CoralGablesExtractor: expected dict, got {type(data).__name__}",
                ctx,
            )
            return events

        products = data.get("data", [])
        if not isinstance(products, list):
            Logger.warn(
                "CoralGablesExtractor: 'data' key missing or not a list",
                ctx,
            )
            return events

        now = datetime.now(timezone.utc).date()

        for product in products:
            event = CoralGablesComedyClubEventExtractor._parse_product(
                product, now, ctx
            )
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def _parse_product(
        product: Dict[str, Any],
        today,
        ctx: Dict,
    ) -> Optional[CoralGablesComedyClubEvent]:
        """Parse a single product dict into an event, or None if invalid/past."""
        details = product.get("product_type_details", {})
        if not details:
            return None

        start_date = details.get("start_date", "")
        start_time = details.get("start_time", "")
        if not start_date or not start_time:
            Logger.warn(
                f"CoralGablesExtractor: missing date/time for product '{product.get('name', '?')}'",
                ctx,
            )
            return None

        # Skip past events
        try:
            event_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if event_date < today:
                return None
        except ValueError:
            return None

        # Skip hidden products
        if product.get("visibility") == "hidden":
            return None

        name = product.get("name", "").strip()
        if not name:
            return None

        site_link = product.get("site_link", "")

        # Extract price (in cents)
        price_info = product.get("price", {})
        price_cents = None
        if isinstance(price_info, dict):
            regular = price_info.get("regular")
            if regular is not None:
                try:
                    price_cents = int(regular)
                except (ValueError, TypeError):
                    pass

        # Sold out
        badges = product.get("badges", {})
        sold_out = bool(badges.get("out_of_stock", False))

        # Parse performers from event name (split on " & ")
        performers = [
            p.strip()
            for p in _AMP_SPLIT_RE.split(name)
            if p.strip()
        ]

        return CoralGablesComedyClubEvent(
            name=name,
            start_date=start_date,
            start_time=start_time,
            site_link=site_link,
            performers=performers,
            price_cents=price_cents,
            sold_out=sold_out,
        )
