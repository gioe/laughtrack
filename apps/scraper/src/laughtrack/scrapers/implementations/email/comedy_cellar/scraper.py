"""
Comedy Cellar email scraper.

Subclasses EmailBaseScraper to ingest venue newsletters from comedycellar.com.
The only method that needs implementation is parse_email_html(); all
Gmail I/O, deduplication, and Show transformation are handled by the base class.
"""

from datetime import datetime
from typing import List

from laughtrack.core.entities.event.email_show_event import EmailShowEvent
from laughtrack.scrapers.base.email_base_scraper import EmailBaseScraper
from laughtrack.scrapers.implementations.email.comedy_cellar.extractor import (
    ComedyCellarEmailExtractor,
)


class ComedyCellarEmailScraper(EmailBaseScraper):
    """
    Scraper that ingests Comedy Cellar venue newsletters via Gmail.

    Class attributes:
        key:           Unique scraper identifier used for deduplication bookkeeping.
        sender_domain: Gmail sender filter; only emails from this domain are processed.
    """

    key = "comedy_cellar_email"
    sender_domain = "comedycellar.com"

    def parse_email_html(
        self, html_body: str, subject: str, received_at: datetime
    ) -> List[EmailShowEvent]:
        """
        Extract show listings from a Comedy Cellar newsletter.

        Args:
            html_body:   Decoded HTML body of the email.
            subject:     Email subject line (unused; present for API compliance).
            received_at: Timestamp when the email was received (unused here).

        Returns:
            List of EmailShowEvent objects parsed from the newsletter.
        """
        extractor = ComedyCellarEmailExtractor(logger_context=self.logger_context)
        return extractor.extract(html_body)
