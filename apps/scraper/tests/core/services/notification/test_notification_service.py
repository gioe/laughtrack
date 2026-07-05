"""Tests for ComedianArrivalNotificationService."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import ANY, MagicMock, patch

import pytest

from laughtrack.core.services.notification.geo import _haversine_miles
from laughtrack.core.services.notification.service import (
    ApnsPushService,
    ComedianArrivalNotificationService,
    FcmPushService,
    PushDeliveryResult,
    YouTubeLiveNotificationService,
    _build_comedian_image_url,
)

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
    club_timezone: str | None = "America/New_York",
    comedian_avatar_path: str | None = None,
    comedian_has_image: bool = False,
    notification_type: str = "email",
    push_token_id: str | None = None,
    push_token: str | None = None,
    push_platform: str | None = None,
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
        "club_timezone": club_timezone,
        "comedian_avatar_path": comedian_avatar_path,
        "comedian_has_image": comedian_has_image,
        "notification_type": notification_type,
        "push_token_id": push_token_id,
        "push_token": push_token,
        "push_platform": push_platform,
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
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
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
            notification_group_id=ANY,
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
            notification_group_id=ANY,
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


class TestPlatformRouting:
    """Sender selection is keyed on the token platform (TASK-3278)."""

    def _service(self, apns, fcm):
        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0
        return ComedianArrivalNotificationService(
            zip_distance=mock_zip,
            push_sender=apns,
            fcm_sender=fcm,
        )

    def test_android_token_routes_to_fcm_not_apns(self):
        row = _make_row(
            notification_type="push",
            push_token_id="tok-a",
            push_token="fcm-token",
            push_platform="android",
        )
        apns = MagicMock()
        fcm = MagicMock()
        fcm.send_show_notification.return_value = MagicMock(
            success=True, invalid_token=False, status_code=200, reason=None
        )
        service = self._service(apns, fcm)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch.object(service, "_record_notification"):
                summary = service.run(radius_miles=50.0, days_ahead=30)

        fcm.send_show_notification.assert_called_once()
        apns.send_show_notification.assert_not_called()
        assert fcm.send_show_notification.call_args.kwargs["device_token"] == "fcm-token"
        assert summary["push_sent"] == 1

    def test_ios_token_routes_to_apns_not_fcm(self):
        row = _make_row(
            notification_type="push",
            push_token_id="tok-i",
            push_token="apns-token",
            push_platform="ios",
        )
        apns = MagicMock()
        apns.send_show_notification.return_value = MagicMock(
            success=True, invalid_token=False, status_code=200, reason=None
        )
        fcm = MagicMock()
        service = self._service(apns, fcm)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch.object(service, "_record_notification"):
                summary = service.run(radius_miles=50.0, days_ahead=30)

        apns.send_show_notification.assert_called_once()
        fcm.send_show_notification.assert_not_called()
        assert summary["push_sent"] == 1

    def test_null_platform_falls_back_to_apns(self):
        # Legacy tokens stored before the platform column existed come back with
        # NULL platform; they must route to APNs, not FCM.
        row = _make_row(
            notification_type="push",
            push_token_id="tok-legacy",
            push_token="legacy-token",
            push_platform=None,
        )
        apns = MagicMock()
        apns.send_show_notification.return_value = MagicMock(
            success=True, invalid_token=False, status_code=200, reason=None
        )
        fcm = MagicMock()
        service = self._service(apns, fcm)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch.object(service, "_record_notification"):
                summary = service.run(radius_miles=50.0, days_ahead=30)

        apns.send_show_notification.assert_called_once()
        fcm.send_show_notification.assert_not_called()
        assert summary["push_sent"] == 1

    def test_android_fcm_invalid_token_is_deactivated(self):
        row = _make_row(
            notification_type="push",
            push_token_id="tok-a",
            push_token="dead-fcm-token",
            push_platform="android",
        )
        apns = MagicMock()
        fcm = MagicMock()
        fcm.send_show_notification.return_value = MagicMock(
            success=False, invalid_token=True, status_code=404, reason="UNREGISTERED"
        )
        service = self._service(apns, fcm)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch.object(service, "_deactivate_push_token") as mock_deactivate:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        fcm.send_show_notification.assert_called_once()
        apns.send_show_notification.assert_not_called()
        mock_deactivate.assert_called_once_with(token_id="tok-a", reason="UNREGISTERED", status_code=404)
        mock_record.assert_not_called()
        assert summary["push_errors"] == 1


class TestFcmPushServicePayload:
    """The FCM data payload matches what the Android client consumes (TASK-3278)."""

    def test_send_builds_data_only_payload_with_show_keys(self):
        service = FcmPushService(project_id="proj-123", credentials=MagicMock())
        response = MagicMock(status_code=200)

        with patch.object(service, "_access_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                result = service.send_show_notification(
                    device_token="android-token-xyz",
                    comedian_name="Funny Person",
                    show_id=42,
                    show_date=datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc),
                    club_name="The Comedy Club",
                    club_city="New York",
                    club_state="NY",
                    show_page_url="https://laugh-track.com/show/42",
                )

        assert result.success is True
        args, kwargs = client.post.call_args
        assert "/v1/projects/proj-123/messages:send" in args[0]
        assert kwargs["headers"]["authorization"] == "Bearer fake-token"

        message = kwargs["json"]["message"]
        assert message["token"] == "android-token-xyz"
        data = message["data"]
        # Keys LaughTrackMessagingService / routeFromPush read off message.data.
        assert data["showId"] == "42"  # FCM data values must be strings
        assert data["url"] == "https://laugh-track.com/show/42"
        assert data["title"] == "Funny Person is performing near you"
        # Body mirrors the in-app notification center: "{club} on {date} at {time}"
        # in the club's local time (no club_timezone here → America/New_York
        # default; 2026-04-15 20:00 UTC = Wednesday, April 15, 4:00 pm EDT).
        assert data["body"] == "The Comedy Club on Wednesday, April 15 at 4:00 pm EDT"
        assert data["showDate"] == "2026-04-15T20:00:00+00:00"
        # Data-only message: no notification block, so onMessageReceived always
        # fires (even backgrounded) and the client owns the notification UI.
        assert "notification" not in message
        # No headshot passed → no imageUrl key.
        assert "imageUrl" not in data

    def test_send_includes_image_url_in_data_for_rich_push(self):
        service = FcmPushService(project_id="proj-123", credentials=MagicMock())
        response = MagicMock(status_code=200)
        url = "https://laughtrack.b-cdn.net/comedians/assets/7/avatar.png"

        with patch.object(service, "_access_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                service.send_show_notification(
                    device_token="android-token-xyz",
                    comedian_name="Funny Person",
                    show_id=42,
                    show_date=None,
                    club_name="The Comedy Club",
                    club_city="New York",
                    club_state="NY",
                    show_page_url="https://laugh-track.com/show/42",
                    comedian_image_url=url,
                )

        data = client.post.call_args.kwargs["json"]["message"]["data"]
        # LaughTrackMessagingService reads imageUrl off message.data.
        assert data["imageUrl"] == url

    def test_send_marks_unregistered_token_invalid(self):
        service = FcmPushService(project_id="proj-123", credentials=MagicMock())
        response = MagicMock(status_code=404)
        response.json.return_value = {
            "error": {
                "code": 404,
                "status": "NOT_FOUND",
                "details": [
                    {"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": "UNREGISTERED"}
                ],
            }
        }

        with patch.object(service, "_access_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                result = service.send_show_notification(
                    device_token="dead-token",
                    comedian_name="Funny Person",
                    show_id=42,
                    show_date=None,
                    club_name="The Comedy Club",
                    club_city="New York",
                    club_state="NY",
                    show_page_url="https://laugh-track.com/show/42",
                )

        assert result.success is False
        assert result.invalid_token is True
        assert result.reason == "UNREGISTERED"

    def test_send_does_not_deactivate_on_invalid_argument(self):
        # INVALID_ARGUMENT can be a server-side request-shape bug, not a dead
        # token — it must NOT trigger deactivation (would mass-wipe healthy
        # tokens). It surfaces as a non-deactivating failure instead.
        service = FcmPushService(project_id="proj-123", credentials=MagicMock())
        response = MagicMock(status_code=400)
        response.json.return_value = {
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "details": [
                    {"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": "INVALID_ARGUMENT"}
                ],
            }
        }

        with patch.object(service, "_access_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                result = service.send_show_notification(
                    device_token="some-token",
                    comedian_name="Funny Person",
                    show_id=42,
                    show_date=None,
                    club_name="The Comedy Club",
                    club_city="New York",
                    club_state="NY",
                    show_page_url="https://laugh-track.com/show/42",
                )

        assert result.success is False
        assert result.invalid_token is False
        assert result.reason == "INVALID_ARGUMENT"

    def test_send_youtube_live_builds_data_only_payload(self):
        service = FcmPushService(project_id="proj-123", credentials=MagicMock())
        response = MagicMock(status_code=200)

        with patch.object(service, "_access_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                result = service.send_youtube_live_notification(
                    device_token="android-token-xyz",
                    comedian_id="comedian-uuid",
                    comedian_name="Jane Comic",
                    youtube_channel_id="UC-live-channel",
                    youtube_video_id="live-video",
                    video_title="Late set from the club",
                    watch_url="https://www.youtube.com/watch?v=live-video",
                )

        assert result.success is True
        message = client.post.call_args.kwargs["json"]["message"]
        assert message["token"] == "android-token-xyz"
        data = message["data"]
        assert data["type"] == "youtube_live"
        assert data["title"] == "Jane Comic is live on YouTube"
        assert data["body"] == "Late set from the club"
        assert data["comedianId"] == "comedian-uuid"
        assert data["youtubeChannelId"] == "UC-live-channel"
        assert data["youtubeVideoId"] == "live-video"
        assert data["url"] == "https://www.youtube.com/watch?v=live-video"
        assert "notification" not in message


class TestComedianImageUrl:
    """`_build_comedian_image_url` mirrors the web buildComedianImageUrls avatar precedence."""

    def test_prefers_active_asset_avatar_path(self, monkeypatch):
        monkeypatch.setenv("BUNNYCDN_CDN_HOST", "cdn.example.net")
        url = _build_comedian_image_url("comedians/assets/7/avatar.png", "Jane Doe", True)
        assert url == "https://cdn.example.net/comedians/assets/7/avatar.png"

    def test_strips_leading_slash_on_avatar_path(self, monkeypatch):
        monkeypatch.setenv("BUNNYCDN_CDN_HOST", "cdn.example.net")
        url = _build_comedian_image_url("/comedians/assets/7/avatar.png", "Jane Doe", True)
        assert url == "https://cdn.example.net/comedians/assets/7/avatar.png"

    def test_falls_back_to_legacy_name_path_when_has_image(self, monkeypatch):
        monkeypatch.setenv("BUNNYCDN_CDN_HOST", "cdn.example.net")
        url = _build_comedian_image_url(None, "Jane Doe", True)
        assert url == "https://cdn.example.net/comedians/Jane%20Doe.png"

    def test_none_when_no_asset_and_no_legacy_image(self, monkeypatch):
        monkeypatch.setenv("BUNNYCDN_CDN_HOST", "cdn.example.net")
        assert _build_comedian_image_url(None, "Jane Doe", False) is None

    def test_defaults_cdn_host_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("BUNNYCDN_CDN_HOST", raising=False)
        url = _build_comedian_image_url("comedians/assets/7/avatar.png", "Jane Doe", True)
        assert url == "https://laughtrack.b-cdn.net/comedians/assets/7/avatar.png"


class TestApnsPushServicePayload:
    def test_send_show_body_matches_notification_center(self):
        # The push body must read like the in-app notification center subtitle:
        # "{club} on {date} at {time}" in the club's local time (lowercase am/pm,
        # tz abbr), NOT the old "{club} in {city}, {state}". The club timezone must thread
        # through — a Los Angeles club renders Pacific time, not Eastern.
        service = ApnsPushService(
            team_id="TEAM12345",
            key_id="KEYID67890",
            private_key_pem="unused",
            bundle_id="com.example.app",
            use_sandbox=True,
        )
        response = MagicMock(status_code=200)

        with patch.object(service, "_auth_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                result = service.send_show_notification(
                    device_token="apns-token",
                    comedian_name="Funny Person",
                    show_id=42,
                    show_date=datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc),
                    club_name="The Laugh Cellar",
                    club_city="Los Angeles",
                    club_state="CA",
                    show_page_url="https://laugh-track.com/show/42",
                    club_timezone="America/Los_Angeles",
                )

        assert result.success is True
        payload = client.post.call_args.kwargs["json"]
        assert payload["aps"]["alert"]["title"] == "Funny Person is performing near you"
        # 2026-04-15 20:00 UTC = Wednesday, April 15, 1:00 pm PDT in America/Los_Angeles.
        assert payload["aps"]["alert"]["body"] == "The Laugh Cellar on Wednesday, April 15 at 1:00 pm PDT"

    def _send_show(self, comedian_image_url):
        service = ApnsPushService(
            team_id="TEAM12345",
            key_id="KEYID67890",
            private_key_pem="unused",
            bundle_id="com.example.app",
            use_sandbox=True,
        )
        response = MagicMock(status_code=200)
        with patch.object(service, "_auth_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                service.send_show_notification(
                    device_token="apns-token",
                    comedian_name="Funny Person",
                    show_id=42,
                    show_date=None,
                    club_name="The Comedy Club",
                    club_city="New York",
                    club_state="NY",
                    show_page_url="https://laugh-track.com/show/42",
                    comedian_image_url=comedian_image_url,
                )
        return client.post.call_args.kwargs["json"]

    def test_send_show_adds_mutable_content_and_image_url_for_rich_push(self):
        # mutable-content is REQUIRED for the NotificationServiceExtension to run
        # and attach the headshot it downloads from the imageUrl key.
        url = "https://laughtrack.b-cdn.net/comedians/assets/7/avatar.png"
        payload = self._send_show(comedian_image_url=url)
        assert payload["aps"]["mutable-content"] == 1
        assert payload["imageUrl"] == url

    def test_send_show_omits_image_keys_when_no_headshot(self):
        payload = self._send_show(comedian_image_url=None)
        assert "mutable-content" not in payload["aps"]
        assert "imageUrl" not in payload

    def test_send_youtube_live_builds_alert_payload(self):
        service = ApnsPushService(
            team_id="TEAM12345",
            key_id="KEYID67890",
            private_key_pem="unused",
            bundle_id="com.example.app",
            use_sandbox=True,
        )
        response = MagicMock(status_code=200)

        with patch.object(service, "_auth_token", return_value="fake-token"):
            with patch("httpx.Client") as MockClient:
                client = MockClient.return_value.__enter__.return_value
                client.post.return_value = response
                result = service.send_youtube_live_notification(
                    device_token="apns-token",
                    comedian_id="comedian-uuid",
                    comedian_name="Jane Comic",
                    youtube_channel_id="UC-live-channel",
                    youtube_video_id="live-video",
                    video_title=None,
                    watch_url="https://www.youtube.com/watch?v=live-video",
                )

        assert result.success is True
        payload = client.post.call_args.kwargs["json"]
        assert payload["aps"]["alert"]["title"] == "Jane Comic is live on YouTube"
        assert payload["aps"]["alert"]["body"] == "Watch now on YouTube"
        assert payload["type"] == "youtube_live"
        assert payload["comedianId"] == "comedian-uuid"
        assert payload["youtubeChannelId"] == "UC-live-channel"
        assert payload["youtubeVideoId"] == "live-video"
        assert payload["url"] == "https://www.youtube.com/watch?v=live-video"


class TestYouTubeLiveNotificationService:
    def _row(self, **overrides):
        row = {
            "event_id": 42,
            "user_id": "user-1",
            "comedian_uuid": "comedian-uuid",
            "comedian_name": "Jane Comic",
            "youtube_channel_id": "UC-live-channel",
            "youtube_video_id": "live-video",
            "video_title": "Late set from the club",
            "video_url": "https://www.youtube.com/watch?v=live-video",
            "push_token_id": "tok-ios",
            "push_token": "apns-token",
            "push_platform": "ios",
        }
        row.update(overrides)
        return row

    def _service(self, apns=None, fcm=None):
        return YouTubeLiveNotificationService(push_sender=apns, fcm_sender=fcm)

    def test_global_gate_skips_candidate_fetch(self):
        service = self._service()

        with patch.object(service, "_is_global_enabled", return_value=False):
            with patch.object(service, "_fetch_candidates") as mock_fetch:
                summary = service.run()

        mock_fetch.assert_not_called()
        assert summary["global_gated"] == 1
        assert summary["candidates"] == 0
        assert summary["push_sent"] == 0

    def test_candidate_sql_requires_comedian_user_and_token_gates(self):
        service = self._service()
        conn = MagicMock()
        conn.__enter__.return_value = conn
        cur = conn.cursor.return_value.__enter__.return_value
        cur.description = []
        cur.fetchall.return_value = []

        with patch(
            "laughtrack.core.services.notification.service.get_connection",
            return_value=conn,
        ):
            service._fetch_candidates(limit=25)

        sql_arg = cur.execute.call_args.args[0]
        params_arg = cur.execute.call_args.args[1]
        assert "c.youtube_live_notifications_enabled = true" in sql_arg
        assert "up.push_youtube_live_notifications = true" in sql_arg
        assert "JOIN user_push_tokens upt" in sql_arg
        assert "upt.is_active = true" in sql_arg
        assert "yn.id IS NULL" in sql_arg
        assert params_arg == (25,)

    def test_sends_youtube_live_push_and_records_delivery(self):
        apns = MagicMock()
        apns.send_youtube_live_notification.return_value = PushDeliveryResult(success=True, status_code=200)
        service = self._service(apns=apns)

        with patch.object(service, "_is_global_enabled", return_value=True):
            with patch.object(service, "_fetch_candidates", return_value=[self._row()]):
                with patch.object(service, "_record_notification", return_value=501) as mock_record:
                    with patch.object(service, "_record_delivery") as mock_delivery:
                        summary = service.run()

        apns.send_youtube_live_notification.assert_called_once_with(
            device_token="apns-token",
            comedian_id="comedian-uuid",
            comedian_name="Jane Comic",
            youtube_channel_id="UC-live-channel",
            youtube_video_id="live-video",
            video_title="Late set from the club",
            watch_url="https://www.youtube.com/watch?v=live-video",
        )
        mock_record.assert_called_once_with(
            user_id="user-1",
            comedian_id="comedian-uuid",
            youtube_channel_id="UC-live-channel",
            youtube_video_id="live-video",
            video_title="Late set from the club",
            video_url="https://www.youtube.com/watch?v=live-video",
            youtube_websub_event_id=42,
        )
        mock_delivery.assert_called_once_with(
            youtube_live_notification_id=501,
            push_token_id="tok-ios",
            platform="ios",
            status="sent",
            status_code=200,
            failure_reason=None,
        )
        assert summary["candidates"] == 1
        assert summary["push_sent"] == 1
        assert summary["push_errors"] == 0

    def test_android_routes_to_fcm_sender(self):
        fcm = MagicMock()
        fcm.send_youtube_live_notification.return_value = PushDeliveryResult(success=True, status_code=200)
        service = self._service(fcm=fcm)

        with patch.object(service, "_is_global_enabled", return_value=True):
            with patch.object(
                service,
                "_fetch_candidates",
                return_value=[
                    self._row(
                        push_token_id="tok-android",
                        push_token="fcm-token",
                        push_platform="android",
                    )
                ],
            ):
                with patch.object(service, "_record_notification", return_value=501):
                    with patch.object(service, "_record_delivery"):
                        summary = service.run()

        fcm.send_youtube_live_notification.assert_called_once()
        assert fcm.send_youtube_live_notification.call_args.kwargs["device_token"] == "fcm-token"
        assert summary["push_sent"] == 1

    def test_sends_to_every_active_token_for_same_user_and_video(self):
        apns = MagicMock()
        apns.send_youtube_live_notification.return_value = PushDeliveryResult(success=True, status_code=200)
        fcm = MagicMock()
        fcm.send_youtube_live_notification.return_value = PushDeliveryResult(success=True, status_code=200)
        service = self._service(apns=apns, fcm=fcm)

        with patch.object(service, "_is_global_enabled", return_value=True):
            with patch.object(
                service,
                "_fetch_candidates",
                return_value=[
                    self._row(push_token_id="tok-ios", push_token="apns-token", push_platform="ios"),
                    self._row(push_token_id="tok-android", push_token="fcm-token", push_platform="android"),
                ],
            ):
                with patch.object(service, "_record_notification", return_value=501) as mock_record:
                    with patch.object(service, "_record_delivery") as mock_delivery:
                        summary = service.run()

        mock_record.assert_called_once()
        apns.send_youtube_live_notification.assert_called_once()
        fcm.send_youtube_live_notification.assert_called_once()
        assert mock_delivery.call_count == 2
        assert summary["candidates"] == 1
        assert summary["push_sent"] == 2

    def test_duplicate_notification_record_skips_push_send(self):
        apns = MagicMock()
        service = self._service(apns=apns)

        with patch.object(service, "_is_global_enabled", return_value=True):
            with patch.object(service, "_fetch_candidates", return_value=[self._row()]):
                with patch.object(service, "_record_notification", return_value=None):
                    summary = service.run()

        apns.send_youtube_live_notification.assert_not_called()
        assert summary["duplicates"] == 1
        assert summary["push_sent"] == 0

    def test_failed_push_records_delivery_and_deactivates_invalid_token(self):
        apns = MagicMock()
        apns.send_youtube_live_notification.return_value = PushDeliveryResult(
            success=False,
            invalid_token=True,
            status_code=410,
            reason="Unregistered",
        )
        service = self._service(apns=apns)

        with patch.object(service, "_is_global_enabled", return_value=True):
            with patch.object(service, "_fetch_candidates", return_value=[self._row()]):
                with patch.object(service, "_record_notification", return_value=501):
                    with patch.object(service, "_record_delivery") as mock_delivery:
                        with patch.object(service, "_deactivate_push_token") as mock_deactivate:
                            summary = service.run()

        mock_delivery.assert_called_once_with(
            youtube_live_notification_id=501,
            push_token_id="tok-ios",
            platform="ios",
            status="failed",
            status_code=410,
            failure_reason="Unregistered",
        )
        mock_deactivate.assert_called_once_with(
            token_id="tok-ios",
            reason="Unregistered",
            status_code=410,
        )
        assert summary["push_errors"] == 1
        assert summary["errors"] == 1


class TestDryRun:
    def test_dry_run_counts_email_without_sending_or_recording(self):
        row = _make_row(user_zip="10001", club_zip="10002")

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, dry_run=True)

        assert summary["emails_sent"] == 0
        assert summary["emails_would_send"] == 1
        assert summary["push_sent"] == 0
        assert summary["push_would_send"] == 0
        assert summary["errors"] == 0
        MockEmail.send_email.assert_not_called()
        mock_record.assert_not_called()

    def test_dry_run_counts_push_without_sending_or_recording(self):
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
                summary = service.run(radius_miles=50.0, dry_run=True)

        assert summary["push_candidates"] == 1
        assert summary["push_sent"] == 0
        assert summary["push_would_send"] == 1
        assert summary["push_errors"] == 0
        assert summary["emails_would_send"] == 0
        mock_push_sender.send_show_notification.assert_not_called()
        mock_record.assert_not_called()


class TestRunSkipsIfOutsideRadius:
    def test_skips_and_does_not_send(self):
        row = _make_row(user_zip="10001", club_zip="90210")

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 2800.0  # way outside 50 miles

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row]):
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
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
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
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
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
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
            with patch("laughtrack.core.services.notification.service.EmailService"):
                with patch.object(service, "_record_notification") as mock_record:
                    service.run(radius_miles=50.0, days_ahead=30)

        mock_record.assert_called_once_with(
            user_id="user-99",
            comedian_id="comedian-abc",
            show_id=101,
            notification_type="email",
            notification_group_id=ANY,
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
                notification_group_id="grp-1",
            )

        mock_cur.execute.assert_called_once()
        sql_arg, params_arg = mock_cur.execute.call_args[0]
        # SQL should contain ON CONFLICT ... DO NOTHING
        assert "ON CONFLICT" in sql_arg
        assert "DO NOTHING" in sql_arg
        assert "notification_type" in sql_arg
        assert "notification_group_id" in sql_arg
        assert params_arg == ("u1", "c1", 7, "push", "grp-1")


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
        assert "AND sn.comedian_id = c.uuid" not in sql_arg

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

    def test_fetch_candidates_defaults_to_seven_day_catch_up_window(self):
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
            service._fetch_candidates()

        sql_arg = mock_cur.execute.call_args[0][0]
        assert "s2.first_discovered_at >= NOW() - INTERVAL '7 days'" in sql_arg

    def test_fetch_candidates_does_not_filter_out_far_future_new_discoveries(self):
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
            service._fetch_candidates(discovered_within_days=2)

        sql_arg = mock_cur.execute.call_args[0][0]
        assert "s2.date >= NOW()" in sql_arg
        assert "s2.first_discovered_at >= NOW() - INTERVAL '2 days'" in sql_arg
        assert "s2.date <= NOW() + INTERVAL" not in sql_arg


class TestRunMultipleCandidates:
    def test_merges_multiple_followed_comedians_on_same_show_into_one_email(self):
        row1 = _make_row(
            comedian_uuid="comedian-a",
            comedian_name="Comedian A",
            show_id=1,
        )
        row2 = _make_row(
            comedian_uuid="comedian-b",
            comedian_name="Comedian B",
            show_id=1,
        )

        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0

        service = ComedianArrivalNotificationService(zip_distance=mock_zip)

        with patch.object(service, "_fetch_candidates", return_value=[row1, row2]):
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0)

        assert summary["candidates"] == 1
        assert summary["emails_sent"] == 1
        assert summary["errors"] == 0
        mock_zip.distance_miles.assert_called_once_with("10001", "10002")

        sent_message = MockEmail.send_email.call_args[0][0]
        assert sent_message.subject == "Comedian A and Comedian B are performing near you!"
        assert "Comedian A and Comedian B are performing near you!" in sent_message.text_content
        mock_record.assert_called_once_with(
            user_id="user-1",
            comedian_id="comedian-a",
            show_id=1,
            notification_type="email",
            notification_group_id=ANY,
        )

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
            with patch("laughtrack.core.services.notification.service.EmailService") as MockEmail:
                MockEmail.send_email.side_effect = Exception("SMTP failure")
                with patch.object(service, "_record_notification") as mock_record:
                    summary = service.run(radius_miles=50.0, days_ahead=30)

        assert summary["emails_sent"] == 0
        assert summary["errors"] == 1
        mock_record.assert_not_called()


class TestApnsPemNormalization:
    """`ApnsPushService.from_env()` PEM normalization (TASK-2579).

    Local-dev env files often store APNS_PRIVATE_KEY as bare base64
    (no `-----BEGIN PRIVATE KEY-----` headers, no newlines), while CI
    secrets carry the full PEM envelope. `from_env()` must accept both.
    """

    @staticmethod
    def _generate_pem_and_bare_base64() -> tuple[str, str]:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        body_lines = [line for line in pem.splitlines() if line and not line.startswith("-----")]
        bare_base64 = "".join(body_lines)
        return pem, bare_base64

    def _set_env(self, monkeypatch, private_key: str) -> None:
        monkeypatch.setenv("APNS_TEAM_ID", "TEAM12345")
        monkeypatch.setenv("APNS_KEY_ID", "KEYID67890")
        monkeypatch.setenv("APNS_BUNDLE_ID", "com.example.app")
        monkeypatch.setenv("APNS_PRIVATE_KEY", private_key)
        monkeypatch.delenv("APNS_PRIVATE_KEY_PATH", raising=False)
        monkeypatch.delenv("APNS_USE_SANDBOX", raising=False)

    def test_from_env_apns_pem_passthrough_with_full_envelope(self, monkeypatch):
        """A full PEM envelope is left untouched and loads cleanly."""
        pem, _ = self._generate_pem_and_bare_base64()
        self._set_env(monkeypatch, pem)

        service = ApnsPushService.from_env()

        assert service._private_key_pem == pem
        token = service._auth_token()
        assert token.count(".") == 2

    def test_from_env_apns_pem_autowraps_bare_base64(self, monkeypatch):
        """Bare base64 (no headers, no newlines) is wrapped into PEM and loads cleanly."""
        _, bare_base64 = self._generate_pem_and_bare_base64()
        assert "-----BEGIN" not in bare_base64
        assert "\n" not in bare_base64

        self._set_env(monkeypatch, bare_base64)

        service = ApnsPushService.from_env()

        normalized = service._private_key_pem
        assert normalized.startswith("-----BEGIN PRIVATE KEY-----\n")
        assert normalized.rstrip().endswith("-----END PRIVATE KEY-----")
        body_lines = [line for line in normalized.splitlines() if line and not line.startswith("-----")]
        assert all(len(line) <= 64 for line in body_lines)
        assert "".join(body_lines) == bare_base64

        token = service._auth_token()
        assert token.count(".") == 2

    def test_from_env_apns_pem_normalizes_escaped_newlines(self, monkeypatch):
        """Env-file-escaped `\\n` sequences in a full PEM are converted to real newlines."""
        pem, _ = self._generate_pem_and_bare_base64()
        escaped = pem.replace("\n", "\\n")

        self._set_env(monkeypatch, escaped)

        service = ApnsPushService.from_env()

        assert service._private_key_pem == pem
        token = service._auth_token()
        assert token.count(".") == 2


class TestRunGroupsPushNotifications:
    """A run's burst of shows for one user collapses into ONE push (push-only grouping)."""

    def _push_row(self, **kwargs) -> dict:
        base = dict(
            notification_type="push",
            push_token_id="token-row-1",
            push_token="device-abc",
            push_platform="ios",
            user_id="user-1",
            user_zip="10001",
            club_zip="10002",
        )
        base.update(kwargs)
        return _make_row(**base)

    def _service(self, sender):
        mock_zip = MagicMock()
        mock_zip.distance_miles.return_value = 5.0  # within radius
        return ComedianArrivalNotificationService(zip_distance=mock_zip, push_sender=sender)

    def test_one_comedian_multiple_shows_sends_single_grouped_push(self):
        rows = [
            self._push_row(show_id=42, show_date=datetime(2026, 4, 15, 20, 0, tzinfo=timezone.utc)),
            self._push_row(show_id=43, show_date=datetime(2026, 4, 20, 20, 0, tzinfo=timezone.utc)),
            self._push_row(show_id=44, show_date=datetime(2026, 4, 25, 20, 0, tzinfo=timezone.utc)),
        ]
        sender = MagicMock()
        service = self._service(sender)

        with patch.object(service, "_fetch_candidates", return_value=rows):
            with patch.object(service, "_record_notification") as mock_record:
                summary = service.run(radius_miles=50.0)

        # One push covering three shows; every show still recorded so future runs skip them.
        sender.send_show_notification.assert_called_once()
        assert summary["push_sent"] == 1
        kwargs = sender.send_show_notification.call_args.kwargs
        assert kwargs["title"] == "Funny Person has 3 shows near you"
        assert kwargs["body"] == "Tap to see where and when"
        assert kwargs["route"] == "favorites"
        # Deep-link fallback for older clients (no route key) is the soonest show.
        assert kwargs["show_id"] == 42
        assert mock_record.call_count == 3
        assert sorted(c.kwargs["show_id"] for c in mock_record.call_args_list) == [42, 43, 44]
        assert all(c.kwargs["notification_type"] == "push" for c in mock_record.call_args_list)
        # All shows in the group share one notification_group_id (so the center can
        # regroup them into the single push that was sent).
        group_ids = {c.kwargs["notification_group_id"] for c in mock_record.call_args_list}
        assert len(group_ids) == 1 and None not in group_ids

    def test_multiple_comedians_send_digest_push(self):
        rows = [
            self._push_row(
                show_id=42, comedian_uuid="uuid-a", comedian_name="Funny Person",
                show_date=datetime(2026, 4, 15, 20, 0, tzinfo=timezone.utc),
            ),
            self._push_row(
                show_id=43, comedian_uuid="uuid-b", comedian_name="Chuckles McGee",
                show_date=datetime(2026, 4, 20, 20, 0, tzinfo=timezone.utc),
            ),
        ]
        sender = MagicMock()
        service = self._service(sender)

        with patch.object(service, "_fetch_candidates", return_value=rows):
            with patch.object(service, "_record_notification") as mock_record:
                summary = service.run(radius_miles=50.0)

        sender.send_show_notification.assert_called_once()
        assert summary["push_sent"] == 1
        kwargs = sender.send_show_notification.call_args.kwargs
        assert kwargs["title"] == "2 comedians you follow have shows near you"
        assert kwargs["body"] == "Tap to see where and when"
        assert kwargs["route"] == "favorites"
        assert mock_record.call_count == 2

    def test_single_show_keeps_per_show_copy(self):
        # A lone show sends with no title/body override — the sender builds the copy.
        sender = MagicMock()
        service = self._service(sender)

        with patch.object(service, "_fetch_candidates", return_value=[self._push_row(show_id=42)]):
            with patch.object(service, "_record_notification"):
                summary = service.run(radius_miles=50.0)

        sender.send_show_notification.assert_called_once()
        assert summary["push_sent"] == 1
        kwargs = sender.send_show_notification.call_args.kwargs
        assert kwargs["title"] is None
        assert kwargs["body"] is None
        assert kwargs["route"] is None

    def test_separate_users_are_not_merged(self):
        rows = [
            self._push_row(show_id=42, user_id="user-1", push_token_id="tok-1", push_token="dev-1"),
            self._push_row(show_id=43, user_id="user-2", push_token_id="tok-2", push_token="dev-2"),
        ]
        sender = MagicMock()
        service = self._service(sender)

        with patch.object(service, "_fetch_candidates", return_value=rows):
            with patch.object(service, "_record_notification"):
                summary = service.run(radius_miles=50.0)

        assert sender.send_show_notification.call_count == 2
        assert summary["push_sent"] == 2
