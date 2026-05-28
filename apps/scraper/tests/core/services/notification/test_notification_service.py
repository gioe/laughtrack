"""Tests for ComedianArrivalNotificationService."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from laughtrack.core.services.notification.geo import _haversine_miles
from laughtrack.core.services.notification.service import ComedianArrivalNotificationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(
    user_id: str = "user-1",
    user_email: str = "user@example.com",
    user_name: str = "Test User",
    user_zip: str = "10001",
    nearby_distance_miles: int | None = None,
    comedian_uuid: str = "comedian-uuid-1",
    comedian_name: str = "Funny Person",
    show_id: int = 42,
    show_date: object | None = None,
    show_page_url: str = "https://laugh-track.com/show/42",
    club_name: str = "The Comedy Club",
    club_address: str = "123 Main St",
    club_city: str = "New York",
    club_state: str = "NY",
    club_zip: str = "10002",
    notification_type: str = "email",
    push_token_id: str | None = None,
    push_token: str | None = None,
) -> dict:
    if show_date is None:
        show_date = datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc)
    return {
        "user_id": user_id,
        "user_email": user_email,
        "user_name": user_name,
        "user_zip": user_zip,
        "nearby_distance_miles": nearby_distance_miles,
        "comedian_uuid": comedian_uuid,
        "comedian_name": comedian_name,
        "show_id": show_id,
        "show_date": show_date,
        "show_page_url": show_page_url,
        "club_name": club_name,
        "club_address": club_address,
        "club_city": club_city,
        "club_state": club_state,
        "club_zip": club_zip,
        "notification_type": notification_type,
        "push_token_id": push_token_id,
        "push_token": push_token,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHaversineKnownDistance:
    def test_nyc_to_la(self):
        """NYC (40.7128, -74.006) to LA (34.0522, -118.2437) is ~2448 miles."""
        dist = _haversine_miles(40.7128, -74.0060, 34.0522, -118.2437)
        assert abs(dist - 2448) < 50, f"Expected ~2448 miles, got {dist:.1f}"

    def test_same_point_is_zero(self):
        dist = _haversine_miles(40.7128, -74.0060, 40.7128, -74.0060)
        assert dist == pytest.approx(0.0, abs=1e-6)


class TestRunSendsEmailForMatchingComedian:
    def test_sends_email_and_records_notification(self):
        row = _make_row(user_zip="10001", club_zip="10002")

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0  # well within 50 miles

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch(
                "laughtrack.core.services.notification.service.EmailService"
            ) as MockEmail:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["emails_sent"] == 1
        assert summary["distance_filtered"] == 0
        assert summary["errors"] == 0

        # EmailService.send_email should have been called once
        MockEmail.send_email.assert_called_once()
        sent_message = MockEmail.send_email.call_args[0][0]
        assert "Funny Person" in sent_message.subject
        assert sent_message.to_emails == "user@example.com"

        # SentNotification insert should have been recorded
        mock_record.assert_called_once_with(
            user_id="user-1",
            comedian_id="comedian-uuid-1",
            show_id=42,
            notification_type="email",
        )


class TestRunSendsPushForMatchingComedian:
    def test_sends_push_and_records_push_notification(self):
        row = _make_row(
            notification_type="push",
            push_token_id="token-row-1",
            push_token="abcdef123456",
        )

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0
        mock_push_sender = MagicMock()

        service = ComedianArrivalNotificationService(
            zip_distance=mock_zip,
            push_sender=mock_push_sender,
        )

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch.object(service, "_record_notification") as mock_record:
                summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["push_candidates"] == 1
        assert summary["push_sent"] == 1
        assert summary["push_filtered"] == 0
        assert summary["push_errors"] == 0
        mock_push_sender.send_show_notification.assert_called_once()
        payload = mock_push_sender.send_show_notification.call_args.kwargs
        assert payload["device_token"] == "abcdef123456"
        assert payload["comedian_name"] == "Funny Person"
        assert payload["club_name"] == "The Comedy Club"
        assert payload["show_id"] == 42
        assert payload["show_page_url"] == "https://laugh-track.com/show/42"
        mock_record.assert_called_once_with(
            user_id="user-1",
            comedian_id="comedian-uuid-1",
            show_id=42,
            notification_type="push",
        )

    def test_deactivates_invalid_push_token_and_counts_error(self):
        row = _make_row(
            notification_type="push",
            push_token_id="token-row-1",
            push_token="bad-token",
        )

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0
        mock_push_sender = MagicMock()
        mock_push_sender.send_show_notification.return_value = MagicMock(
            success=False,
            invalid_token=True,
            status_code=410,
            reason="Unregistered",
        )

        service = ComedianArrivalNotificationService(
            zip_distance=mock_zip,
            push_sender=mock_push_sender,
        )

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch.object(service, "_deactivate_push_token") as mock_deactivate:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["push_sent"] == 0
        assert summary["push_errors"] == 1
        mock_deactivate.assert_called_once_with(
            token_id="token-row-1",
            reason="Unregistered",
            status_code=410,
        )
        mock_record.assert_not_called()


class TestRunSkipsIfOutsideRadius:
    def test_skips_and_does_not_send(self):
        row = _make_row(user_zip="10001", club_zip="90210")

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 2800.0  # way outside 50 miles

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch(
                "laughtrack.core.services.notification.service.EmailService"
            ) as MockEmail:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["emails_sent"] == 0
        assert summary["distance_filtered"] == 1
        assert summary["errors"] == 0
        MockEmail.send_email.assert_not_called()
        mock_record.assert_not_called()

    def test_uses_profile_radius_when_smaller_than_job_default(self):
        row = _make_row(nearby_distance_miles=25)

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 40.0

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch(
                "laughtrack.core.services.notification.service.EmailService"
            ) as MockEmail:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["emails_sent"] == 0
        assert summary["distance_filtered"] == 1
        assert summary["errors"] == 0
        MockEmail.send_email.assert_not_called()
        mock_record.assert_not_called()


class TestRunSkipsIfDistanceUnknown:
    def test_skips_when_distance_is_none(self):
        row = _make_row(user_zip="00000", club_zip="99999")

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = None  # unknown zip code

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch(
                "laughtrack.core.services.notification.service.EmailService"
            ) as MockEmail:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["emails_sent"] == 0
        assert summary["distance_filtered"] == 1
        assert summary["errors"] == 0
        MockEmail.send_email.assert_not_called()
        mock_record.assert_not_called()


class TestRunRecordsSentNotification:
    def test_insert_called_with_correct_args(self):
        row = _make_row(
            user_id="user-99",
            comedian_uuid="comedian-abc",
            show_id=101,
        )

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 10.0

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch(
                "laughtrack.core.services.notification.service.EmailService"
            ):
                with patch.object(service, "_record_notification") as mock_record:
                    service.run(radius_miles=50.0, days_ahead=30)

        mock_record.assert_called_once_with(
            user_id="user-99",
            comedian_id="comedian-abc",
            show_id=101,
            notification_type="email",
        )

    def test_record_notification_uses_correct_sql_params(self):
        """_record_notification binds the notification_type channel."""
        service = ComedianArrivalNotificationService()

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cur

        with patch(
            "laughtrack.core.services.notification.service.get_connection",
            return_value=mock_conn,
        ):
            service._record_notification(
                user_id="u1",
                comedian_id="c1",
                show_id=7,
                notification_type="push",
            )

        mock_cur.execute.assert_called_once()
        sql_arg, params_arg = mock_cur.execute.call_args[0]
        # SQL should contain ON CONFLICT ... DO NOTHING
        assert "ON CONFLICT" in sql_arg
        assert "DO NOTHING" in sql_arg
        assert "notification_type" in sql_arg
        assert params_arg == ("u1", "c1", 7, "push")


class TestPushCandidateSql:
    def test_fetch_candidates_includes_push_opt_in_active_tokens_and_push_dedupe(self):
        service = ComedianArrivalNotificationService()

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cur
        mock_cur.description = []
        mock_cur.fetchall.return_value = []

        with patch(
            "laughtrack.core.services.notification.service.get_connection",
            return_value=mock_conn,
        ):
            service._fetch_candidates(days_ahead=30)

        sql_arg = mock_cur.execute.call_args[0][0]
        assert "up.push_show_notifications = true" in sql_arg
        assert "JOIN user_push_tokens upt" in sql_arg
        assert "upt.is_active = true" in sql_arg
        assert "sn.notification_type = 'push'" in sql_arg
        assert "sn.notification_type = 'email'" in sql_arg

    def test_fetch_candidates_filters_to_recently_discovered_shows(self):
        service = ComedianArrivalNotificationService()

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cur
        mock_cur.description = []
        mock_cur.fetchall.return_value = []

        with patch(
            "laughtrack.core.services.notification.service.get_connection",
            return_value=mock_conn,
        ):
            service._fetch_candidates(days_ahead=30, discovered_within_days=2)

        sql_arg = mock_cur.execute.call_args[0][0]
        assert "s2.first_discovered_at IS NOT NULL" in sql_arg
        assert "s2.first_discovered_at >= NOW() - INTERVAL '2 days'" in sql_arg


class TestRunMultipleCandidates:
    def test_sends_to_all_within_radius(self):
        row1 = _make_row(user_id="u1", show_id=1, comedian_name="Comedian A")
        row2 = _make_row(user_id="u2", show_id=2, comedian_name="Comedian B")
        row3 = _make_row(user_id="u3", show_id=3, comedian_name="Comedian C", user_zip="90210", club_zip="90211")

        mock_zip = MagicMock()
        # row1 and row2 are within radius; row3 is outside
        mock_zip.distance_miles.side_effect = [5.0, 10.0, 2800.0]

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row1, row2, row3]):
            with patch("laughtrack.core.services.notification.service.EmailService"):
                with patch.object(service, "_record_notification"):
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["candidates"] == 3
        assert summary["emails_sent"] == 2
        assert summary["distance_filtered"] == 1
        assert summary["errors"] == 0

    def test_error_on_send_increments_error_count(self):
        row = _make_row()

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch(
                "laughtrack.core.services.notification.service.EmailService"
            ) as MockEmail:
                MockEmail.send_email.side_effect = Exception("SMTP failure")
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["emails_sent"] == 0
        assert summary["errors"] == 1
        mock_record.assert_not_called()
