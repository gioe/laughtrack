"""Unit tests for EmailBaseScraper and EmailPageData."""

from datetime import datetime, timezone
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from laughtrack.core.clients.gmail.client import GmailMessage
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.base.email_base_scraper import EmailBaseScraper
from laughtrack.scrapers.base.email_page_data import EmailPageData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_club() -> Club:
    _c = Club(id=1, name='Test Club', address='', website='https://example.com', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='example.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_gmail_msg(
    msg_id: str = "MSG1",
    subject: str = "Test Subject",
    date: str = "Mon, 1 Jan 2026 00:00:00 +0000",
    html_body: str = "<p>Hello</p>",
) -> GmailMessage:
    return GmailMessage(
        message_id=msg_id,
        thread_id="T1",
        subject=subject,
        sender="noreply@example.com",
        date=date,
        snippet="snippet",
        html_body=html_body,
    )


class ConcreteEmailScraper(EmailBaseScraper):
    """Minimal concrete subclass used only in tests."""

    key = "test_email_scraper"
    sender_domain = "example.com"

    def parse_email_html(self, html_body: str, subject: str, received_at: datetime) -> List[Any]:
        return [{"html": html_body, "subject": subject}]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def club():
    return _make_club()


@pytest.fixture
def scraper(club):
    return ConcreteEmailScraper(club)


# ---------------------------------------------------------------------------
# EmailPageData tests
# ---------------------------------------------------------------------------


class TestEmailPageData:
    def test_is_transformable_with_events(self):
        pd = EmailPageData(
            html_body="<p>test</p>",
            subject="Sub",
            received_at=datetime.now(timezone.utc),
            event_list=[{"event": 1}],
        )
        assert pd.is_transformable() is True

    def test_is_transformable_empty(self):
        pd = EmailPageData(
            html_body="<p>test</p>",
            subject="Sub",
            received_at=datetime.now(timezone.utc),
            event_list=[],
        )
        assert pd.is_transformable() is False

    def test_event_list_defaults_to_empty(self):
        pd = EmailPageData(
            html_body="<p></p>",
            subject="",
            received_at=datetime.now(timezone.utc),
        )
        assert hasattr(pd, "event_list")
        assert pd.event_list == []


# ---------------------------------------------------------------------------
# EmailBaseScraper structural tests
# ---------------------------------------------------------------------------


