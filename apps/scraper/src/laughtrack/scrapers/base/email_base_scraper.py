"""
Abstract base class for email-based scrapers.

EmailBaseScraper extends BaseScraper with email-specific lifecycle hooks so that
venue subclasses only need to implement parse_email_html() to participate in the
standard two-phase scraping pipeline.

Pipeline overview:
  1. collect_scraping_targets()  — lists unread Gmail messages from sender_domain,
                                   filters out already-processed IDs, caches messages.
  2. get_data(message_id)        — retrieves cached message, calls parse_email_html(),
                                   returns an EmailPageData container.
  3. transform_data(page_data)   — inherited from BaseScraper; applies the venue's
                                   transformation pipeline to page_data.event_list.

Processed message IDs are persisted in a `processed_emails` PostgreSQL table so
the same email is never ingested twice across runs.
"""

from abc import abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Set

from laughtrack.core.clients.gmail.client import EmailInboxClient, GmailMessage
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import ScrapingTarget
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.base.email_page_data import EmailPageData


class EmailBaseScraper(BaseScraper):
    """
    Abstract base class for scrapers that ingest venue emails.

    Subclasses must set the ``sender_domain`` class attribute and implement
    ``parse_email_html()``.  All other lifecycle methods are provided by this
    class and by the parent BaseScraper.

    Class attributes:
        sender_domain (str): Domain of the email sender to query, e.g.
                             ``"ticketmaster.com"``.  Must be set by every
                             concrete subclass.

    Example::

        class AcmeVenueScraper(EmailBaseScraper):
            key = "acme_venue"
            sender_domain = "acmevenue.com"

            def parse_email_html(
                self, html_body: str, subject: str, received_at: datetime
            ) -> List[AcmeEvent]:
                return AcmeEventExtractor().extract(html_body)
    """

    sender_domain: str  # Must be overridden by every concrete subclass

    def __init__(self, club: Club) -> None:
        super().__init__(club)
        if not getattr(self, "sender_domain", None):
            raise TypeError(
                f"{type(self).__name__} must set a non-empty 'sender_domain' class attribute."
            )
        self._inbox_client: EmailInboxClient = EmailInboxClient()
        # Keyed by message_id; populated in collect_scraping_targets() and evicted in get_data()
        self._email_cache: Dict[str, GmailMessage] = {}

    # ------------------------------------------------------------------
    # Processed-email tracking (PostgreSQL)
    # ------------------------------------------------------------------

    def _ensure_processed_table(self) -> None:
        """Create the processed_emails table if it does not already exist."""
        try:
            from laughtrack.adapters.db import get_connection

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS processed_emails (
                            message_id   TEXT        NOT NULL,
                            scraper_key  TEXT        NOT NULL,
                            processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            PRIMARY KEY (message_id, scraper_key)
                        )
                        """
                    )
        except Exception as exc:
            Logger.warning(
                f"[EmailBaseScraper] Could not ensure processed_emails table: {exc}. "
                "Previously processed emails may be re-ingested on this run.",
                self.logger_context,
            )

    def _load_processed_ids(self) -> Set[str]:
        """Return the set of message IDs already processed by this scraper."""
        try:
            from laughtrack.adapters.db import get_connection

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT message_id FROM processed_emails WHERE scraper_key = %s",
                        (self.key,),
                    )
                    return {row[0] for row in cur.fetchall()}
        except Exception as exc:
            Logger.debug(
                f"[EmailBaseScraper] Could not load processed IDs: {exc}",
                self.logger_context,
            )
            return set()

    def _mark_processed(self, message_id: str) -> None:
        """Persist a message ID so it is skipped on subsequent runs."""
        try:
            from laughtrack.adapters.db import get_connection

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO processed_emails (message_id, scraper_key)
                        VALUES (%s, %s)
                        ON CONFLICT (message_id, scraper_key) DO NOTHING
                        """,
                        (message_id, self.key),
                    )
        except Exception as exc:
            Logger.debug(
                f"[EmailBaseScraper] Could not mark {message_id} as processed: {exc}",
                self.logger_context,
            )

    # ------------------------------------------------------------------
    # BaseScraper lifecycle overrides
    # ------------------------------------------------------------------

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Return unprocessed Gmail message IDs filtered by sender_domain.

        Fetches all unread emails from the configured sender domain, removes
        any whose IDs are already present in ``processed_emails``, caches the
        remaining GmailMessage objects by ID, and returns the IDs as scraping
        targets.
        """
        self._ensure_processed_table()

        emails: List[GmailMessage] = self._inbox_client.list_unread_emails(self.sender_domain)
        processed: Set[str] = self._load_processed_ids()

        targets: List[ScrapingTarget] = []
        for email in emails:
            if email.message_id not in processed:
                self._email_cache[email.message_id] = email
                targets.append(email.message_id)

        Logger.debug(
            f"[EmailBaseScraper] {len(emails)} unread emails from @{self.sender_domain}, "
            f"{len(targets)} unprocessed",
            self.logger_context,
        )
        return targets

    async def get_data(self, target: ScrapingTarget) -> Optional[EventListContainer]:
        """
        Build an EmailPageData from the cached email identified by *target*.

        Calls ``parse_email_html()`` to populate ``event_list``, then marks the
        message as processed.  Returns ``None`` when no cached message exists or
        when the email has no HTML body (message is still marked processed to
        prevent infinite retries on malformed emails).

        Args:
            target: Gmail message ID returned by collect_scraping_targets().

        Returns:
            EmailPageData implementing EventListContainer, or None.
        """
        # Pop evicts the entry so the cache does not grow unboundedly.
        message: Optional[GmailMessage] = self._email_cache.pop(target, None)
        if message is None:
            Logger.debug(
                f"[EmailBaseScraper] No cached email for message_id={target}",
                self.logger_context,
            )
            return None

        if not message.html_body:
            # Mark so we do not keep retrying a text-only or empty email.
            self._mark_processed(target)
            return None

        try:
            received_at: datetime = parsedate_to_datetime(message.date)
        except Exception:
            received_at = datetime.now(timezone.utc)

        try:
            events: List[Any] = self.parse_email_html(message.html_body, message.subject, received_at)
        except Exception as parse_exc:
            Logger.error(
                f"[EmailBaseScraper] parse_email_html raised for {target}: {parse_exc}",
                self.logger_context,
            )
            self._mark_processed(target)
            return None

        page_data = EmailPageData(
            html_body=message.html_body,
            subject=message.subject,
            received_at=received_at,
            event_list=events,
        )
        self._mark_processed(target)
        return page_data

    # ------------------------------------------------------------------
    # Abstract interface for venue subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def parse_email_html(self, html_body: str, subject: str, received_at: datetime) -> List[Any]:
        """
        Parse the email HTML body into venue-specific event objects.

        Subclasses must implement this method to extract structured event data
        from the email's HTML content.  The returned objects must be compatible
        with the venue's transformation pipeline (i.e. the same event type
        that ``transform_data`` knows how to handle).

        Args:
            html_body:   Decoded HTML body of the email.
            subject:     Email subject line.
            received_at: Timestamp when the email was received.

        Returns:
            List of venue-specific event objects; may be empty.
        """
        ...
