"""Data model for a single performance from the Philly Improv Theater (PHIT) Crowdwork API."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlsplit

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


def crowdwork_performance_identity(url: str, date: datetime) -> Optional[str]:
    """Identify an exact Crowdwork URL/UTC occurrence without inventing a room.

    Preserve the source URL, including query parameters: equivalence between
    aliases or date selectors is not established. Naive domain dates are UTC.
    This encoding is also used by the reviewed legacy-row backfill.
    """
    if not isinstance(url, str) or not isinstance(date, datetime):
        return None
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"crowdwork.com", "www.crowdwork.com"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.fragment
            or any(char.isspace() for char in url)
            or not re.fullmatch(r"/e/[A-Za-z0-9_-]+/?", parsed.path)
        ):
            return None
        utc_date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
        encoded = json.dumps(
            [url, utc_date.isoformat(timespec="microseconds")],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (ValueError, TypeError, OverflowError):
        return None
    return "crowdwork:" + hashlib.sha256(encoded).hexdigest()


@dataclass
class PhillyImprovShow(ShowConvertible):
    """
    A single performance instance from the Crowdwork/Fourthwall Tickets API.

    PHIT's shows (PHEST events) may have multiple performance dates. The scraper
    expands each date into a separate PhillyImprovShow so the transformer handles
    one instance per Show.

    Fields:
        name: Event title (e.g. "SPRING PHEST 2026")
        date_str: ISO-style datetime string for this specific performance
                  (e.g. "2026-05-15T19:00:00" or "2026-05-15 19:00:00")
        timezone: IANA timezone (e.g. "America/New_York")
        url: Crowdwork ticket/event page URL
        cost_formatted: Display price string (e.g. "Free", "$15")
        sold_out: True when the Crowdwork badges.spots field indicates sold out
        description: Optional HTML description body
        lineup_names: Performer names extracted from Crowdwork event page HTML
    """

    name: str
    date_str: str
    timezone: str
    url: str
    cost_formatted: str = ""
    sold_out: bool = False
    description: str = ""
    lineup_names: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this performance to a Show domain object."""
        try:
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.date_str,
                self.timezone or club.timezone,
            )
        except Exception:
            return None

        show_url = url or self.url

        price = _parse_price(self.cost_formatted)
        lineup = [Comedian(name=name) for name in self.lineup_names if name]
        tickets = []
        if show_url:
            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(
                    show_url,
                    price=price,
                    sold_out=self.sold_out,
                )
            )

        identified = club.source_metadata.get("source_performance_identity") is True
        identity = crowdwork_performance_identity(show_url, start_date) if identified else None
        if identified and identity is None:
            raise ValueError("Crowdwork performance requires a valid event URL and UTC occurrence")

        show = ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=show_url,
            lineup=lineup,
            tickets=tickets,
            description=self.description or None,
            room="",
            supplied_tags=["improv"],
            enhanced=enhanced,
        )
        if show is not None and identified:
            show.source_performance_id = identity
        return show


def _parse_price(cost_formatted: str) -> float:
    """
    Extract a numeric price from a Crowdwork cost string.

    Examples:
        "Free"  → 0.0
        "$15"   → 15.0
        "$10 – $20" → 10.0  (take the lower bound)
        ""      → 0.0
    """
    if not cost_formatted or cost_formatted.strip().lower() in ("free", ""):
        return 0.0
    matches = re.findall(r"\d+(?:\.\d+)?", cost_formatted)
    if matches:
        try:
            return float(matches[0])
        except (ValueError, TypeError):
            pass
    return 0.0
