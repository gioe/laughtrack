from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.infrastructure.monitoring.alerts import Alert, AlertSeverity
from laughtrack.infrastructure.monitoring.channels import SlackAlertChannel


@pytest.fixture
def alert():
    return Alert(
        id="test-1",
        title="Test Alert",
        description="Something went wrong",
        severity=AlertSeverity.HIGH,
        timestamp=datetime(2026, 3, 4, 12, 0, 0),
        source="scraper",
        metadata={"club_id": 5},
    )


@pytest.fixture
def channel():
    return SlackAlertChannel(webhook_url="https://hooks.slack.com/services/test")


def _mock_session(status: int, body: str = "ok"):
    """Build a mock curl_cffi AsyncSession: post() is an AsyncMock returning a response."""
    response = MagicMock()
    response.status_code = status
    response.text = body

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.post = AsyncMock(return_value=response)

    return session


@pytest.mark.asyncio
async def test_send_alert_returns_true_on_200(alert, channel):
    with patch("laughtrack.infrastructure.monitoring.channels.AsyncSession", return_value=_mock_session(200)):
        result = await channel.send_alert(alert)
    assert result is True


@pytest.mark.asyncio
async def test_send_alert_returns_false_on_non_200(alert, channel):
    with patch("laughtrack.infrastructure.monitoring.channels.AsyncSession", return_value=_mock_session(400, "invalid_payload")):
        result = await channel.send_alert(alert)
    assert result is False


@pytest.mark.asyncio
async def test_send_alert_returns_false_on_exception(alert, channel):
    with patch("laughtrack.infrastructure.monitoring.channels.AsyncSession", side_effect=Exception("network error")):
        result = await channel.send_alert(alert)
    assert result is False


@pytest.mark.asyncio
async def test_send_alert_payload_includes_severity_color(alert, channel):
    session = _mock_session(200)
    with patch("laughtrack.infrastructure.monitoring.channels.AsyncSession", return_value=session):
        await channel.send_alert(alert)

    call_kwargs = session.post.call_args.kwargs
    attachment = call_kwargs["json"]["attachments"][0]
    assert attachment["color"] == "#ff8800"  # HIGH color


@pytest.mark.asyncio
async def test_send_alert_omits_footer_when_no_metadata(channel):
    alert = Alert(
        id="test-2",
        title="No Meta",
        description="desc",
        severity=AlertSeverity.LOW,
        timestamp=datetime(2026, 3, 4, 12, 0, 0),
        source="scraper",
        metadata={},
    )
    session = _mock_session(200)
    with patch("laughtrack.infrastructure.monitoring.channels.AsyncSession", return_value=session):
        await channel.send_alert(alert)

    call_kwargs = session.post.call_args.kwargs
    attachment = call_kwargs["json"]["attachments"][0]
    assert "footer" not in attachment


@pytest.mark.asyncio
async def test_send_alert_includes_footer_when_metadata_present(alert, channel):
    session = _mock_session(200)
    with patch("laughtrack.infrastructure.monitoring.channels.AsyncSession", return_value=session):
        await channel.send_alert(alert)

    call_kwargs = session.post.call_args.kwargs
    attachment = call_kwargs["json"]["attachments"][0]
    assert "footer" in attachment
    assert "club_id" in attachment["footer"]
