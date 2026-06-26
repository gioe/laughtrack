"""Dojour showing extraction from user_feed API responses."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.dojour import DojourEvent
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class DojourExtractor:
    """Converts raw Dojour ``user_feed`` results into DojourEvent showings."""

    @staticmethod
    def extract_events(
        results: List[Dict[str, Any]],
        default_timezone: str = "America/Chicago",
        now: Optional[datetime] = None,
    ) -> List[DojourEvent]:
        """Flatten each event's ``upcoming_showing_set`` into one DojourEvent
        per showing.

        Each feed row is an event whose ``upcoming_showing_set`` lists every
        upcoming showtime; we emit one showing each so distinct seatings persist
        as separate Shows. Past showings (start before ``now``) are dropped so
        re-runs only surface upcoming shows. When an event carries no
        ``upcoming_showing_set`` we fall back to the row's own instance-level
        ``start_dt``.
        """
        reference = now or datetime.now(timezone.utc)
        results_out: List[DojourEvent] = []
        for row in results or []:
            if not isinstance(row, dict):
                continue
            event = row.get("event")
            if not isinstance(event, dict):
                continue

            title = (event.get("title") or "").strip()
            absolute_url = event.get("absolute_url") or ""
            if not title or not absolute_url:
                continue
            if event.get("cancelled") is True:
                continue

            showings = event.get("upcoming_showing_set")
            if not isinstance(showings, list) or not showings:
                # Fall back to the row's own instance-level showing.
                showings = [row]

            for showing in showings:
                parsed = DojourExtractor._parse_showing(showing, event, default_timezone, reference)
                if parsed is not None:
                    results_out.append(parsed)
        return results_out

    @staticmethod
    def _parse_showing(
        showing: Any,
        event: Dict[str, Any],
        default_timezone: str,
        reference: datetime,
    ) -> Optional[DojourEvent]:
        if not isinstance(showing, dict):
            return None
        start_dt = showing.get("start_dt")
        if not start_dt:
            return None

        tz_name = showing.get("timezone") or default_timezone

        # Drop past showings (Dojour's "upcoming" set is usually clean, but a
        # row-level fallback or a stale cache can carry past dates). Localize a
        # naive start to the showing's timezone first so a colon-/offset-less
        # date is still comparable (and dropped) rather than slipping through.
        try:
            parsed_start = DateTimeUtils.parse_datetime_with_timezone(str(start_dt), tz_name)
        except (ValueError, TypeError):
            return None
        if parsed_start < reference:
            return None

        return DojourEvent(
            event_id=str(event.get("id") or ""),
            title=(event.get("title") or "").strip(),
            start_dt=str(start_dt),
            absolute_url=event.get("absolute_url") or "",
            showings_url=event.get("call_to_action_url") or None,
            description=event.get("description") or None,
            min_price_cents=DojourExtractor._min_price_cents(showing.get("offer")),
            timezone_name=tz_name,
        )

    @staticmethod
    def _min_price_cents(offer: Any) -> Optional[int]:
        """Lowest active option price (in cents) across the showing's offer."""
        if not isinstance(offer, dict):
            return None
        prices: List[int] = []
        for option in offer.get("option_set") or []:
            if not isinstance(option, dict):
                continue
            if option.get("active") is False:
                continue
            price = option.get("price")
            if isinstance(price, int) and price >= 0:
                prices.append(price)
        return min(prices) if prices else None
