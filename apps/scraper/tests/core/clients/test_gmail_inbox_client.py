"""Unit tests for EmailInboxClient against a mocked Gmail API."""

import base64

import pytest

from laughtrack.core.clients.gmail import client as gmail_module
from laughtrack.core.clients.gmail.client import EmailInboxClient, GmailMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _b64(text: str) -> str:
    """Return a URL-safe base64 encoding of *text*."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def _make_message(
    msg_id: str = "MSG1",
    thread_id: str = "THREAD1",
    subject: str = "Hello",
    sender: str = "user@example.com",
    date: str = "Mon, 1 Jan 2026 00:00:00 +0000",
    snippet: str = "snippet text",
    html: str = "<p>body</p>",
    text: str = "body",
) -> dict:
    """Build a minimal Gmail API message dict (multipart/alternative)."""
    return {
        "id": msg_id,
        "threadId": thread_id,
        "snippet": snippet,
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": date},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64(text)},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": _b64(html)},
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def silence_logging(monkeypatch):
    monkeypatch.setattr(gmail_module.Logger, "debug", lambda *a, **k: None)


@pytest.fixture
def client_with_mock_service(monkeypatch):
    """Return an EmailInboxClient whose _build_service is replaced with a factory."""

    def factory(mock_service):
        c = EmailInboxClient.__new__(EmailInboxClient)
        c._client_id = "CLIENT_ID"
        c._client_secret = "CLIENT_SECRET"
        c._refresh_token = "REFRESH_TOKEN"
        c._service = mock_service
        return c

    return factory


# ---------------------------------------------------------------------------
# Credential loading tests (criterion 231 / 234)
# ---------------------------------------------------------------------------


def test_credentials_loaded_from_env_vars(monkeypatch):
    """EmailInboxClient reads credentials exclusively from env vars."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "my_client_id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "my_client_secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "my_refresh_token")

    c = EmailInboxClient()

    assert c._client_id == "my_client_id"
    assert c._client_secret == "my_client_secret"
    assert c._refresh_token == "my_refresh_token"


def test_credentials_default_to_empty_string_when_missing(monkeypatch):
    """Missing env vars default to empty string, not hardcoded values."""
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)

    c = EmailInboxClient()

    assert c._client_id == ""
    assert c._client_secret == ""
    assert c._refresh_token == ""


def test_build_service_passes_env_credentials_to_google(monkeypatch):
    """_build_service passes client_id/client_secret/refresh_token from env vars to Google."""
    import sys
    import types

    captured = {}

    class FakeCredentials:
        def __init__(self, *, token, refresh_token, client_id, client_secret, token_uri):
            captured["client_id"] = client_id
            captured["client_secret"] = client_secret
            captured["refresh_token"] = refresh_token

        def refresh(self, request):
            pass

    class FakeRequest:
        pass

    def fake_build(service, version, credentials):
        captured["service_built"] = True
        return object()

    # Inject fake google modules into sys.modules so the lazy imports inside
    # _build_service resolve without the real google-auth package installed.
    fake_google = types.ModuleType("google")
    fake_oauth2 = types.ModuleType("google.oauth2")
    fake_oauth2_creds = types.ModuleType("google.oauth2.credentials")
    fake_oauth2_creds.Credentials = FakeCredentials
    fake_auth = types.ModuleType("google.auth")
    fake_auth_transport = types.ModuleType("google.auth.transport")
    fake_auth_transport_requests = types.ModuleType("google.auth.transport.requests")
    fake_auth_transport_requests.Request = FakeRequest
    fake_apiclient = types.ModuleType("googleapiclient")
    fake_discovery = types.ModuleType("googleapiclient.discovery")
    fake_discovery.build = fake_build

    for name, mod in [
        ("google", fake_google),
        ("google.oauth2", fake_oauth2),
        ("google.oauth2.credentials", fake_oauth2_creds),
        ("google.auth", fake_auth),
        ("google.auth.transport", fake_auth_transport),
        ("google.auth.transport.requests", fake_auth_transport_requests),
        ("googleapiclient", fake_apiclient),
        ("googleapiclient.discovery", fake_discovery),
    ]:
        monkeypatch.setitem(sys.modules, name, mod)

    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")

    c = EmailInboxClient()
    c._build_service()

    assert captured["client_id"] == "cid"
    assert captured["client_secret"] == "csecret"
    assert captured["refresh_token"] == "rtoken"
    assert captured["service_built"] is True


# ---------------------------------------------------------------------------
# list_unread_emails (criterion 232)
# ---------------------------------------------------------------------------


def test_list_unread_emails_uses_correct_query(client_with_mock_service):
    """list_unread_emails builds the correct Gmail query for the sender domain."""
    queries_used = []

    class FakeMessages:
        def list(self, userId, q):
            queries_used.append(q)

            class FakeExecute:
                def execute(self):
                    return {"messages": []}

            return FakeExecute()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    c = client_with_mock_service(FakeService())
    result = c.list_unread_emails("ticketmaster.com")

    assert queries_used == ["is:unread from:@ticketmaster.com"]
    assert result == []