class TestEmailBaseScraperStructure:
    def test_inherits_from_base_scraper(self, scraper):
        assert isinstance(scraper, BaseScraper)

    def test_cannot_instantiate_without_parse_email_html(self, club):
        """EmailBaseScraper itself is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            EmailBaseScraper(club)  # type: ignore[abstract]

    def test_missing_sender_domain_raises_type_error(self, club):
        """Subclasses that forget sender_domain fail immediately at construction."""
        class NoSenderDomain(EmailBaseScraper):
            key = "no_domain"
            def parse_email_html(self, html_body, subject, received_at):
                return []

        with pytest.raises(TypeError, match="sender_domain"):
            NoSenderDomain(club)

    def test_sender_domain_set_on_subclass(self, scraper):
        assert scraper.sender_domain == "example.com"

    def test_key_set_on_subclass(self, scraper):
        assert scraper.key == "test_email_scraper"


# ---------------------------------------------------------------------------
# collect_scraping_targets tests
# ---------------------------------------------------------------------------


class TestCollectScrapingTargets:
    @pytest.mark.asyncio
    async def test_returns_only_unprocessed_ids(self, scraper):
        msg1 = _make_gmail_msg("MSG1")
        msg2 = _make_gmail_msg("MSG2")
        scraper._inbox_client = MagicMock()
        scraper._inbox_client.list_unread_emails.return_value = [msg1, msg2]

        with patch.object(scraper, "_ensure_processed_table"):
            with patch.object(scraper, "_load_processed_ids", return_value={"MSG1"}):
                targets = await scraper.collect_scraping_targets()

        assert targets == ["MSG2"]
        assert "MSG2" in scraper._email_cache
        assert "MSG1" not in scraper._email_cache

    @pytest.mark.asyncio
    async def test_empty_when_all_processed(self, scraper):
        scraper._inbox_client = MagicMock()
        scraper._inbox_client.list_unread_emails.return_value = [_make_gmail_msg("MSG1")]

        with patch.object(scraper, "_ensure_processed_table"):
            with patch.object(scraper, "_load_processed_ids", return_value={"MSG1"}):
                targets = await scraper.collect_scraping_targets()

        assert targets == []

    @pytest.mark.asyncio
    async def test_all_unread_returned_when_none_processed(self, scraper):
        msgs = [_make_gmail_msg(f"MSG{i}") for i in range(3)]
        scraper._inbox_client = MagicMock()
        scraper._inbox_client.list_unread_emails.return_value = msgs

        with patch.object(scraper, "_ensure_processed_table"):
            with patch.object(scraper, "_load_processed_ids", return_value=set()):
                targets = await scraper.collect_scraping_targets()

        assert set(targets) == {"MSG0", "MSG1", "MSG2"}

    @pytest.mark.asyncio
    async def test_filters_by_sender_domain(self, scraper):
        scraper._inbox_client = MagicMock()
        scraper._inbox_client.list_unread_emails.return_value = []

        with patch.object(scraper, "_ensure_processed_table"):
            with patch.object(scraper, "_load_processed_ids", return_value=set()):
                await scraper.collect_scraping_targets()

        scraper._inbox_client.list_unread_emails.assert_called_once_with("example.com")


# ---------------------------------------------------------------------------
# get_data tests
# ---------------------------------------------------------------------------


class TestGetData:
    @pytest.mark.asyncio
    async def test_returns_email_page_data(self, scraper):
        msg = _make_gmail_msg("MSG1", html_body="<p>show info</p>")
        scraper._email_cache["MSG1"] = msg

        with patch.object(scraper, "_mark_processed"):
            result = await scraper.get_data("MSG1")

        assert result is not None
        assert isinstance(result, EmailPageData)
        assert result.html_body == "<p>show info</p>"
        assert result.subject == "Test Subject"
        assert len(result.event_list) == 1

    @pytest.mark.asyncio
    async def test_marks_processed_after_success(self, scraper):
        scraper._email_cache["MSG1"] = _make_gmail_msg("MSG1")

        with patch.object(scraper, "_mark_processed") as mock_mark:
            await scraper.get_data("MSG1")

        mock_mark.assert_called_once_with("MSG1")

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_cache(self, scraper):
        result = await scraper.get_data("UNKNOWN")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_and_marks_processed_for_no_html_body(self, scraper):
        msg = _make_gmail_msg("MSG1", html_body=None)
        scraper._email_cache["MSG1"] = msg

        with patch.object(scraper, "_mark_processed") as mock_mark:
            result = await scraper.get_data("MSG1")

        assert result is None
        mock_mark.assert_called_once_with("MSG1")

    @pytest.mark.asyncio
    async def test_parses_rfc2822_date(self, scraper):
        msg = _make_gmail_msg("MSG1", date="Thu, 5 Mar 2026 10:30:00 +0000")
        scraper._email_cache["MSG1"] = msg

        with patch.object(scraper, "_mark_processed"):
            result = await scraper.get_data("MSG1")

        assert result is not None
        assert result.received_at.year == 2026
        assert result.received_at.month == 3
        assert result.received_at.day == 5

    @pytest.mark.asyncio
    async def test_falls_back_to_utc_now_on_bad_date(self, scraper):
        msg = _make_gmail_msg("MSG1", date="not-a-date")
        scraper._email_cache["MSG1"] = msg

        before = datetime.now(timezone.utc)
        with patch.object(scraper, "_mark_processed"):
            result = await scraper.get_data("MSG1")
        after = datetime.now(timezone.utc)

        assert result is not None
        assert before <= result.received_at <= after

    @pytest.mark.asyncio
    async def test_calls_parse_email_html(self, scraper):
        msg = _make_gmail_msg("MSG1", html_body="<div>events</div>")
        scraper._email_cache["MSG1"] = msg

        with patch.object(scraper, "_mark_processed"):
            with patch.object(
                scraper, "parse_email_html", return_value=[{"parsed": True}]
            ) as mock_parse:
                result = await scraper.get_data("MSG1")

        mock_parse.assert_called_once()
        assert result is not None
        assert result.event_list == [{"parsed": True}]

    @pytest.mark.asyncio
    async def test_parse_email_html_exception_marks_processed_and_returns_none(self, scraper):
        """If parse_email_html raises, the email is still marked processed to prevent loops."""
        msg = _make_gmail_msg("MSG1", html_body="<div>bad</div>")
        scraper._email_cache["MSG1"] = msg

        with patch.object(scraper, "_mark_processed") as mock_mark:
            with patch.object(scraper, "parse_email_html", side_effect=ValueError("bad html")):
                result = await scraper.get_data("MSG1")

        assert result is None
        mock_mark.assert_called_once_with("MSG1")

    @pytest.mark.asyncio
    async def test_cache_entry_evicted_after_get_data(self, scraper):
        """get_data() pops the message from _email_cache to prevent unbounded growth."""
        msg = _make_gmail_msg("MSG1")
        scraper._email_cache["MSG1"] = msg

        with patch.object(scraper, "_mark_processed"):
            await scraper.get_data("MSG1")

        assert "MSG1" not in scraper._email_cache
