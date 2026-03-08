"""
Email page data container for email-based scrapers.

EmailPageData holds the raw content of a scraped email and the parsed event list
produced by venue-specific parse_email_html() implementations.  It satisfies the
EventListContainer duck-type protocol so it can flow through the standard
BaseScraper transformation pipeline unchanged.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List


@dataclass
class EmailPageData:
    """
    Raw email content plus the venue-specific event objects parsed from it.

    Attributes:
        html_body:  Decoded HTML body of the email.
        subject:    Email subject line.
        received_at: Timestamp when the email was received.
        event_list: Venue-specific event objects produced by parse_email_html().
                    Populated before EmailPageData is returned from get_data().
    """

    html_body: str
    subject: str
    received_at: datetime
    event_list: List[Any] = field(default_factory=list)

    def is_transformable(self) -> bool:
        """Return True when there is at least one parsed event."""
        return len(self.event_list) > 0
