"""Comedian arrival notification service.

Queries upcoming shows where a user's favorited comedian is in the lineup,
filters by distance from user's zip code to club's zip code, sends notification
emails, and records sent notifications to prevent duplicates.
"""

from __future__ import annotations

import base64
import html as html_module
import json
import os
import textwrap
import time
import uuid
from dataclasses import dataclass
from typing import Dict
from urllib.parse import quote
from zoneinfo import ZoneInfo

from laughtrack.infrastructure.database.connection import get_connection
from laughtrack.core.entities.email.local.email_models import EmailMessage
from laughtrack.core.services.notification.geo import ZipCodeDistance
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.email.service import EmailService

_BASE_CANDIDATES_SELECT_SQL = """
SELECT
    u.id          AS user_id,
    u.email       AS user_email,
    u.name        AS user_name,
    up.zip_code   AS user_zip,
    up.nearby_distance_miles,
    c.uuid        AS comedian_uuid,
    c.name        AS comedian_name,
    s.id          AS show_id,
    s.date        AS show_date,
    s.show_page_url,
    cl.name       AS club_name,
    cl.address    AS club_address,
    cl.city       AS club_city,
    cl.state      AS club_state,
    cl.zip_code   AS club_zip,
    cl.timezone   AS club_timezone,
    c.has_image   AS comedian_has_image,
    (
        SELECT cia.avatar_path
        FROM comedian_image_assets cia
        WHERE cia.comedian_id = c.id
          AND cia.is_active = true
          AND cia.avatar_path IS NOT NULL
        ORDER BY cia.published_at DESC
        LIMIT 1
    ) AS comedian_avatar_path,
    {notification_type_sql} AS notification_type,
    {push_token_id_sql} AS push_token_id,
    {push_token_sql} AS push_token,
    {push_platform_sql} AS push_platform
FROM users u
JOIN user_profiles up ON up.user_id = u.id
JOIN favorite_comedians fc ON fc.profile_id = up.id
JOIN comedians c ON c.uuid = fc.comedian_id
JOIN lineup_items li ON li.comedian_id = c.uuid AND li.show_id IN (
    SELECT s2.id FROM shows s2
    WHERE s2.date >= NOW()
      AND s2.first_discovered_at IS NOT NULL
      AND s2.first_discovered_at >= NOW() - INTERVAL '%s days'
)
JOIN shows s ON s.id = li.show_id
JOIN clubs cl ON cl.id = s.club_id
{push_join_sql}
WHERE up.email_show_notifications = true
  AND up.zip_code IS NOT NULL AND up.zip_code != ''
  AND cl.zip_code IS NOT NULL AND cl.zip_code != ''
  AND NOT EXISTS (
      SELECT 1 FROM sent_notifications sn
      WHERE sn.user_id = u.id
        AND sn.show_id = s.id
        AND sn.notification_type = 'email'
  )
"""

_EMAIL_CANDIDATES_SQL = _BASE_CANDIDATES_SELECT_SQL.format(
    notification_type_sql="'email'",
    push_token_id_sql="NULL",
    push_token_sql="NULL",
    push_platform_sql="NULL",
    push_join_sql="",
)

_PUSH_CANDIDATES_SQL = (
    _BASE_CANDIDATES_SELECT_SQL.format(
        notification_type_sql="'push'",
        push_token_id_sql="upt.id",
        push_token_sql="upt.token",
        push_platform_sql="upt.platform",
        push_join_sql="JOIN user_push_tokens upt ON upt.user_id = u.id AND upt.profile_id = up.id AND upt.is_active = true",
    )
    .replace("up.email_show_notifications = true", "up.push_show_notifications = true")
    .replace("sn.notification_type = 'email'", "sn.notification_type = 'push'")
)

_CANDIDATES_SQL = f"""
{_EMAIL_CANDIDATES_SQL}
UNION ALL
{_PUSH_CANDIDATES_SQL}
ORDER BY user_id, show_date, comedian_name, notification_type, push_token_id
"""

_INSERT_SENT_NOTIFICATION_SQL = """
INSERT INTO sent_notifications (user_id, comedian_id, show_id, notification_type, notification_group_id, sent_at)
VALUES (%s, %s, %s, %s, %s, NOW())
ON CONFLICT (user_id, comedian_id, show_id, notification_type) DO NOTHING
"""

_DEACTIVATE_PUSH_TOKEN_SQL = """
UPDATE user_push_tokens
SET is_active = false,
    revoked_at = NOW(),
    updated_at = NOW()
WHERE id = %s
"""

_YOUTUBE_LIVE_CANDIDATES_SQL = """
SELECT
    ywe.id AS event_id,
    u.id AS user_id,
    c.uuid AS comedian_uuid,
    c.name AS comedian_name,
    ywe.youtube_channel_id,
    ywe.youtube_video_id,
    ywe.video_title,
    ywe.video_url,
    upt.id AS push_token_id,
    upt.token AS push_token,
    upt.platform AS push_platform
FROM youtube_websub_events ywe
JOIN comedians c ON c.uuid = ywe.comedian_id
JOIN favorite_comedians fc ON fc.comedian_id = c.uuid
JOIN user_profiles up ON up.id = fc.profile_id
JOIN users u ON u.id = up.user_id
JOIN user_push_tokens upt
  ON upt.user_id = u.id
 AND upt.profile_id = up.id
 AND upt.is_active = true
LEFT JOIN youtube_live_notifications yn
  ON yn.user_id = u.id
 AND yn.comedian_id = c.uuid
 AND yn.youtube_video_id = ywe.youtube_video_id
 AND yn.notification_type = 'push'
WHERE ywe.event_status = 'verified'
  AND ywe.verification_status = 'live'
  AND ywe.youtube_channel_id IS NOT NULL
  AND ywe.youtube_video_id IS NOT NULL
  AND ywe.video_url IS NOT NULL
  AND c.youtube_live_notifications_enabled = true
  AND up.push_youtube_live_notifications = true
  AND yn.id IS NULL
ORDER BY ywe.verified_at ASC NULLS LAST, ywe.received_at ASC, u.id, upt.id
LIMIT %s
"""

_YOUTUBE_LIVE_GLOBAL_ENABLED_SQL = """
SELECT push_delivery_enabled
FROM youtube_websub_settings
WHERE id = 1
"""

_INSERT_YOUTUBE_LIVE_NOTIFICATION_SQL = """
INSERT INTO youtube_live_notifications (
    user_id,
    comedian_id,
    youtube_channel_id,
    youtube_video_id,
    video_title,
    video_url,
    notification_type,
    youtube_websub_event_id,
    sent_at
)
VALUES (%s, %s, %s, %s, %s, %s, 'push', %s, NOW())
ON CONFLICT (user_id, comedian_id, youtube_video_id, notification_type) DO NOTHING
RETURNING id
"""

_INSERT_YOUTUBE_LIVE_DELIVERY_SQL = """
INSERT INTO youtube_live_notification_deliveries (
    youtube_live_notification_id,
    push_token_id,
    platform,
    delivery_status,
    status_code,
    failure_reason,
    attempted_at
)
VALUES (%s, %s, %s, %s, %s, %s, NOW())
"""

