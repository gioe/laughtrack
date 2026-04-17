"""
Data model for a single event scraped from a JetBook (Bubble.io) venue iframe.

JetBook is a hosted ticketing platform built on Bubble.io, embedded as an
iframe on venue websites (e.g. https://jetbook.co/o_iframe/<venue-slug>).
Upcoming events are served via Bubble's Elasticsearch proxy endpoints
(/elasticsearch/msearch) — while the POST bodies are opaque/encrypted, the
responses return plaintext JSON documents with full event fields.

Per-event detail pages live at https://jetbook.co/e/<slug>.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _parse_bubble_millis(ms: int, timezone_name: str) -> Optional[datetime]:
    """Parse a Bubble.io Unix-millisecond timestamp and localize to *timezone_name*."""
    try:
        utc_dt = datetime.fromtimestamp(ms / 1000.0, tz=pytz.utc)
        return utc_dt.astimezone(pytz.timezone(timezone_name))
    except Exception:
        return None


@dataclass
class JetBookEvent(ShowConvertible):
    """A single upcoming show scraped from a JetBook venue iframe."""

    title: str              # e.g. "Tan Sedan + Mom & Dad Are Fighting Again"
    start_time_ms: int      # Unix millisecond timestamp from parsedate_start_date
    slug: str               # Bubble slug, e.g. "tan-sedan---mom--dad-s3zb"
    description: str = ""   # description_text (may be empty)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show domain object."""
        from laughtrack.scrapers.implementations.jetbook.extractor import JetBookExtractor
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_time_ms or not self.slug:
            return None

        # JetBook is a generic multi-venue platform — rely on the club's
        # configured timezone rather than a venue-specific hardcoded default.
        # Fall back to UTC (and log) so a missing timezone produces a visible
        # anomaly rather than silently shifting times by several hours.
        tz_name = club.timezone
        if not tz_name:
            Logger.warn(
                f"JetBookEvent: club '{club.name}' has no timezone set; "
                "falling back to UTC for show date conversion"
            )
            tz_name = "UTC"
        start_dt = _parse_bubble_millis(self.start_time_ms, tz_name)
        if start_dt is None:
            return None

        ticket_url = url or JetBookExtractor.build_ticket_url(self.slug)
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            enhanced=enhanced,
        )
