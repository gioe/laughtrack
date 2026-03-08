"""
Gotham Comedy Club email scraper.

Subclasses EmailBaseScraper to ingest venue newsletters from gothamcomedy.com.
The only method that needs implementation is parse_email_html(); all
Gmail I/O, deduplication, and Show transformation are handled by the base class.
"""

from datetime import datetime
from typing import List

from laughtrack.core.entities.event.email_show_event import EmailShowEvent
from laughtrack.scrapers.base.email_base_scraper import EmailBaseScraper
from laughtrack.scrapers.implementations.email.gotham.extractor import GothamEmailExtractor


class GothamEmailScraper(EmailBaseScraper):
    """
    Scraper that ingests Gotham Comedy Club venue newsletters via Gmail.

    Class attributes:
        key:           Unique scraper identifier used for deduplication bookkeeping.
        sender_domain: Gmail sender filter; only emails from this domain are processed.
    """

    key = "gotham_email"
    sender_domain = "gothamcomedy.com"

    def parse_email_html(
        self, html_body: str, subject: str, received_at: datetime
    ) -> List[EmailShowEvent]:
        """
        Extract show listings from a Gotham Comedy Club newsletter.

        Args:
            html_body:   Decoded HTML body of the email.
            subject:     Email subject line (unused; present for API compliance).
            received_at: Timestamp when the email was received (unused here).

        Returns:
            List of EmailShowEvent objects parsed from the newsletter.
        """
        extractor = GothamEmailExtractor(logger_context=self.logger_context)
        return extractor.extract(html_body)