_INVALID_APNS_REASONS = {
    "BadDeviceToken",
    "DeviceTokenNotForTopic",
    "Unregistered",
}

# FCM HTTP v1 error codes that unambiguously mean the token is dead and should
# be deactivated. Only UNREGISTERED qualifies (app uninstalled / token expired).
# INVALID_ARGUMENT is deliberately EXCLUDED: FCM returns 400/INVALID_ARGUMENT for
# *any* malformed request field, so a server-side payload-shape bug would
# otherwise mass-deactivate every healthy Android token in a run. Such failures
# stay non-deactivating (logged as a push error) so the bug is fixed, not papered
# over by wiping tokens. SENDER_ID_MISMATCH / auth errors are config problems,
# also excluded.
_INVALID_FCM_REASONS = {
    "UNREGISTERED",
}


# %-formatted (not f-string) so DB-sourced values can only enter the template
# through the explicit html.escape()-wrapped substitution dict below.
_EMAIL_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">%(e_comedian)s %(verb)s performing near you!</h2>
  <p>Great news — one of your favorite comedians has an upcoming show in your area.</p>
  <table style="width:100%%; border-collapse:collapse; margin: 16px 0;">
    <tr>
      <td style="padding: 8px 0; font-weight: bold; width: 120px;">Comedian:</td>
      <td style="padding: 8px 0;">%(e_comedian)s</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; font-weight: bold;">Date:</td>
      <td style="padding: 8px 0;">%(e_date_str)s</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; font-weight: bold;">Venue:</td>
      <td style="padding: 8px 0;">%(e_club)s</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; font-weight: bold;">Location:</td>
      <td style="padding: 8px 0;">%(e_location)s</td>
    </tr>
  </table>
  %(ticket_line)s
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
  <p style="color: #666; font-size: 12px;">
    You're receiving this email because you follow %(e_comedian)s on LaughTrack and have
    enabled show notifications. To unsubscribe, visit your account settings at
    <a href="https://laugh-track.com">laugh-track.com</a>.
  </p>
