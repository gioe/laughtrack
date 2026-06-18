"""WooCommerce Store API event data model.

Used by the generic ``woocommerce_store_api`` scraper for WordPress + WooCommerce
venues that sell each show as a product. A product can carry several "Show Dates"
and "Show Times" attribute terms; the extractor expands the cartesian product so
each ``WoocommerceEvent`` represents exactly one showtime.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# WooCommerce "Show Dates" are MM/DD/YYYY; "Show Times" vary (6:30pm, 7pm, 19:30).
# strptime %p matches AM/PM case-insensitively, so lower-case "pm" parses.
_DATETIME_FORMATS = (
    "%m/%d/%Y %I:%M%p",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y %I%p",
    "%m/%d/%Y %I %p",
    "%m/%d/%Y %H:%M",
)
_DATE_ONLY_FORMAT = "%m/%d/%Y"


@dataclass
class WoocommerceEvent(ShowConvertible):
    """A single showtime parsed from one WooCommerce product.

    ``date_str`` is a WooCommerce "Show Dates" term (``MM/DD/YYYY``) and
    ``time_str`` a "Show Times" term (e.g. ``6:30pm``); together they resolve to
    the show datetime in the club's timezone. ``permalink`` is the product page,
    used as both the show URL and the ticket purchase URL. ``price`` is in dollars
    (``None`` when the product carried no price).
    """

    name: str
    date_str: str
    time_str: Optional[str]
    permalink: str
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this showtime to a Show, or None if the date cannot be parsed."""
        if not self.date_str:
            return None

        start_date = self._parse_show_datetime(club.timezone or "America/New_York")
        if start_date is None:
            return None

        tickets = [
            ShowFactoryUtils.create_fallback_ticket(self.permalink, price=self.price)
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=self.permalink,
            lineup=[],
            tickets=tickets,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )

    def _parse_show_datetime(self, timezone_name: str) -> Optional[datetime]:
        """Parse date_str + time_str into a timezone-aware datetime, or None."""
        tz = pytz.timezone(timezone_name)
        time_str = (self.time_str or "").strip()
        if time_str:
            combined = f"{self.date_str.strip()} {time_str}"
            for fmt in _DATETIME_FORMATS:
                try:
                    return tz.localize(datetime.strptime(combined, fmt))
                except ValueError:
                    continue
        try:
            return tz.localize(datetime.strptime(self.date_str.strip(), _DATE_ONLY_FORMAT))
        except ValueError:
            return None
