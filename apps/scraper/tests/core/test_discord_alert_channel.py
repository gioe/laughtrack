import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from gioe_libs.alerting import Alert, AlertSeverity, DiscordAlertChannel


@pytest.fixture
def alert():
    return Alert(
        title="Test Alert",
        message="Something went wrong",
        severity=AlertSeverity.HIGH,
        metadata={"club_id": 5},
    )


@pytest.fixture
def channel():
    return DiscordAlertChannel(webhook_url="https://discord.com/api/webhooks/test")


def _mock_urlopen():
    """Context manager mock that succeeds silently (Discord returns 204 No Content)."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _capture_urlopen():
    """Returns (mock_fn, captured_requests) where captured_requests is populated on call."""
    captured = []

    def mock_fn(req, timeout=None, **kwargs):
        captured.append(req)
        return _mock_urlopen()

    return mock_fn, captured


def test_send_returns_true_on_success(alert, channel):
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        result = channel.send(alert)
    assert result is True


def test_send_returns_false_on_http_error(alert, channel):
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(None, 400, "Bad Request", {}, None),
    ):
        result = channel.send(alert)
    assert result is False


def test_send_returns_false_on_exception(alert, channel):
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        result = channel.send(alert)
    assert result is False


def test_send_payload_uses_discord_embed_format(alert, channel):
    mock_fn, captured = _capture_urlopen()
    with patch("urllib.request.urlopen", side_effect=mock_fn):
        channel.send(alert)

    payload = json.loads(captured[0].data.decode())
    assert "embeds" in payload
    assert "attachments" not in payload
    embed = payload["embeds"][0]
    assert embed["color"] == 0xFF8800  # HIGH color
    assert "title" in embed
    assert "description" in embed


def test_send_omits_fields_when_no_metadata(channel):
    no_meta_alert = Alert(
        title="No Meta",
        message="desc",
        severity=AlertSeverity.LOW,
        metadata={},
    )
    mock_fn, captured = _capture_urlopen()
    with patch("urllib.request.urlopen", side_effect=mock_fn):
        channel.send(no_meta_alert)

    embed = json.loads(captured[0].data.decode())["embeds"][0]
    assert "fields" not in embed


def test_send_includes_fields_when_metadata_present(alert, channel):
    mock_fn, captured = _capture_urlopen()
    with patch("urllib.request.urlopen", side_effect=mock_fn):
        channel.send(alert)

    embed = json.loads(captured[0].data.decode())["embeds"][0]
    assert "fields" in embed
    field_names = [f["name"] for f in embed["fields"]]
    assert "club_id" in field_names


def test_send_with_long_message_passes_full_content_to_discord(channel):
    """gioe_libs does not truncate; callers are responsible for length limits."""
    long_message = "x" * 3000
    long_alert = Alert(
        title="Long Alert",
        message=long_message,
        severity=AlertSeverity.LOW,
        metadata={},
    )
    mock_fn, captured = _capture_urlopen()
    with patch("urllib.request.urlopen", side_effect=mock_fn):
        result = channel.send(long_alert)

    assert result is True
    embed = json.loads(captured[0].data.decode())["embeds"][0]
    # gioe_libs passes the message through as-is; Discord may reject >2048 chars
    assert embed["description"] == long_message
