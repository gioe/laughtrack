"""Tests for the notify-comedian-arrivals CLI command."""

from __future__ import annotations

from unittest.mock import patch

from laughtrack.app.commands.notify_comedian_arrivals import main


def _summary() -> dict[str, int]:
    return {
        "candidates": 0,
        "distance_filtered": 0,
        "emails_would_send": 0,
        "emails_sent": 0,
        "errors": 0,
        "push_candidates": 0,
        "push_filtered": 0,
        "push_would_send": 0,
        "push_sent": 0,
        "push_errors": 0,
    }


def test_main_passes_default_catch_up_window_to_service():
    with patch(
        "laughtrack.app.commands.notify_comedian_arrivals.ComedianArrivalNotificationService"
    ) as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.run.return_value = _summary()

        main([])

    mock_service.run.assert_called_once_with(
        radius_miles=50.0,
        discovered_within_days=7,
        dry_run=False,
    )


def test_main_accepts_discovered_within_days_override():
    with patch(
        "laughtrack.app.commands.notify_comedian_arrivals.ComedianArrivalNotificationService"
    ) as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.run.return_value = _summary()

        main(["--radius", "25", "--discovered-within-days", "3", "--dry-run"])

    mock_service.run.assert_called_once_with(
        radius_miles=25.0,
        discovered_within_days=3,
        dry_run=True,
    )