def test_list_unread_emails_fetches_each_message(client_with_mock_service):
    """list_unread_emails calls fetch_email for each returned message ID."""
    raw = [{"id": "M1"}, {"id": "M2"}]
    fetched_ids = []

    class FakeMessages:
        def list(self, userId, q):
            class FakeExecute:
                def execute(self):
                    return {"messages": raw}

            return FakeExecute()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    c = client_with_mock_service(FakeService())

    # Override fetch_email to capture calls
    def fake_fetch(message_id):
        fetched_ids.append(message_id)
        return GmailMessage(
            message_id=message_id,
            thread_id="T",
            subject="S",
            sender="s@example.com",
            date="d",
            snippet="snip",
        )

    c.fetch_email = fake_fetch

    emails = c.list_unread_emails("example.com")

    assert fetched_ids == ["M1", "M2"]
    assert len(emails) == 2
    assert emails[0].message_id == "M1"
    assert emails[1].message_id == "M2"


def test_list_unread_emails_skips_failed_fetches(client_with_mock_service):
    """list_unread_emails silently skips messages that fail to fetch (None)."""
    raw = [{"id": "M1"}, {"id": "M2"}]

    class FakeMessages:
        def list(self, userId, q):
            class FakeExecute:
                def execute(self):
                    return {"messages": raw}

            return FakeExecute()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    c = client_with_mock_service(FakeService())

    def fake_fetch(message_id):
        if message_id == "M1":
            return None  # simulated failure
        return GmailMessage(message_id=message_id, thread_id="T", subject="S", sender="s@e.com", date="d", snippet="")

    c.fetch_email = fake_fetch

    emails = c.list_unread_emails("example.com")

    assert len(emails) == 1
    assert emails[0].message_id == "M2"


# ---------------------------------------------------------------------------
# fetch_email (criterion 233)
# ---------------------------------------------------------------------------


def test_fetch_email_returns_correct_metadata(client_with_mock_service):
    """fetch_email maps Gmail API response fields to GmailMessage correctly."""
    msg_data = _make_message(
        msg_id="ABC",
        thread_id="TABC",
        subject="Comedy Night",
        sender="club@example.com",
        date="Fri, 1 Jan 2026 20:00:00 +0000",
        snippet="Join us for...",
        html="<h1>Comedy</h1>",
        text="Comedy",
    )

    class FakeMessages:
        def get(self, userId, id, format):
            class FakeExecute:
                def execute(self):
                    return msg_data

            return FakeExecute()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    c = client_with_mock_service(FakeService())
    email = c.fetch_email("ABC")

    assert email is not None
    assert email.message_id == "ABC"
    assert email.thread_id == "TABC"
    assert email.subject == "Comedy Night"
    assert email.sender == "club@example.com"
    assert email.date == "Fri, 1 Jan 2026 20:00:00 +0000"
    assert email.snippet == "Join us for..."
    assert email.html_body == "<h1>Comedy</h1>"
    assert email.text_body == "Comedy"


def test_fetch_email_returns_none_on_api_error(client_with_mock_service):
    """fetch_email returns None when the API raises an exception."""

    class FakeMessages:
        def get(self, userId, id, format):
            class FakeExecute:
                def execute(self):
                    raise Exception("API error")

            return FakeExecute()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeService:
        def users(self):
            return FakeUsers()

    c = client_with_mock_service(FakeService())
    result = c.fetch_email("MISSING")

    assert result is None


# ---------------------------------------------------------------------------
# _extract_bodies (multipart handling)
# ---------------------------------------------------------------------------


def test_extract_bodies_plain_only():
    c = EmailInboxClient.__new__(EmailInboxClient)
    payload = {
        "mimeType": "text/plain",
        "body": {"data": _b64("plain text")},
    }
    html, text = c._extract_bodies(payload)
    assert html is None
    assert text == "plain text"


def test_extract_bodies_html_only():
    c = EmailInboxClient.__new__(EmailInboxClient)
    payload = {
        "mimeType": "text/html",
        "body": {"data": _b64("<p>html</p>")},
    }
    html, text = c._extract_bodies(payload)
    assert html == "<p>html</p>"
    assert text is None


def test_extract_bodies_multipart_alternative():
    c = EmailInboxClient.__new__(EmailInboxClient)
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("plain")}},
            {"mimeType": "text/html", "body": {"data": _b64("<p>html</p>")}},
        ],
    }
    html, text = c._extract_bodies(payload)
    assert html == "<p>html</p>"
    assert text == "plain"


def test_extract_bodies_nested_multipart():
    c = EmailInboxClient.__new__(EmailInboxClient)
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("nested plain")}},
                    {"mimeType": "text/html", "body": {"data": _b64("<p>nested html</p>")}},
                ],
            }
        ],
    }
    html, text = c._extract_bodies(payload)
    assert html == "<p>nested html</p>"
    assert text == "nested plain"


# ---------------------------------------------------------------------------
# _decode_body
# ---------------------------------------------------------------------------


def test_decode_body_valid():
    encoded = _b64("hello world")
    assert EmailInboxClient._decode_body(encoded) == "hello world"


def test_decode_body_empty_returns_none():
    assert EmailInboxClient._decode_body("") is None


def test_decode_body_none_returns_none():
    assert EmailInboxClient._decode_body(None) is None


def test_decode_body_invalid_returns_none():
    # Pass something that cannot be decoded as UTF-8 after base64 decode
    # Use latin-1 encoded bytes that are invalid UTF-8 as base64
    invalid = base64.urlsafe_b64encode(b"\xff\xfe").decode("ascii")
    # Should return None because UTF-8 decoding will fail
    result = EmailInboxClient._decode_body(invalid)
    assert result is None
