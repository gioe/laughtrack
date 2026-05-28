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
import time
from dataclasses import dataclass
from typing import Dict

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
    {notification_type_sql} AS notification_type,
    {push_token_id_sql} AS push_token_id,
    {push_token_sql} AS push_token
FROM users u
JOIN user_profiles up ON up.user_id = u.id
JOIN favorite_comedians fc ON fc.profile_id = up.id
JOIN comedians c ON c.uuid = fc.comedian_id
JOIN lineup_items li ON li.comedian_id = c.uuid AND li.show_id IN (
    SELECT s2.id FROM shows s2
    WHERE s2.date >= NOW()
      AND s2.date <= NOW() + INTERVAL '%s days'
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
        AND sn.comedian_id = c.uuid
        AND sn.show_id = s.id
        AND sn.notification_type = 'email'
  )
"""

_EMAIL_CANDIDATES_SQL = _BASE_CANDIDATES_SELECT_SQL.format(
    notification_type_sql="'email'",
    push_token_id_sql="NULL",
    push_token_sql="NULL",
    push_join_sql="",
)

_PUSH_CANDIDATES_SQL = _BASE_CANDIDATES_SELECT_SQL.format(
    notification_type_sql="'push'",
    push_token_id_sql="upt.id",
    push_token_sql="upt.token",
    push_join_sql="JOIN user_push_tokens upt ON upt.user_id = u.id AND upt.profile_id = up.id AND upt.is_active = true",
).replace("up.email_show_notifications = true", "up.push_show_notifications = true").replace(
    "sn.notification_type = 'email'", "sn.notification_type = 'push'"
)

_CANDIDATES_SQL = f"""
{_EMAIL_CANDIDATES_SQL}
UNION ALL
{_PUSH_CANDIDATES_SQL}
ORDER BY user_id, show_date, comedian_name, notification_type, push_token_id
"""

_INSERT_SENT_NOTIFICATION_SQL = """
INSERT INTO sent_notifications (user_id, comedian_id, show_id, notification_type, sent_at)
VALUES (%s, %s, %s, %s, NOW())
ON CONFLICT (user_id, comedian_id, show_id, notification_type) DO NOTHING
"""

_DEACTIVATE_PUSH_TOKEN_SQL = """
UPDATE user_push_tokens
SET is_active = false,
    revoked_at = NOW(),
    updated_at = NOW()
