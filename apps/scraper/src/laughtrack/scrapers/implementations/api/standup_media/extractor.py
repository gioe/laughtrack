"""StandUp Media show extraction from GetAllShows JSON responses.

The API returns one record per price section, so a single showtime appears as
multiple rows sharing one ``ShowID``. ``extract_events`` de-duplicates by
``ShowID`` (keeping the cheapest non-zero section price) and drops private
events, rows missing a usable showtime, and past showtimes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.event.standup_media import StandUpMediaEvent
from laughtrack.foundation.utilities.datetime import DateTimeUtils


class StandUpMediaExtractor:
    """Converts raw StandUp Media GetAllShows payloads to StandUpMediaEvent objects."""

    @staticmethod
    def extract_events(
        records: List[Dict[str, Any]],
        purchase_url: str,
        default_timezone: str = "America/Chicago",
    ) -> List[StandUpMediaEvent]:
        """De-duplicate section rows by ``ShowID`` into one event per showtime.

        Skips records flagged ``isprivate`` (private buyouts), rows without a
        ``ShowID`` / ``ShowTm`` / ``ComicName``, and showtimes in the past — the
        GetAllShows feed has only returned upcoming shows so far, but the
        past-date guard mirrors the do314 extractor so nightly re-runs never
        re-ingest stale showtimes if the API starts returning history. The kept
        price is the lowest positive section ``ShowPrice`` for the showtime
        (``None`` when no positive price is present).
        """
        by_show_id: Dict[str, StandUpMediaEvent] = {}
        for raw in records or []:
            if not isinstance(raw, dict):
                continue
            if raw.get("isprivate") is True:
                continue
            show_id = str(raw.get("ShowID") or "").strip()
            show_tm = (raw.get("ShowTm") or "").strip()
            name = (raw.get("ComicName") or "").strip()
            if not show_id or not show_tm or not name:
                continue
            if StandUpMediaExtractor._is_past(show_tm, default_timezone):
                continue

            price = StandUpMediaExtractor._coerce_price(raw.get("ShowPrice"))
            sold_out = StandUpMediaExtractor._coerce_soldout(raw.get("soldout"))

            existing = by_show_id.get(show_id)
            if existing is None:
                by_show_id[show_id] = StandUpMediaEvent(
                    show_id=show_id,
                    name=name,
                    start_str=show_tm,
                    purchase_url=purchase_url,
                    price=price,
                    sold_out=sold_out,
                    timezone_name=default_timezone,
                )
            else:
                # Another price section for the same showtime: keep the lowest
                # positive price; a showtime is sold out only if every section is.
                if price is not None and (existing.price is None or price < existing.price):
                    existing.price = price
                existing.sold_out = existing.sold_out and sold_out

        return list(by_show_id.values())

    @staticmethod
    def _is_past(show_tm: str, timezone: str) -> bool:
        """True when the localized showtime is strictly before now.

        Unparseable datetimes return ``False`` (kept) so a parse quirk never
        silently drops a real show — ``event.to_show`` drops it later if the
        date truly can't be resolved.
        """
        try:
            resolved = DateTimeUtils.parse_datetime_with_timezone(show_tm, timezone)
        except (ValueError, TypeError):
            return False
        return resolved < datetime.now(resolved.tzinfo)

    @staticmethod
    def _coerce_price(value: Any) -> Optional[float]:
        try:
            price = float(value)
        except (TypeError, ValueError):
            return None
        return price if price > 0 else None

    @staticmethod
    def _coerce_soldout(value: Any) -> bool:
        # API uses 0/1 (int) for the soldout flag.
        try:
            return int(value) == 1
        except (TypeError, ValueError):
            return bool(value)
