#!/usr/bin/env python3
"""Send a diagnostic APNs notification to a LaughTrack user."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


SKILL_SCRIPT = Path(__file__).resolve()
REPO_ROOT = SKILL_SCRIPT.parents[4]
SCRAPER_ROOT = REPO_ROOT / "apps" / "scraper"
sys.path.insert(0, str(SCRAPER_ROOT))
sys.path.insert(0, str(SCRAPER_ROOT / "src"))

from laughtrack.core.services.notification.service import ApnsPushService  # noqa: E402
from laughtrack.infrastructure.database.connection import get_connection  # noqa: E402


DEFAULT_TITLE = "LaughTrack test notification"
DEFAULT_BODY = "If you can see this, push delivery is working."


@dataclass(frozen=True)
class Target:
    user_id: str
    email: str
    token_id: str | None
    token: str | None
    last_registered_at: object | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a diagnostic APNs notification to a user's newest active iOS token."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--email", help="Exact user email address (case-insensitive)")
    target.add_argument("--user-id", help="Exact users.id value")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Notification title")
    parser.add_argument("--body", default=DEFAULT_BODY, help="Notification body")
    return parser


def find_target(connection: object, *, email: str | None, user_id: str | None) -> Target | None:
    where_sql = "lower(u.email) = lower(%s)" if email else "u.id = %s"
    identifier = email if email else user_id
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                u.id,
                u.email,
                upt.id,
                upt.token,
                upt.last_registered_at
            FROM users u
            LEFT JOIN LATERAL (
                SELECT id, token, last_registered_at, created_at
                FROM user_push_tokens
                WHERE user_id = u.id
                  AND platform = 'ios'
                  AND is_active = true
                ORDER BY last_registered_at DESC, created_at DESC
                LIMIT 1
            ) upt ON true
            WHERE {where_sql}
            LIMIT 1
            """,
            (identifier,),
        )
        row = cursor.fetchone()

    if row is None:
        return None
    return Target(
        user_id=row[0],
        email=row[1],
        token_id=row[2],
        token=row[3],
        last_registered_at=row[4],
    )


def run(
    argv: Sequence[str] | None = None,
    *,
    connection_factory: Callable[..., object] = get_connection,
    service_factory: Callable[[], ApnsPushService] = ApnsPushService.from_env,
) -> int:
    args = build_parser().parse_args(argv)

    with connection_factory() as connection:
        target = find_target(connection, email=args.email, user_id=args.user_id)

    if target is None:
        identifier = args.email if args.email else args.user_id
        print(f"User not found: {identifier}", file=sys.stderr)
        return 2

    if not target.token or not target.token_id:
        print(
            f"No active iOS push token for user_id={target.user_id} email={target.email}; no push sent."
        )
        return 0

    result = service_factory().send_test_notification(
        device_token=target.token,
        title=args.title,
        body=args.body,
    )
    registered_at = (
        target.last_registered_at.isoformat()
        if hasattr(target.last_registered_at, "isoformat")
        else str(target.last_registered_at)
    )
    print(
        f"user_id={target.user_id} email={target.email} token_id={target.token_id} "
        f"last_registered_at={registered_at} success={result.success} "
        f"status_code={result.status_code} reason={result.reason or '-'}"
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(run())
