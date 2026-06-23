"""Data models for the generic FareHarbor scraper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


def parse_fareharbor_datetime(
    start_at: str, utc_start_at: Optional[str], timezone_name: str
) -> Optional[datetime]:
    """Parse FareHarbor availability timestamps into an aware local datetime."""
    if start_at:
        try:
            naive = datetime.fromisoformat(start_at.strip())
            if naive.tzinfo is not None:
                return naive
            return pytz.timezone(timezone_name).localize(naive)
        except Exception:
            pass

    if utc_start_at:
        cleaned = utc_start_at.strip()
        if cleaned.endswith("Z"):
            cleaned = f"{cleaned[:-1]}+00:00"
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            try:
                return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                return None
    return None


@dataclass
class FareHarborEvent(ShowConvertible):
    """One dated FareHarbor availability for one item."""

    title: str
    start_at: str
    utc_start_at: Optional[str]
    show_page_url: str
    price: Optional[float] = None
    description: Optional[str] = None
    sold_out: bool = False

    def to_show(
        self, club: Club, enhanced: bool = True, url: Optional[str] = None
    ) -> Optional[Show]:
        if not self.title or not self.show_page_url:
            return None

        start_dt = parse_fareharbor_datetime(
            self.start_at, self.utc_start_at, club.timezone or "America/New_York"
        )
        if start_dt is None or start_dt < datetime.now(timezone.utc):
            return None

        show_page_url = url or self.show_page_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                show_page_url, price=self.price, sold_out=self.sold_out
            )
        ]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=self.description,
            room="",
            enhanced=enhanced,
        )


@dataclass
class FareHarborPageData(EventListContainer[FareHarborEvent]):
    """Extracted FareHarbor availability events."""

    event_list: List[FareHarborEvent]