</body>
</html>"""


def _format_comedian_names(names: list[str]) -> str:
    cleaned = [name for name in names if name]
    if not cleaned:
        return "A comedian you follow"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _is_plural_comedian_label(comedian_name: str) -> bool:
    return " and " in comedian_name or ", " in comedian_name


# Fallback timezone for shows whose club has no stored timezone. Mirrors
# apps/web DEFAULT_SHOW_TIMEZONE so push and notification-center copy agree.
_DEFAULT_SHOW_TIMEZONE = "America/New_York"


def _format_performance_time(show_date: object, timezone: str | None) -> str:
    """Club-local "8:30 pm EDT" for the push body.

    Mirrors the web notification-center formatPerformanceTime (Intl.DateTimeFormat
    with hour/minute/dayPeriod/timeZoneName) so the push body matches what the
    in-app notification center shows: lowercase am/pm, short tz abbreviation.
    """
    if not hasattr(show_date, "astimezone"):
        return ""
    try:
        tz = ZoneInfo(timezone or _DEFAULT_SHOW_TIMEZONE)
    except Exception:
        tz = ZoneInfo(_DEFAULT_SHOW_TIMEZONE)
    local = show_date.astimezone(tz)
    hour = local.strftime("%-I")  # no leading zero, matching hour: "numeric"
    minute = local.strftime("%M")
    day_period = local.strftime("%p").lower()  # center lowercases am/pm
    tz_abbrev = local.strftime("%Z")
    parts = [f"{hour}:{minute}" if hour and minute else "", day_period, tz_abbrev]
    return " ".join(part for part in parts if part)


def _format_performance_date(show_date: object, timezone: str | None) -> str:
    """Club-local "Friday, July 4" for the push body.

    Mirrors the web notification-center formatPerformanceDate (Intl.DateTimeFormat
    with weekday: "long", month: "long", day: "numeric") so the push body matches
    the in-app notification center.
    """
    if not hasattr(show_date, "astimezone"):
        return ""
    try:
        tz = ZoneInfo(timezone or _DEFAULT_SHOW_TIMEZONE)
    except Exception:
        tz = ZoneInfo(_DEFAULT_SHOW_TIMEZONE)
    local = show_date.astimezone(tz)
    return local.strftime("%A, %B %-d")  # %-d: no leading zero, matching day: "numeric"


def _format_show_subtitle(club_name: str, show_date: object, timezone: str | None) -> str:
    """"{club} on {date} at {time}" push body — matches the notification-center subtitle."""
    date_str = _format_performance_date(show_date, timezone)
    time_str = _format_performance_time(show_date, timezone)
    when = " ".join(
        part
        for part in (
            f"on {date_str}" if date_str else "",
            f"at {time_str}" if time_str else "",
        )
        if part
    )
    if club_name and when:
        return f"{club_name} {when}"
    return when or club_name


# Grouped pushes (multiple shows in one run) carry a generic CTA body; tapping
# opens the Favorites tab, which renders upcoming shows from followed comedians.
_GROUPED_PUSH_BODY = "Tap to see where and when"


def _notification_group_id(cache: dict, user_id: object) -> str:
    """One group id per (user, run), memoized in `cache` for the run.

    Push and email records for the same user in the same run share it so the
    in-app notification center can reconstruct the single notification that was
    sent from its rows.
    """
    gid = cache.get(user_id)
    if gid is None:
        gid = uuid.uuid4().hex
        cache[user_id] = gid
    return gid


def _build_grouped_push_copy(events: list[dict]) -> tuple[str, str]:
    """Title/body for a per-user push covering MORE THAN ONE show in a run.

    Single-show sends keep the existing "{comedian} is performing near you" /
    "{club} on {date} at {time}" copy; this only runs when a user has >1 distinct
    show this run, and picks a title tier (the body is always the CTA):
      - one comedian, N shows -> "{C} has N shows near you"
      - >=2 comedians         -> "K comedians you follow have shows near you"

    `events` must be pre-sorted soonest-first.
    """
    # Distinct comedian names, in soonest-first order.
    names: list[str] = []
    for event in events:
        for name in event.get("comedian_names") or [event.get("comedian_name")]:
            if name and name not in names:
                names.append(name)

    if len(names) <= 1:
        comedian = names[0] if names else _format_comedian_names([])
        verb = "have" if _is_plural_comedian_label(comedian) else "has"
        title = f"{comedian} {verb} {len(events)} shows near you"
    else:
        title = f"{len(names)} comedians you follow have shows near you"
    return title, _GROUPED_PUSH_BODY


def _build_comedian_image_url(
    avatar_path: str | None,
    comedian_name: str | None,
    has_image: bool | None,
) -> str | None:
    """Public CDN URL for a comedian's headshot, for the rich push attachment.

    Mirrors the web buildComedianImageUrls avatar precedence: the active image
    asset's avatar_path wins; otherwise fall back to the legacy name-based path
    when the comedian has_image; None when there is nothing to show.
    """
    cdn_host = os.environ.get("BUNNYCDN_CDN_HOST") or "laughtrack.b-cdn.net"
    if avatar_path:
        return f"https://{cdn_host}/{avatar_path.lstrip('/')}"
    if has_image and comedian_name:
        return f"https://{cdn_host}/comedians/{quote(comedian_name, safe='')}.png"
    return None


def _build_email_html(
    comedian_name: str,
    show_date: object,
    club_name: str,
    club_city: str,
    club_state: str,
    show_page_url: str,
) -> str:
    date_str = show_date.strftime("%A, %B %-d, %Y at %-I:%M %p") if hasattr(show_date, "strftime") else str(show_date)
    e_comedian = html_module.escape(comedian_name)
    e_club = html_module.escape(club_name)
    e_location = html_module.escape(", ".join(filter(None, [club_city, club_state])))
    e_date_str = html_module.escape(date_str)
    ticket_line = (
        '<p><a href="%s" style="color:#1a73e8;">View show and buy tickets</a></p>' % html_module.escape(show_page_url)
        if show_page_url
        else ""
    )
    return _EMAIL_HTML_TEMPLATE % {
        "e_comedian": e_comedian,
        "verb": "are" if _is_plural_comedian_label(comedian_name) else "is",
        "e_club": e_club,
        "e_location": e_location,
        "e_date_str": e_date_str,
        "ticket_line": ticket_line,
    }


def _build_email_text(
    comedian_name: str,
    show_date: object,
    club_name: str,
    club_city: str,
    club_state: str,
    show_page_url: str,
) -> str:
    date_str = show_date.strftime("%A, %B %-d, %Y at %-I:%M %p") if hasattr(show_date, "strftime") else str(show_date)
    location = ", ".join(filter(None, [club_city, club_state]))
    verb = "are" if _is_plural_comedian_label(comedian_name) else "is"
    lines = [
        f"{comedian_name} {verb} performing near you!",
        "",
        f"Comedian: {comedian_name}",
        f"Date: {date_str}",
        f"Venue: {club_name}",
        f"Location: {location}",
    ]
    if show_page_url:
        lines += ["", f"View show and buy tickets: {show_page_url}"]
    lines += [
        "",
        "---",
        f"You're receiving this because you follow {comedian_name} on LaughTrack.",
        "To unsubscribe, visit laugh-track.com and update your notification settings.",
    ]
    return "\n".join(lines)


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class PushDeliveryResult:
    success: bool
    invalid_token: bool = False
    status_code: int | None = None
    reason: str | None = None


class ApnsPushService:
    """Minimal APNs provider client for show notifications."""

    def __init__(
        self,
        team_id: str,
        key_id: str,
        private_key_pem: str,
        bundle_id: str,
        use_sandbox: bool = False,
    ):
        self._team_id = team_id
        self._key_id = key_id
        self._private_key_pem = private_key_pem
        self._bundle_id = bundle_id
        self._host = "api.sandbox.push.apple.com" if use_sandbox else "api.push.apple.com"
        self._cached_token: tuple[str, int] | None = None

    @classmethod
    def from_env(cls) -> "ApnsPushService":
        private_key = os.getenv("APNS_PRIVATE_KEY")
        private_key_path = os.getenv("APNS_PRIVATE_KEY_PATH")
        if not private_key and private_key_path:
            with open(private_key_path, encoding="utf-8") as f:
                private_key = f.read()
        if private_key:
            private_key = private_key.replace("\\n", "\n")
            if "-----BEGIN" not in private_key:
                stripped = "".join(private_key.split())
                body = "\n".join(textwrap.wrap(stripped, 64))
                private_key = "-----BEGIN PRIVATE KEY-----\n" f"{body}\n" "-----END PRIVATE KEY-----\n"

        missing = [
            name
            for name, value in {
                "APNS_TEAM_ID": os.getenv("APNS_TEAM_ID"),
                "APNS_KEY_ID": os.getenv("APNS_KEY_ID"),
                "APNS_PRIVATE_KEY": private_key,
                "APNS_BUNDLE_ID": os.getenv("APNS_BUNDLE_ID"),
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing APNs configuration: {', '.join(missing)}")

        return cls(
            team_id=os.environ["APNS_TEAM_ID"],
            key_id=os.environ["APNS_KEY_ID"],
            private_key_pem=private_key or "",
            bundle_id=os.environ["APNS_BUNDLE_ID"],
            use_sandbox=os.getenv("APNS_USE_SANDBOX", "false").lower() in ("1", "true", "yes", "on"),
        )

    def send_show_notification(
        self,
        device_token: str,
        comedian_name: str,
        show_id: int,
        show_date: object,
        club_name: str,
        club_city: str,
        club_state: str,
        show_page_url: str,
        club_timezone: str | None = None,
        comedian_image_url: str | None = None,
        title: str | None = None,
        body: str | None = None,
        route: str | None = None,
        show_ids: str | None = None,
    ) -> PushDeliveryResult:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("APNs push delivery requires httpx with HTTP/2 support") from e

        # title/body default to the single-show copy; a grouped per-user push
        # (multiple shows in one run) passes precomputed strings to override them.
        verb = "are" if _is_plural_comedian_label(comedian_name) else "is"
        title = title if title is not None else f"{comedian_name} {verb} performing near you"
        # Body mirrors the in-app notification center: "{club} on {date} at {time}".
        body = body if body is not None else _format_show_subtitle(club_name, show_date, club_timezone)

        aps: dict = {
            "alert": {
                "title": title,
                "body": body,
            },
            "sound": "default",
        }
        payload = {
            "aps": aps,
            "showId": show_id,
            "url": show_page_url,
        }
        # Grouped pushes set route so clients open the Favorites tab; the showId
        # above stays as the fallback older clients (no route key) use.
        if route:
            payload["route"] = route
        # Comma-joined show ids so the Favorites tab can scope to this push's shows.
        if show_ids:
            payload["showIds"] = show_ids
        if hasattr(show_date, "isoformat"):
            payload["showDate"] = show_date.isoformat()
        # Rich push: mutable-content lets the NotificationServiceExtension run and
        # attach the headshot it downloads from the `imageUrl` key.
        if comedian_image_url:
            aps["mutable-content"] = 1
            payload["imageUrl"] = comedian_image_url

        headers = {
            "authorization": f"bearer {self._auth_token()}",
            "apns-topic": self._bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        url = f"https://{self._host}/3/device/{device_token}"
        with httpx.Client(http2=True, timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if 200 <= response.status_code < 300:
            return PushDeliveryResult(success=True, status_code=response.status_code)

        reason = self._extract_reason(response)
        return PushDeliveryResult(
            success=False,
            invalid_token=response.status_code in (400, 410) and reason in _INVALID_APNS_REASONS,
            status_code=response.status_code,
            reason=reason,
        )

    def send_test_notification(
        self,
        device_token: str,
        title: str = "LaughTrack test notification",
        body: str = "If you can see this, push delivery is working.",
    ) -> PushDeliveryResult:
        """Send a diagnostic alert without a show or deep-link payload."""
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("APNs push delivery requires httpx with HTTP/2 support") from e

        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "sound": "default",
            },
            "type": "delivery_test",
        }
        headers = {
            "authorization": f"bearer {self._auth_token()}",
            "apns-topic": self._bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        url = f"https://{self._host}/3/device/{device_token}"
        with httpx.Client(http2=True, timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if 200 <= response.status_code < 300:
            return PushDeliveryResult(success=True, status_code=response.status_code)

        reason = self._extract_reason(response)
        return PushDeliveryResult(
            success=False,
            invalid_token=response.status_code in (400, 410) and reason in _INVALID_APNS_REASONS,
            status_code=response.status_code,
            reason=reason,
        )

    def send_youtube_live_notification(
        self,
        device_token: str,
        comedian_id: str,
        comedian_name: str,
        youtube_channel_id: str,
        youtube_video_id: str,
        video_title: str | None,
        watch_url: str,
    ) -> PushDeliveryResult:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("APNs push delivery requires httpx with HTTP/2 support") from e

        title = f"{comedian_name} is live on YouTube"
        body = video_title or "Watch now on YouTube"
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "sound": "default",
            },
            "type": "youtube_live",
            "comedianId": comedian_id,
            "youtubeChannelId": youtube_channel_id,
            "youtubeVideoId": youtube_video_id,
            "url": watch_url,
        }

        headers = {
            "authorization": f"bearer {self._auth_token()}",
            "apns-topic": self._bundle_id,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        url = f"https://{self._host}/3/device/{device_token}"
        with httpx.Client(http2=True, timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if 200 <= response.status_code < 300:
            return PushDeliveryResult(success=True, status_code=response.status_code)

        reason = self._extract_reason(response)
        return PushDeliveryResult(
            success=False,
            invalid_token=response.status_code in (400, 410) and reason in _INVALID_APNS_REASONS,
            status_code=response.status_code,
            reason=reason,
        )

    def _auth_token(self) -> str:
        now = int(time.time())
        if self._cached_token and now - self._cached_token[1] < 50 * 60:
            return self._cached_token[0]

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import ec, utils
        except ImportError as e:
            raise RuntimeError("APNs token signing requires cryptography") from e

        key = serialization.load_pem_private_key(
            self._private_key_pem.encode("utf-8"),
            password=None,
        )
        header = {"alg": "ES256", "kid": self._key_id}
        claims = {"iss": self._team_id, "iat": now}
        signing_input = ".".join(
            [
                _base64url(json.dumps(header, separators=(",", ":")).encode("utf-8")),
                _base64url(json.dumps(claims, separators=(",", ":")).encode("utf-8")),
            ]
        )
        der_signature = key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(der_signature)
        signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        token = f"{signing_input}.{_base64url(signature)}"
        self._cached_token = (token, now)
        return token

    def _extract_reason(self, response: object) -> str | None:
        try:
            data = response.json()
        except Exception:
            return None
        reason = data.get("reason") if isinstance(data, dict) else None
        return reason if isinstance(reason, str) else None


class FcmPushService:
    """Minimal FCM HTTP v1 client for Android show notifications.

    Mirrors ApnsPushService's send_show_notification(...) contract so the
    notification service can route per-token by platform. Uses the
    already-present google-auth dependency for the service-account OAuth2
    access token rather than pulling in firebase-admin.
    """

    _SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, project_id: str, credentials: object):
        self._project_id = project_id
        self._credentials = credentials

    @classmethod
    def from_env(cls) -> "FcmPushService":
        try:
            from google.oauth2 import service_account
        except ImportError as e:
            raise RuntimeError("FCM push delivery requires google-auth") from e

        raw_json = os.getenv("FCM_SERVICE_ACCOUNT_JSON")
        path = os.getenv("FCM_SERVICE_ACCOUNT_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        info: dict | None = None
        if raw_json:
            info = json.loads(raw_json)
        elif path:
            with open(path, encoding="utf-8") as f:
                info = json.load(f)
        if not info:
            raise ValueError(
                "Missing FCM configuration: set FCM_SERVICE_ACCOUNT_JSON, "
                "FCM_SERVICE_ACCOUNT_PATH, or GOOGLE_APPLICATION_CREDENTIALS"
            )

        project_id = os.getenv("FCM_PROJECT_ID") or info.get("project_id")
        if not project_id:
            raise ValueError(
                "Missing FCM project id: set FCM_PROJECT_ID or include project_id " "in the service account JSON"
            )

        credentials = service_account.Credentials.from_service_account_info(info, scopes=[cls._SCOPE])
        return cls(project_id=str(project_id), credentials=credentials)

    def send_show_notification(
        self,
        device_token: str,
        comedian_name: str,
        show_id: int,
        show_date: object,
        club_name: str,
        club_city: str,
        club_state: str,
        show_page_url: str,
        club_timezone: str | None = None,
        comedian_image_url: str | None = None,
        title: str | None = None,
        body: str | None = None,
        route: str | None = None,
        show_ids: str | None = None,
    ) -> PushDeliveryResult:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("FCM push delivery requires httpx") from e

        # title/body default to the single-show copy; a grouped per-user push
        # (multiple shows in one run) passes precomputed strings to override them.
        verb = "are" if _is_plural_comedian_label(comedian_name) else "is"
        title = title if title is not None else f"{comedian_name} {verb} performing near you"
        # Body mirrors the in-app notification center: "{club} on {date} at {time}".
        body = body if body is not None else _format_show_subtitle(club_name, show_date, club_timezone)

        # Data-only message (no notification block) so the Android
        # FirebaseMessagingService always runs onMessageReceived — even when
        # backgrounded — and builds the notification + deep-link extras itself
        # from these keys (LaughTrackMessagingService reads title/body/showId/url
        # off message.data). FCM data values must all be strings.
        data = {
            "title": title,
            "body": body,
            "showId": str(show_id),
            "url": show_page_url,
        }
        # Grouped pushes set route so clients open the Favorites tab; the showId
        # above stays as the fallback older clients (no route key) use.
        if route:
            data["route"] = route
        # Comma-joined show ids so the Favorites tab can scope to this push's shows.
        if show_ids:
            data["showIds"] = show_ids
        if hasattr(show_date, "isoformat"):
            data["showDate"] = show_date.isoformat()
        # Rich push: the Android client (LaughTrackMessagingService) reads imageUrl
        # off message.data and renders it as a BigPictureStyle headshot.
        if comedian_image_url:
            data["imageUrl"] = comedian_image_url

        message = {
            "message": {
                "token": device_token,
                "data": data,
                "android": {"priority": "high"},
            }
        }

        url = f"https://fcm.googleapis.com/v1/projects/{self._project_id}/messages:send"
        headers = {"authorization": f"Bearer {self._access_token()}"}
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=message)

        if 200 <= response.status_code < 300:
            return PushDeliveryResult(success=True, status_code=response.status_code)

        reason = self._extract_reason(response)
        return PushDeliveryResult(
            success=False,
            invalid_token=response.status_code in (400, 404) and reason in _INVALID_FCM_REASONS,
            status_code=response.status_code,
            reason=reason,
        )

    def _access_token(self) -> str:
        from google.auth.transport.requests import Request

        if not getattr(self._credentials, "valid", False):
            self._credentials.refresh(Request())
        return self._credentials.token

    def _extract_reason(self, response: object) -> str | None:
        try:
            data = response.json()
        except Exception:
            return None
        error = data.get("error") if isinstance(data, dict) else None
        if not isinstance(error, dict):
            return None
        # The FCM-specific code (UNREGISTERED, INVALID_ARGUMENT, …) lives in
        # error.details[].errorCode; fall back to the generic error.status.
        details = error.get("details")
        if isinstance(details, list):
            for detail in details:
                if isinstance(detail, dict) and isinstance(detail.get("errorCode"), str):
                    return detail["errorCode"]
        status = error.get("status")
        return status if isinstance(status, str) else None

    def send_youtube_live_notification(
        self,
        device_token: str,
        comedian_id: str,
        comedian_name: str,
        youtube_channel_id: str,
        youtube_video_id: str,
        video_title: str | None,
        watch_url: str,
    ) -> PushDeliveryResult:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("FCM push delivery requires httpx") from e

        data = {
            "title": f"{comedian_name} is live on YouTube",
            "body": video_title or "Watch now on YouTube",
            "type": "youtube_live",
            "comedianId": comedian_id,
            "youtubeChannelId": youtube_channel_id,
            "youtubeVideoId": youtube_video_id,
            "url": watch_url,
        }
        message = {
            "message": {
                "token": device_token,
                "data": data,
                "android": {"priority": "high"},
            }
        }

        url = f"https://fcm.googleapis.com/v1/projects/{self._project_id}/messages:send"
        headers = {"authorization": f"Bearer {self._access_token()}"}
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=message)

        if 200 <= response.status_code < 300:
            return PushDeliveryResult(success=True, status_code=response.status_code)

        reason = self._extract_reason(response)
        return PushDeliveryResult(
            success=False,
            invalid_token=response.status_code in (400, 404) and reason in _INVALID_FCM_REASONS,
            status_code=response.status_code,
            reason=reason,
        )


class YouTubeLiveNotificationService:
    """Sends push notifications when verified YouTube WebSub events go live."""

    def __init__(self, push_sender: object | None = None, fcm_sender: object | None = None):
        self._push_sender = push_sender
        self._fcm_sender = fcm_sender

    def run(self, limit: int = 50, dry_run: bool = False) -> Dict[str, int]:
        summary = {
            "global_gated": 0,
            "candidates": 0,
            "push_would_send": 0,
            "push_sent": 0,
            "push_errors": 0,
            "duplicates": 0,
            "errors": 0,
        }

        Logger.info(f"YouTubeLiveNotificationService: starting run (limit={limit}, dry_run={dry_run})")

        try:
            if not self._is_global_enabled():
                summary["global_gated"] = 1
                Logger.info("YouTubeLiveNotificationService: skipped — global push delivery disabled")
                return summary
        except Exception as e:
            Logger.error(f"YouTubeLiveNotificationService: failed to read global gate: {e}")
            summary["errors"] += 1
            return summary

        try:
            rows = self._fetch_candidates(limit=limit)
        except Exception as e:
            Logger.error(f"YouTubeLiveNotificationService: failed to fetch candidates: {e}")
            summary["errors"] += 1
            return summary

        rows = self._merge_same_youtube_live_candidates(rows)
        summary["candidates"] = len(rows)

        for row in rows:
            event_id = row["event_id"]
            user_id = row["user_id"]
            comedian_uuid = row["comedian_uuid"]
            comedian_name = row["comedian_name"]
            youtube_channel_id = row["youtube_channel_id"]
            youtube_video_id = row["youtube_video_id"]
            video_title = row.get("video_title")
            video_url = row["video_url"]
            push_tokens = row.get("push_tokens") or []

            if dry_run:
                for push_token_row in push_tokens:
                    try:
                        self._ensure_push_sender_configured(push_token_row.get("push_platform"))
                    except Exception as e:
                        Logger.error(
                            f"YouTubeLiveNotificationService: dry-run push config check failed "
                            f"for user={user_id} token_id={push_token_row.get('push_token_id')} "
                            f"event={event_id}: {e}"
                        )
                        summary["push_errors"] += 1
                        summary["errors"] += 1
                        continue
                    summary["push_would_send"] += 1
                continue

            try:
                notification_id = self._record_notification(
                    user_id=user_id,
                    comedian_id=comedian_uuid,
                    youtube_channel_id=youtube_channel_id,
                    youtube_video_id=youtube_video_id,
                    video_title=video_title,
                    video_url=video_url,
                    youtube_websub_event_id=event_id,
                )
            except Exception as e:
                Logger.error(
                    f"YouTubeLiveNotificationService: failed to record notification "
                    f"for user={user_id} event={event_id}: {e}"
                )
                summary["push_errors"] += 1
                summary["errors"] += 1
                continue

            if notification_id is None:
                summary["duplicates"] += 1
                continue

            for push_token_row in push_tokens:
                push_token_id = push_token_row.get("push_token_id")
                push_token = push_token_row.get("push_token")
                push_platform = push_token_row.get("push_platform")

                if not push_token_id or not push_token:
                    Logger.warn(
                        f"YouTubeLiveNotificationService: skipping user={user_id} "
                        f"event={event_id}: candidate missing active device token"
                    )
                    summary["push_errors"] += 1
                    summary["errors"] += 1
                    continue

                try:
                    result = self._send_push_notification(
                        platform=push_platform,
                        device_token=push_token,
                        comedian_id=comedian_uuid,
                        comedian_name=comedian_name,
                        youtube_channel_id=youtube_channel_id,
                        youtube_video_id=youtube_video_id,
                        video_title=video_title,
                        watch_url=video_url,
                    )
                except Exception as e:
                    Logger.error(
                        f"YouTubeLiveNotificationService: failed to send push to user={user_id} "
                        f"token_id={push_token_id} event={event_id}: {e}"
                    )
                    self._record_delivery(
                        youtube_live_notification_id=notification_id,
                        push_token_id=push_token_id,
                        platform=push_platform,
                        status="failed",
                        status_code=None,
                        failure_reason=str(e),
                    )
                    summary["push_errors"] += 1
                    summary["errors"] += 1
                    continue

                if result.success:
                    self._record_delivery(
                        youtube_live_notification_id=notification_id,
                        push_token_id=push_token_id,
                        platform=push_platform,
                        status="sent",
                        status_code=result.status_code,
                        failure_reason=None,
                    )
                    summary["push_sent"] += 1
                    continue

                self._record_delivery(
                    youtube_live_notification_id=notification_id,
                    push_token_id=push_token_id,
                    platform=push_platform,
                    status="failed",
                    status_code=result.status_code,
                    failure_reason=result.reason,
                )
                if result.invalid_token:
                    self._deactivate_push_token(
                        token_id=push_token_id,
                        reason=result.reason or "unknown",
                        status_code=result.status_code or 0,
                    )
                summary["push_errors"] += 1
                summary["errors"] += 1

        Logger.info(
            f"YouTubeLiveNotificationService: done — candidates={summary['candidates']} "
            f"push_would_send={summary['push_would_send']} push_sent={summary['push_sent']} "
            f"push_errors={summary['push_errors']} duplicates={summary['duplicates']} "
            f"errors={summary['errors']}"
        )
        return summary

    def _merge_same_youtube_live_candidates(self, rows: list[dict]) -> list[dict]:
        merged: dict[tuple[object, object, object, object], dict] = {}
        for row in rows:
            key = (
                row["event_id"],
                row["user_id"],
                row["comedian_uuid"],
                row["youtube_video_id"],
            )
            existing = merged.get(key)
            token_row = {
                "push_token_id": row.get("push_token_id"),
                "push_token": row.get("push_token"),
                "push_platform": row.get("push_platform"),
            }
            if existing is None:
                merged_row = dict(row)
                merged_row["push_tokens"] = [token_row]
                merged[key] = merged_row
                continue
            existing["push_tokens"].append(token_row)
        return list(merged.values())

    def _is_global_enabled(self) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_YOUTUBE_LIVE_GLOBAL_ENABLED_SQL)
                row = cur.fetchone()
        return bool(row and row[0])

    def _fetch_candidates(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_YOUTUBE_LIVE_CANDIDATES_SQL, (limit,))
                cols = [d[0] for d in cur.description]
                for raw in cur.fetchall():
                    rows.append(dict(zip(cols, raw)))
        return rows

    def _resolve_push_sender(self, platform: str | None):
        if platform == "android":
            if self._fcm_sender is None:
                self._fcm_sender = FcmPushService.from_env()
            return self._fcm_sender
        if self._push_sender is None:
            self._push_sender = ApnsPushService.from_env()
        return self._push_sender

    def _ensure_push_sender_configured(self, platform: str | None = None) -> None:
        self._resolve_push_sender(platform)

    def _send_push_notification(
        self,
        platform: str | None,
        device_token: str,
        comedian_id: str,
        comedian_name: str,
        youtube_channel_id: str,
        youtube_video_id: str,
        video_title: str | None,
        watch_url: str,
    ) -> PushDeliveryResult:
        sender = self._resolve_push_sender(platform)
        return sender.send_youtube_live_notification(
            device_token=device_token,
            comedian_id=comedian_id,
            comedian_name=comedian_name,
            youtube_channel_id=youtube_channel_id,
            youtube_video_id=youtube_video_id,
            video_title=video_title,
            watch_url=watch_url,
        )

    def _record_notification(
        self,
        user_id: str,
        comedian_id: str,
        youtube_channel_id: str,
        youtube_video_id: str,
        video_title: str | None,
        video_url: str,
        youtube_websub_event_id: int,
    ) -> int | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_YOUTUBE_LIVE_NOTIFICATION_SQL,
                    (
                        user_id,
                        comedian_id,
                        youtube_channel_id,
                        youtube_video_id,
                        video_title,
                        video_url,
                        youtube_websub_event_id,
                    ),
                )
                row = cur.fetchone()
        return int(row[0]) if row else None

    def _record_delivery(
        self,
        youtube_live_notification_id: int,
        push_token_id: str,
        platform: str | None,
        status: str,
        status_code: int | None,
        failure_reason: str | None,
    ) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_YOUTUBE_LIVE_DELIVERY_SQL,
                    (
                        youtube_live_notification_id,
                        push_token_id,
                        platform,
                        status,
                        status_code,
                        failure_reason,
                    ),
                )

    def _deactivate_push_token(self, token_id: str, reason: str, status_code: int) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_DEACTIVATE_PUSH_TOKEN_SQL, (token_id,))
        Logger.warn(
            f"YouTubeLiveNotificationService: deactivated push token id={token_id} "
            f"after push status={status_code} reason={reason}"
        )


class ComedianArrivalNotificationService:
    """Sends notification emails when a favorited comedian has a nearby upcoming show."""

    def __init__(
        self,
        zip_distance: ZipCodeDistance | None = None,
        push_sender: object | None = None,
        fcm_sender: object | None = None,
    ):
        self._zip_distance = zip_distance or ZipCodeDistance()
        # APNs sender (iOS tokens). Name kept for backwards-compat with the
        # existing test seam that injects via push_sender=.
        self._push_sender = push_sender
        # FCM sender (Android tokens), lazily built from env when first needed.
        self._fcm_sender = fcm_sender

    def _merge_same_show_candidates(self, rows: list[dict]) -> list[dict]:
        """Collapse multiple followed comedians on the same show into one candidate."""
        merged: dict[tuple[object, object, object, object], dict] = {}
        for row in rows:
            notification_type = row.get("notification_type") or "email"
            push_token_id = row.get("push_token_id") if notification_type == "push" else None
            key = (row["user_id"], row["show_id"], notification_type, push_token_id)
            existing = merged.get(key)
            if existing is None:
                merged_row = dict(row)
                merged_row["comedian_uuids"] = [row["comedian_uuid"]]
                merged_row["comedian_names"] = [row["comedian_name"]]
                merged[key] = merged_row
                continue

            if row["comedian_uuid"] not in existing["comedian_uuids"]:
                existing["comedian_uuids"].append(row["comedian_uuid"])
            if row["comedian_name"] not in existing["comedian_names"]:
                existing["comedian_names"].append(row["comedian_name"])

        return list(merged.values())

    def run(
        self,
        radius_miles: float = 50.0,
        days_ahead: int | None = None,
        discovered_within_days: int = 7,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Query newly discovered future shows and send notifications for matches
        within each user's radius.

        radius_miles is the fallback radius for profiles without a stored
        nearby_distance_miles preference.
        days_ahead is accepted for backward compatibility but no longer limits
        notification eligibility. discovered_within_days is a bounded catch-up
        window for newly discovered shows whose first notification run was missed.
        dry_run counts deliverable notifications without sending or recording them.

        Returns a summary dict with email and push delivery counts.
        """
        summary = {
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

        Logger.info(
            f"ComedianArrivalNotificationService: starting run "
            f"(radius={radius_miles} miles, discovered_within_days={discovered_within_days}, "
            f"dry_run={dry_run})"
        )

        try:
            rows = self._fetch_candidates(discovered_within_days=discovered_within_days)
        except Exception as e:
            Logger.error(f"ComedianArrivalNotificationService: failed to fetch candidates: {e}")
            summary["errors"] += 1
            return summary

        raw_candidate_count = len(rows)
        rows = self._merge_same_show_candidates(rows)

        summary["candidates"] = len(rows)
        summary["push_candidates"] = sum(1 for row in rows if row.get("notification_type") == "push")
        Logger.info(
            f"ComedianArrivalNotificationService: {len(rows)} candidate notification(s) before distance filter "
            f"(raw_rows={raw_candidate_count}, push_candidates={summary['push_candidates']})"
        )

        # Emails send per-show inline below; push sends are deferred and grouped
        # per (user, device token) after the loop, so a run's burst of shows for
        # one user collapses into a single push instead of one-per-show spam.
        push_groups: dict[tuple[object, object], dict] = {}
        # One notification_group_id per (user, run), shared by that user's push and
        # email records so the notification center can group them back together.
        run_group_ids: dict[object, str] = {}

        for row in rows:
            notification_type = row.get("notification_type") or "email"
            user_id = row["user_id"]
            user_email = row["user_email"]
            user_name = row["user_name"] or ""
            user_zip = row["user_zip"] or ""
            effective_radius_miles = self._effective_radius_miles(row, radius_miles)
            comedian_uuid = row["comedian_uuids"][0] if row.get("comedian_uuids") else row["comedian_uuid"]
            comedian_name = _format_comedian_names(row.get("comedian_names") or [row["comedian_name"]])
            show_id = row["show_id"]
            show_date = row["show_date"]
            show_page_url = row["show_page_url"] or ""
            club_name = row["club_name"]
            club_city = row["club_city"] or ""
            club_state = row["club_state"] or ""
            club_zip = row["club_zip"] or ""
            club_timezone = row.get("club_timezone")
            # Rich-push headshot source: the primary (first) comedian; the actual
            # image URL is built per group in _process_push_group.
            primary_comedian_name = (row.get("comedian_names") or [row["comedian_name"]])[0]
            push_token_id = row.get("push_token_id")
            push_token = row.get("push_token")
            push_platform = row.get("push_platform")

            # Distance check
            distance = self._zip_distance.distance_miles(user_zip, club_zip)
            if distance is None:
                Logger.warn(
                    f"ComedianArrivalNotificationService: skipping user={user_id} show={show_id} "
                    f"— could not compute distance for zips {user_zip!r}/{club_zip!r}"
                )
                summary["distance_filtered"] += 1
                if notification_type == "push":
                    summary["push_filtered"] += 1
                continue

            if distance > effective_radius_miles:
                Logger.info(
                    f"ComedianArrivalNotificationService: skipping user={user_id} show={show_id} "
                    f"comedian={comedian_name!r} — distance {distance:.1f} miles exceeds radius "
                    f"{effective_radius_miles} miles"
                )
                summary["distance_filtered"] += 1
                if notification_type == "push":
                    summary["push_filtered"] += 1
                continue

            if notification_type == "push":
                if not push_token_id or not push_token:
                    Logger.warn(
                        f"ComedianArrivalNotificationService: skipping push for user={user_id} show={show_id}: "
                        "candidate missing active device token"
                    )
                    summary["push_errors"] += 1
                    summary["errors"] += 1
                    continue
                # Defer: accumulate this show under the user's device token and
                # send one grouped push after the loop (see _process_push_group).
                group = push_groups.setdefault(
                    (user_id, push_token_id),
                    {
                        "user_id": user_id,
                        "push_token": push_token,
                        "push_token_id": push_token_id,
                        "push_platform": push_platform,
                        "events": [],
                    },
                )
                group["events"].append(
                    {
                        "comedian_uuid": comedian_uuid,
                        "comedian_name": comedian_name,
                        "comedian_names": row.get("comedian_names") or [row["comedian_name"]],
                        "primary_comedian_name": primary_comedian_name,
                        "comedian_avatar_path": row.get("comedian_avatar_path"),
                        "comedian_has_image": row.get("comedian_has_image"),
                        "show_id": show_id,
                        "show_date": show_date,
                        "show_page_url": show_page_url,
                        "club_name": club_name,
                        "club_city": club_city,
                        "club_state": club_state,
                        "club_timezone": club_timezone,
                        "distance": distance,
                        "effective_radius_miles": effective_radius_miles,
                    }
                )
                continue

            # Email path — one send per show (unchanged; only push is grouped).
            if dry_run:
                summary["emails_would_send"] += 1
                Logger.info(
                    f"ComedianArrivalNotificationService: dry-run would send email to user={user_id} "
                    f"comedian={comedian_name!r} show={show_id} distance={distance:.1f} miles "
                    f"radius={effective_radius_miles} miles"
                )
                continue
            try:
                self._send_notification(
                    user_email=user_email,
                    user_name=user_name,
                    comedian_name=comedian_name,
                    show_date=show_date,
                    club_name=club_name,
                    club_city=club_city,
                    club_state=club_state,
                    show_page_url=show_page_url,
                )
            except Exception as e:
                Logger.error(
                    f"ComedianArrivalNotificationService: failed to send email "
                    f"to user={user_id} show={show_id}: {e}"
                )
                summary["errors"] += 1
                continue

            try:
                self._record_notification(
                    user_id=user_id,
                    comedian_id=comedian_uuid,
                    show_id=show_id,
                    notification_type="email",
                    notification_group_id=_notification_group_id(run_group_ids, user_id),
                )
            except Exception as e:
                Logger.error(
                    f"ComedianArrivalNotificationService: failed to record email notification "
                    f"for user={user_id} show={show_id}: {e}"
                )
                summary["errors"] += 1
                continue

            Logger.info(
                f"ComedianArrivalNotificationService: sent email notification to user={user_id} "
                f"comedian={comedian_name!r} show={show_id} distance={distance:.1f} miles "
                f"radius={effective_radius_miles} miles"
            )
            summary["emails_sent"] += 1

        # Grouped push delivery: one push per (user, device token) covering all of
        # this run's in-range shows for that user.
        for group in push_groups.values():
            self._process_push_group(group, summary=summary, dry_run=dry_run, group_ids=run_group_ids)

        Logger.info(
            f"ComedianArrivalNotificationService: done — "
            f"candidates={summary['candidates']} distance_filtered={summary['distance_filtered']} "
            f"emails_would_send={summary['emails_would_send']} emails_sent={summary['emails_sent']} "
            f"push_candidates={summary['push_candidates']} push_filtered={summary['push_filtered']} "
            f"push_would_send={summary['push_would_send']} push_sent={summary['push_sent']} "
            f"push_errors={summary['push_errors']} errors={summary['errors']}"
        )
        return summary

    def _process_push_group(self, group: dict, summary: dict, dry_run: bool, group_ids: dict) -> None:
        """Send one grouped push for a (user, device token) and record every show.

        A single-show group keeps the existing per-show copy (the sender builds
        "{comedian} is performing near you" / "{club} on {date} at {time}"). A
        multi-show group passes a precomputed tiered title/body from
        _build_grouped_push_copy. Either way every show is recorded so future
        runs don't re-notify (the candidate dedup keys on (user, show, 'push')).
        """
        user_id = group["user_id"]
        push_token = group["push_token"]
        push_token_id = group["push_token_id"]
        push_platform = group["push_platform"]
        # Soonest show first; any show without a date sorts last.
        events = sorted(
            group["events"],
            key=lambda e: (e.get("show_date") is None, e.get("show_date")),
        )
        if not events:
            return
        show_ids = [event["show_id"] for event in events]

        if dry_run:
            try:
                self._ensure_push_sender_configured(push_platform)
            except Exception as e:
                Logger.error(
                    f"ComedianArrivalNotificationService: dry-run push config check failed "
                    f"for user={user_id} token_id={push_token_id} shows={show_ids}: {e}"
                )
                summary["push_errors"] += 1
                summary["errors"] += 1
                return
            summary["push_would_send"] += 1
            Logger.info(
                f"ComedianArrivalNotificationService: dry-run would send grouped push to user={user_id} "
                f"shows={show_ids} ({len(events)} show(s))"
            )
            return

        primary = events[0]
        grouped = len(events) > 1
        # One show → sender builds the single-show copy and the tap opens that show.
        # Many → tiered copy + route the tap to the Favorites tab (which renders
        # upcoming shows from followed comedians). showId below stays as the
        # older-client fallback.
        title, body = _build_grouped_push_copy(events) if grouped else (None, None)
        route = "favorites" if grouped else None
        # Show ids let the Favorites tab scope to just this push's shows.
        show_ids = ",".join(str(event["show_id"]) for event in events) if grouped else None
        comedian_image_url = _build_comedian_image_url(
            primary.get("comedian_avatar_path"),
            primary.get("primary_comedian_name"),
            primary.get("comedian_has_image"),
        )

        try:
            result = self._send_push_notification(
                platform=push_platform,
                device_token=push_token,
                comedian_name=primary["comedian_name"],
                # Soonest show is the deep-link fallback every current client
                # understands (grouped tap → soonest show) until client routing
                # learns comedian/favorites destinations.
                show_id=primary["show_id"],
                show_date=primary["show_date"],
                club_name=primary["club_name"],
                club_city=primary["club_city"],
                club_state=primary["club_state"],
                show_page_url=primary["show_page_url"],
                club_timezone=primary["club_timezone"],
                comedian_image_url=comedian_image_url,
                title=title,
                body=body,
                route=route,
                show_ids=show_ids,
            )
        except Exception as e:
            Logger.error(
                f"ComedianArrivalNotificationService: failed to send push to user={user_id} "
                f"token_id={push_token_id} shows={show_ids}: {e}"
            )
            summary["push_errors"] += 1
            summary["errors"] += 1
            return
        if not result.success:
            Logger.warn(
                f"ComedianArrivalNotificationService: push failed for user={user_id} "
                f"token_id={push_token_id} shows={show_ids} status={result.status_code} reason={result.reason}"
            )
            if result.invalid_token:
                self._deactivate_push_token(
                    token_id=push_token_id,
                    reason=result.reason or "unknown",
                    status_code=result.status_code or 0,
                )
            summary["push_errors"] += 1
            summary["errors"] += 1
            return

        group_id = _notification_group_id(group_ids, user_id)
        record_failed = False
        for event in events:
            try:
                self._record_notification(
                    user_id=user_id,
                    comedian_id=event["comedian_uuid"],
                    show_id=event["show_id"],
                    notification_type="push",
                    notification_group_id=group_id,
                )
            except Exception as e:
                Logger.error(
                    f"ComedianArrivalNotificationService: failed to record push notification "
                    f"for user={user_id} show={event['show_id']}: {e}"
                )
                record_failed = True
        if record_failed:
            summary["push_errors"] += 1
            summary["errors"] += 1

        summary["push_sent"] += 1
        Logger.info(
            f"ComedianArrivalNotificationService: sent grouped push to user={user_id} "
            f"shows={show_ids} ({len(events)} show(s))"
        )

    def _effective_radius_miles(self, row: dict, fallback_radius_miles: float) -> float:
        profile_radius = row.get("nearby_distance_miles")
        if profile_radius is None:
            return fallback_radius_miles
        return float(profile_radius)

    def _fetch_candidates(self, days_ahead: int | None = None, discovered_within_days: int = 7) -> list:
        """Fetch all candidate rows from the DB."""
        rows = []
        with get_connection() as conn:
            with conn.cursor() as cur:
                # psycopg2 does not allow %s inside a string literal in mogrify-style
                # substitution, so we use Python string formatting for INTERVAL values
                # after coercing them to ints.
                discovered_within_days = int(discovered_within_days)
                sql = _CANDIDATES_SQL % (
                    discovered_within_days,
                    discovered_within_days,
                )
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                for raw in cur.fetchall():
                    rows.append(dict(zip(cols, raw)))
        return rows

    def _send_notification(
        self,
        user_email: str,
        user_name: str,
        comedian_name: str,
        show_date: object,
        club_name: str,
        club_city: str,
        club_state: str,
        show_page_url: str,
    ) -> None:
        """Build and send the notification email."""
        html = _build_email_html(
            comedian_name=comedian_name,
            show_date=show_date,
            club_name=club_name,
            club_city=club_city,
            club_state=club_state,
            show_page_url=show_page_url,
        )
        text = _build_email_text(
            comedian_name=comedian_name,
            show_date=show_date,
            club_name=club_name,
            club_city=club_city,
            club_state=club_state,
            show_page_url=show_page_url,
        )
        message = EmailMessage(
            to_emails=user_email,
            subject=(
                f"{comedian_name} "
                f"{'are' if _is_plural_comedian_label(comedian_name) else 'is'} "
                "performing near you!"
            ),
            html_content=html,
            text_content=text,
        )
        EmailService.send_email(message)

    def _resolve_push_sender(self, platform: str | None):
        """Return the sender for a token's platform, building it from env once.

        android -> FCM (HTTP v1); anything else (ios, or legacy NULL) -> APNs.
        Both senders expose the same send_show_notification(...) contract.
        """
        if platform == "android":
            if self._fcm_sender is None:
                self._fcm_sender = FcmPushService.from_env()
            return self._fcm_sender
        if self._push_sender is None:
            self._push_sender = ApnsPushService.from_env()
        return self._push_sender

    def _send_push_notification(
        self,
        platform: str | None,
        device_token: str,
        comedian_name: str,
        show_id: int,
        show_date: object,
        club_name: str,
        club_city: str,
        club_state: str,
        show_page_url: str,
        club_timezone: str | None = None,
        comedian_image_url: str | None = None,
        title: str | None = None,
        body: str | None = None,
        route: str | None = None,
        show_ids: str | None = None,
    ) -> PushDeliveryResult:
        sender = self._resolve_push_sender(platform)
        return sender.send_show_notification(
            device_token=device_token,
            comedian_name=comedian_name,
            show_id=show_id,
            show_date=show_date,
            club_name=club_name,
            club_city=club_city,
            club_state=club_state,
            show_page_url=show_page_url,
            club_timezone=club_timezone,
            comedian_image_url=comedian_image_url,
            title=title,
            body=body,
            route=route,
            show_ids=show_ids,
        )

    def _ensure_push_sender_configured(self, platform: str | None = None) -> None:
        self._resolve_push_sender(platform)

    def _record_notification(
        self,
        user_id: str,
        comedian_id: str,
        show_id: int,
        notification_type: str = "email",
        notification_group_id: str | None = None,
    ) -> None:
        """Insert a SentNotification record to prevent duplicate deliveries per channel."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_SENT_NOTIFICATION_SQL,
                    (user_id, comedian_id, show_id, notification_type, notification_group_id),
                )

    def _deactivate_push_token(self, token_id: str, reason: str, status_code: int) -> None:
        """Deactivate a device token rejected by APNs as invalid or expired."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_DEACTIVATE_PUSH_TOKEN_SQL, (token_id,))
        Logger.warn(
            f"ComedianArrivalNotificationService: deactivated push token id={token_id} "
            f"after APNs status={status_code} reason={reason}"
        )
