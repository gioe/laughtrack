"""Tests for the notify-youtube-live CLI command."""

from __future__ import annotations

from unittest.mock import patch

from laughtrack.app.commands.notify_youtube_live import main


def _summary() -> dict[str, int]:
    return {
        "global_gated": 0,
        "candidates": 1,
        "push_would_send": 0,
        "push_sent": 1,
        "push_errors": 0,
        "duplicates": 0,
        "errors": 0,
    }


def test_main_passes_limit_and_dry_run_to_service():
    with patch("laughtrack.app.commands.notify_youtube_live.YouTubeLiveNotificationService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.run.return_value = _summary()

        main(["--limit", "25", "--dry-run"])

    mock_service.run.assert_called_once_with(limit=25, dry_run=True)
