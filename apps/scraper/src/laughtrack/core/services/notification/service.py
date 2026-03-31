"""Comedian arrival notification service.

Queries upcoming shows where a user's favorited comedian is in the lineup,
filters by distance from user's zip code to club's zip code, sends notification
emails, and records sent notifications to prevent duplicates.
"""

from __future__ import annotations

import html as html_module
from typing import Dict

from laughtrack.core.data.db_connection import get_connection
from laughtrack.core.entities.email.local.email_models import EmailMessage
from laughtrack.core.services.notification.geo import ZipCodeDistance
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.email.service import EmailService

_CANDIDATES_SQL = """
SELECT
    u.id          AS user_id,
    u.email       AS user_email,
    u.name        AS user_name,
    up.zip_code   AS user_zip,
    c.uuid        AS comedian_uuid,
    c.name        AS comedian_name,
    s.id          AS show_id,
    s.date        AS show_date,
    s.show_page_url,
    cl.name       AS club_name,
    cl.address    AS club_address,
    cl.city       AS club_city,
    cl.state      AS club_state,
    cl.zip_code   AS club_zip
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
ORDER BY u.id, s.date, c.name
"""

_INSERT_SENT_NOTIFICATION_SQL = """
INSERT INTO sent_notifications (user_id, comedian_id, show_id, notification_type, sent_at)
VALUES (%s, %s, %s, 'email', NOW())
ON CONFLICT (user_id, comedian_id, show_id, notification_type) DO NOTHING
"""


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
    ticket_line = (
        f'<p><a href="{html_module.escape(show_page_url)}" style="color:#1a73e8;">View show and buy tickets</a></p>'
        if show_page_url
        else ""
    )
    return f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #1a1a1a;">{e_comedian} is performing near you!</h2>
  <p>Great news — one of your favorite comedians has an upcoming show in your area.</p>
  <table style="width:100%; border-collapse:collapse; margin: 16px 0;">
    <tr>
      <td style="padding: 8px 0; font-weight: bold; width: 120px;">Comedian:</td>
      <td style="padding: 8px 0;">{e_comedian}</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; font-weight: bold;">Date:</td>
      <td style="padding: 8px 0;">{date_str}</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; font-weight: bold;">Venue:</td>
      <td style="padding: 8px 0;">{e_club}</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; font-weight: bold;">Location:</td>
      <td style="padding: 8px 0;">{e_location}</td>
    </tr>
  </table>
  {ticket_line}
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
  <p style="color: #666; font-size: 12px;">
    You're receiving this email because you follow {e_comedian} on LaughTrack and have
    enabled show notifications. To unsubscribe, visit your account settings at
    <a href="https://laugh-track.com">laugh-track.com</a>.
  </p>
</body>
</html>"""


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


class ComedianArrivalNotificationService:
    """Sends notification emails when a favorited comedian has a nearby upcoming show."""

    def __init__(self, zip_distance: ZipCodeDistance | None = None):
        self._zip_distance = zip_distance or ZipCodeDistance()

    def run(self, radius_miles: float = 50.0, days_ahead: int = 30) -> Dict[str, int]:
        """
        Query candidates and send emails for all matches within radius.

        Returns a summary dict: {"candidates": N, "distance_filtered": N, "emails_sent": N, "errors": N}
        """
        summary = {"candidates": 0, "distance_filtered": 0, "emails_sent": 0, "errors": 0}

        Logger.info(f"ComedianArrivalNotificationService: starting run (radius={radius_miles} miles, days_ahead={days_ahead})")

        try:
            rows = self._fetch_candidates(days_ahead)
        except Exception as e:
            Logger.error(f"ComedianArrivalNotificationService: failed to fetch candidates: {e}")
            summary["errors"] += 1
            return summary

        summary["candidates"] = len(rows)
        Logger.info(f"ComedianArrivalNotificationService: {len(rows)} candidate row(s) before distance filter")

        for row in rows:
            user_id = row["user_id"]
            user_email = row["user_email"]
            user_name = row["user_name"] or ""
            user_zip = row["user_zip"] or ""
            comedian_uuid = row["comedian_uuid"]
            comedian_name = row["comedian_name"]
            show_id = row["show_id"]
            show_date = row["show_date"]
            show_page_url = row["show_page_url"] or ""
            club_name = row["club_name"]
            club_city = row["club_city"] or ""
            club_state = row["club_state"] or ""
            club_zip = row["club_zip"] or ""

            # Distance check
            distance = self._zip_distance.distance_miles(user_zip, club_zip)
            if distance is None:
                Logger.warn(
                    f"ComedianArrivalNotificationService: skipping user={user_id} show={show_id} "
                    f"— could not compute distance for zips {user_zip!r}/{club_zip!r}"
                )
                summary["distance_filtered"] += 1
                continue

            if distance > radius_miles:
                Logger.info(
                    f"ComedianArrivalNotificationService: skipping user={user_id} show={show_id} "
                    f"comedian={comedian_name!r} — distance {distance:.1f} miles > radius {radius_miles} miles"
                )
                summary["distance_filtered"] += 1
                continue

            # Send email
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
                    f"ComedianArrivalNotificationService: failed to send email to user={user_id} show={show_id}: {e}"
                )
                summary["errors"] += 1
                continue

            # Record sent notification
            try:
                self._record_notification(
                    user_id=user_id,
                    comedian_id=comedian_uuid,
                    show_id=show_id,
                )
            except Exception as e:
                Logger.error(
                    f"ComedianArrivalNotificationService: failed to record notification for user={user_id} show={show_id}: {e}"
                )
                summary["errors"] += 1
                continue

            Logger.info(
                f"ComedianArrivalNotificationService: sent notification to user={user_id} "
                f"comedian={comedian_name!r} show={show_id} distance={distance:.1f} miles"
            )
            summary["emails_sent"] += 1

        Logger.info(
            f"ComedianArrivalNotificationService: done — "
            f"candidates={summary['candidates']} distance_filtered={summary['distance_filtered']} "
            f"emails_sent={summary['emails_sent']} errors={summary['errors']}"
        )
        return summary

    def _fetch_candidates(self, days_ahead: int) -> list:
        """Fetch all candidate rows from the DB."""
        rows = []
        with get_connection() as conn:
            with conn.cursor() as cur:
                # psycopg2 does not allow %s inside a string literal in mogrify-style
                # substitution, so we use Python string formatting for the INTERVAL value
                # (days_ahead is always an int — no injection risk).
                sql = _CANDIDATES_SQL % days_ahead
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

    def _record_notification(self, user_id: str, comedian_id: str, show_id: int) -> None:
        """Insert a SentNotification record to prevent duplicate emails."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_INSERT_SENT_NOTIFICATION_SQL, (user_id, comedian_id, show_id))
