"""Data model for a single performance from the Philly Improv Theater (PHIT) Crowdwork API."""

from dataclasses import dataclass, field
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


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
    """

    name: str
    date_str: str
    timezone: str
    url: str
    cost_formatted: str = ""
    sold_out: bool = False
    description: str = ""

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
        tickets = []
        if show_url:
            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(
                    show_url,
                    price=price,
                    sold_out=self.sold_out,
                )
            )

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room="",
            supplied_tags=["improv"],
            enhanced=enhanced,
        )


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
    import re
    matches = re.findall(r"\d+(?:\.\d+)?", cost_formatted)
    if matches:
        try:
            return float(matches[0])
        except (ValueError, TypeError):
            pass
    return 0.0
