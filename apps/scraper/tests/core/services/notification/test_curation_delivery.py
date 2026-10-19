"""Delivery-boundary regression: stale candidates cannot bypass current curation."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import pytest
from laughtrack.core.services.notification import service as module


@pytest.mark.parametrize("available", [True, False])
def test_show_delivery_checks_all_queued_performers_and_current_alias_membership(
    monkeypatch, available
):
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = (1,) if available else None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def connection():
        yield conn

    monkeypatch.setattr(module, "get_connection", connection)
    assert (
        module.ComedianArrivalNotificationService()._show_is_public(42, ["a", "b"])
        is available
    )
    sql, params = cursor.execute.call_args.args
    assert params == (["a", "b"], 42, ["a", "b"])
    assert "curation_comedian_policy" in sql and "policy.disposition='approved'" in sql
    assert "parent_comedian_id=m.id" in sql and "NOT EXISTS" in sql


@pytest.mark.parametrize("kind", ["show", "youtube"])
def test_policy_outage_holds_delivery(monkeypatch, kind):
    def unavailable():
        raise RuntimeError("policy store unavailable")

    monkeypatch.setattr(module, "get_connection", unavailable)
    if kind == "show":
        assert (
            module.ComedianArrivalNotificationService()._show_is_public(42, ["a"])
            is False
        )
    else:
        assert module.YouTubeLiveNotificationService()._comedian_is_public("a") is False


def test_youtube_block_after_fetch_prevents_recording_and_sending():
    service = module.YouTubeLiveNotificationService()
    row = dict(
        event_id=1,
        user_id="user",
        comedian_uuid="a",
        comedian_name="A",
        youtube_channel_id="channel",
        youtube_video_id="video",
        video_url="https://youtube.com/watch?v=video",
        push_token_id=1,
        push_token="token",
        push_platform="ios",
    )
    with patch.object(service, "_is_global_enabled", return_value=True), patch.object(
        service, "_fetch_candidates", return_value=[row]
    ), patch.object(service, "_comedian_is_public", return_value=False), patch.object(
        service, "_record_notification"
    ) as record, patch.object(
        service, "_send_push_notification"
    ) as send:
        result = service.run()
    assert result["push_sent"] == 0
    record.assert_not_called()
    send.assert_not_called()