WHERE id = %s
"""

_INVALID_APNS_REASONS = {
    "BadDeviceToken",
    "DeviceTokenNotForTopic",
    "Unregistered",
}


# %-formatted (not f-string) so DB-sourced values can only enter the template
# through the explicit html.escape()-wrapped substitution dict below.
_EMAIL_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">%(e_comedian)s is performing near you!</h2>
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
        '<p><a href="%s" style="color:#1a73e8;">View show and buy tickets</a></p>'
        % html_module.escape(show_page_url)
        if show_page_url
        else ""
    )
    return _EMAIL_HTML_TEMPLATE % {
        "e_comedian": e_comedian,
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
    lines = [
        f"{comedian_name} is performing near you!",
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
    ) -> PushDeliveryResult:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("APNs push delivery requires httpx with HTTP/2 support") from e

        title = f"{comedian_name} is performing near you"
        location = ", ".join(filter(None, [club_city, club_state]))
        body = f"{club_name}"
        if location:
            body = f"{body} in {location}"

        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "sound": "default",
            },
            "showId": show_id,
            "url": show_page_url,
        }
        if hasattr(show_date, "isoformat"):
            payload["showDate"] = show_date.isoformat()

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


class ComedianArrivalNotificationService:
    """Sends notification emails when a favorited comedian has a nearby upcoming show."""

    def __init__(self, zip_distance: ZipCodeDistance | None = None, push_sender: object | None = None):
        self._zip_distance = zip_distance or ZipCodeDistance()
        self._push_sender = push_sender

    def run(self, radius_miles: float = 50.0, days_ahead: int = 30) -> Dict[str, int]:
        """
        Query candidates and send emails for matches within each user's radius.

        radius_miles is the fallback radius for profiles without a stored
        nearby_distance_miles preference.

        Returns a summary dict with email and push delivery counts.
        """
        summary = {
            "candidates": 0,
            "distance_filtered": 0,
            "emails_sent": 0,
            "errors": 0,
            "push_candidates": 0,
            "push_filtered": 0,
            "push_sent": 0,
            "push_errors": 0,
        }

        Logger.info(
            f"ComedianArrivalNotificationService: starting run "
            f"(radius={radius_miles} miles, days_ahead={days_ahead})"
        )

        try:
            rows = self._fetch_candidates(days_ahead)
        except Exception as e:
            Logger.error(f"ComedianArrivalNotificationService: failed to fetch candidates: {e}")
            summary["errors"] += 1
            return summary

        summary["candidates"] = len(rows)
        summary["push_candidates"] = sum(1 for row in rows if row.get("notification_type") == "push")
        Logger.info(
            f"ComedianArrivalNotificationService: {len(rows)} candidate row(s) before distance filter "
            f"(push_candidates={summary['push_candidates']})"
        )

        for row in rows:
            notification_type = row.get("notification_type") or "email"
            user_id = row["user_id"]
            user_email = row["user_email"]
            user_name = row["user_name"] or ""
            user_zip = row["user_zip"] or ""
            effective_radius_miles = self._effective_radius_miles(row, radius_miles)
            comedian_uuid = row["comedian_uuid"]
            comedian_name = row["comedian_name"]
            show_id = row["show_id"]
            show_date = row["show_date"]
            show_page_url = row["show_page_url"] or ""
            club_name = row["club_name"]
            club_city = row["club_city"] or ""
            club_state = row["club_state"] or ""
            club_zip = row["club_zip"] or ""
            push_token_id = row.get("push_token_id")
            push_token = row.get("push_token")

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
                try:
                    result = self._send_push_notification(
                        device_token=push_token,
                        comedian_name=comedian_name,
                        show_id=show_id,
                        show_date=show_date,
                        club_name=club_name,
                        club_city=club_city,
                        club_state=club_state,
                        show_page_url=show_page_url,
                    )
                except Exception as e:
                    Logger.error(
                        f"ComedianArrivalNotificationService: failed to send push to user={user_id} "
                        f"token_id={push_token_id} show={show_id}: {e}"
                    )
                    summary["push_errors"] += 1
                    summary["errors"] += 1
                    continue
                if not result.success:
                    Logger.warn(
                        f"ComedianArrivalNotificationService: push failed for user={user_id} "
                        f"token_id={push_token_id} show={show_id} status={result.status_code} reason={result.reason}"
                    )
                    if result.invalid_token:
                        self._deactivate_push_token(
                            token_id=push_token_id,
                            reason=result.reason or "unknown",
                            status_code=result.status_code or 0,
                        )
                    summary["push_errors"] += 1
                    summary["errors"] += 1
                    continue
            else:
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

            # Record sent notification
            try:
                self._record_notification(
                    user_id=user_id,
                    comedian_id=comedian_uuid,
                    show_id=show_id,
                    notification_type=notification_type,
                )
            except Exception as e:
                Logger.error(
                    f"ComedianArrivalNotificationService: failed to record {notification_type} notification "
                    f"for user={user_id} show={show_id}: {e}"
                )
                summary["errors"] += 1
                if notification_type == "push":
                    summary["push_errors"] += 1
                continue

            Logger.info(
                f"ComedianArrivalNotificationService: sent {notification_type} notification to user={user_id} "
                f"comedian={comedian_name!r} show={show_id} distance={distance:.1f} miles "
                f"radius={effective_radius_miles} miles"
            )
            if notification_type == "push":
                summary["push_sent"] += 1
            else:
                summary["emails_sent"] += 1

        Logger.info(
            f"ComedianArrivalNotificationService: done — "
            f"candidates={summary['candidates']} distance_filtered={summary['distance_filtered']} "
            f"emails_sent={summary['emails_sent']} push_candidates={summary['push_candidates']} "
            f"push_filtered={summary['push_filtered']} push_sent={summary['push_sent']} "
            f"push_errors={summary['push_errors']} errors={summary['errors']}"
        )
        return summary

    def _effective_radius_miles(self, row: dict, fallback_radius_miles: float) -> float:
        profile_radius = row.get("nearby_distance_miles")
        if profile_radius is None:
            return fallback_radius_miles
        return float(profile_radius)

    def _fetch_candidates(self, days_ahead: int) -> list:
        """Fetch all candidate rows from the DB."""
        rows = []
        with get_connection() as conn:
            with conn.cursor() as cur:
                # psycopg2 does not allow %s inside a string literal in mogrify-style
                # substitution, so we use Python string formatting for the INTERVAL value
                # (days_ahead is always an int — no injection risk).
                sql = _CANDIDATES_SQL % (days_ahead, days_ahead)
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
            subject=f"{comedian_name} is performing near you!",
            html_content=html,
            text_content=text,
        )
        EmailService.send_email(message)

    def _send_push_notification(
        self,
        device_token: str,
        comedian_name: str,
        show_id: int,
        show_date: object,
        club_name: str,
        club_city: str,
        club_state: str,
        show_page_url: str,
    ) -> PushDeliveryResult:
        sender = self._push_sender
        if sender is None:
            sender = ApnsPushService.from_env()
            self._push_sender = sender
        return sender.send_show_notification(
            device_token=device_token,
            comedian_name=comedian_name,
            show_id=show_id,
            show_date=show_date,
            club_name=club_name,
            club_city=club_city,
            club_state=club_state,
            show_page_url=show_page_url,
        )

    def _record_notification(
        self,
        user_id: str,
        comedian_id: str,
        show_id: int,
        notification_type: str = "email",
    ) -> None:
        """Insert a SentNotification record to prevent duplicate deliveries per channel."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_INSERT_SENT_NOTIFICATION_SQL, (user_id, comedian_id, show_id, notification_type))

    def _deactivate_push_token(self, token_id: str, reason: str, status_code: int) -> None:
        """Deactivate a device token rejected by APNs as invalid or expired."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_DEACTIVATE_PUSH_TOKEN_SQL, (token_id,))
        Logger.warn(
            f"ComedianArrivalNotificationService: deactivated push token id={token_id} "
            f"after APNs status={status_code} reason={reason}"
        )
