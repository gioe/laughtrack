"""Data model for Tessitura TNEW production-season performances.

Tessitura's newer TNEW storefronts render event listings from
``/api/products/productionseasons``. The API returns productions containing a
``performances`` array; each performance becomes one LaughTrack show.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


def _parse_tnew_datetime(value: str, timezone_name: str) -> Optional[datetime]:
    """Parse a TNEW performance datetime and localize naive values.

    Groundlings sends both ``performanceDate`` with an offset and
    ``iso8601DateString`` without one. Prefer the offset-bearing value when
    available, but support both shapes for other TNEW operators.
    """
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None

    if parsed.tzinfo is not None:
        return parsed
    try:
        return pytz.timezone(timezone_name).localize(parsed)
    except pytz.UnknownTimeZoneError:
        return pytz.timezone("America/New_York").localize(parsed)


@dataclass
class TessituraTNEWEvent(ShowConvertible):
    """A single performance from a Tessitura TNEW production-season payload."""

    title: str
    start_date_str: str
    show_page_url: str
    production_title: Optional[str] = None
    is_visible: bool = True
    is_on_sale: Optional[bool] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show, dropping incomplete, hidden, or past performances."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.is_visible or not self.title or not self.start_date_str or not self.show_page_url:
            return None

        start_dt = _parse_tnew_datetime(
            self.start_date_str, club.timezone or "America/New_York"
        )
        if start_dt is None or start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(show_page_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            room="",
            enhanced=enhanced,
        )
