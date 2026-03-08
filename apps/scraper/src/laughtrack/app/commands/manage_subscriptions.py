"""CLI for managing email subscription tracking.

Subcommands:
  list  — print clubs that lack an active EmailSubscription record
  add   — insert or update an EmailSubscription row for a club
"""

import argparse
import sys

from laughtrack.adapters.db import db


def cmd_list() -> None:
    """Print clubs without an active EmailSubscription."""
    sql = """
        SELECT c.id, c.name
        FROM clubs c
        LEFT JOIN email_subscriptions es
               ON es.club_id = c.id AND es.subscribed = true
        WHERE es.club_id IS NULL
        ORDER BY c.name
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    if not rows:
        print("All clubs have an active email subscription.")
        return

    print(f"{'ID':<8} Name")
    print("-" * 40)
    for club_id, name in rows:
        print(f"{club_id:<8} {name}")


def cmd_add(club_id: int, sender_domain: str) -> None:
    """Insert or update an EmailSubscription row."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Validate club exists
            cur.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
            row = cur.fetchone()
            if row is None:
                print(f"Error: club_id {club_id} not found.", file=sys.stderr)
                sys.exit(1)
            club_name = row[0]

            # Upsert
            cur.execute(
                """
                INSERT INTO email_subscriptions (club_id, sender_domain, subscribed)
                VALUES (%s, %s, true)
                ON CONFLICT (club_id) DO UPDATE
                    SET sender_domain = EXCLUDED.sender_domain,
                        subscribed    = true
                """,
                (club_id, sender_domain),
            )

    print(f"Subscription saved: club '{club_name}' (id={club_id}), sender_domain='{sender_domain}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage_subscriptions",
        description="Manage email subscription tracking for clubs.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser(
        "list",
        help="Print clubs that do not have an active EmailSubscription record.",
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Insert or update an EmailSubscription row for a club.",
    )
    add_parser.add_argument("club_id", type=int, help="Club ID (must exist in the DB).")
    add_parser.add_argument("sender_domain", help="Email sender domain (e.g. comedycellar.com).")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "list":
        cmd_list()
    elif args.subcommand == "add":
        cmd_add(args.club_id, args.sender_domain)


if __name__ == "__main__":
    main()
