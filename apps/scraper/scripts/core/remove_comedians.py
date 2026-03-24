"""
Batch comedian removal tool.

Accepts comedian names (via --name or --names-file), checks the deny list,
shows a dry-run status table, and with --confirm deletes records and updates
the deny list.

Usage:
    cd apps/scraper

    # Dry-run (status table only, no DB changes):
    .venv/bin/python scripts/core/remove_comedians.py --name "John Doe"
    .venv/bin/python scripts/core/remove_comedians.py --names-file names.txt

    # Execute deletion:
    .venv/bin/python scripts/core/remove_comedians.py --name "John Doe" --confirm

Status table columns:
    FOUND        — comedian exists in comedians table (shows lineup_items count)
    NOT IN DB    — not found in comedians table (still added to deny list on --confirm)
    ALREADY DENIED — already in comedian_deny_list; skipped entirely

On --confirm:
    - Deletes lineup_items rows then comedian records in a single transaction
    - Adds FOUND + NOT IN DB names to comedian_deny_list (ON CONFLICT DO NOTHING)
    - ALREADY DENIED names are skipped (already handled)
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from laughtrack.infrastructure.database.connection import get_connection, get_transaction  # noqa: E402
from psycopg2.extras import execute_values  # noqa: E402


def _load_names_file(path: str) -> list:
    """Parse names from file: one per line, ignoring blank lines and # comments."""
    names = []
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            names.append(stripped)
    return names


def _check_deny_list(names: list) -> set:
    """Return the subset of *names* already present in comedian_deny_list."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM comedian_deny_list WHERE name = ANY(%s)",
                (names,),
            )
            return {row[0] for row in cur.fetchall()}


def _lookup_comedians(names: list) -> dict:
    """Return {name: {uuid, lineup_count}} for names found in comedians table."""
    if not names:
        return {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, c.uuid, COUNT(li.show_id) AS lineup_count
                FROM comedians c
                LEFT JOIN lineup_items li ON li.comedian_id = c.uuid
                WHERE c.name = ANY(%s)
                GROUP BY c.name, c.uuid
                """,
                (names,),
            )
            return {row[0]: {'uuid': row[1], 'lineup_count': row[2]} for row in cur.fetchall()}


def _print_status_table(names: list, already_denied: set, found: dict) -> None:
    """Print the dry-run status table to stdout."""
    print(f"\n{'Name':<45} {'Status':<15} {'Lineup Items':>12}")
    print("-" * 75)
    for name in names:
        if name in already_denied:
            status = "ALREADY DENIED"
            lineup = "-"
        elif name in found:
            status = "FOUND"
            lineup = str(found[name]['lineup_count'])
        else:
            status = "NOT IN DB"
            lineup = "-"
        print(f"{name:<45} {status:<15} {lineup:>12}")
    print()


def _confirm_delete(names: list, already_denied: set, found: dict) -> None:
    """Delete comedian + lineup_items for FOUND names; add FOUND + NOT IN DB to deny list.

    ALREADY DENIED names are skipped entirely — already handled.
    """
    names_to_process = [n for n in names if n not in already_denied]
    found_names = [n for n in names_to_process if n in found]
    not_in_db_names = [n for n in names_to_process if n not in found]

    found_uuids = [found[n]['uuid'] for n in found_names]

    with get_transaction() as conn:
        with conn.cursor() as cur:
            deleted_items = 0
            deleted_comedians = 0

            if found_uuids:
                cur.execute(
                    "DELETE FROM lineup_items WHERE comedian_id = ANY(%s)",
                    (found_uuids,),
                )
                deleted_items = cur.rowcount
                cur.execute(
                    "DELETE FROM comedians WHERE uuid = ANY(%s)",
                    (found_uuids,),
                )
                deleted_comedians = cur.rowcount

            deny_rows = [
                (name, 'manual_removal', 'remove_comedians_script')
                for name in names_to_process
            ]
            if deny_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO comedian_deny_list (name, reason, added_by)
                    VALUES %s
                    ON CONFLICT (name) DO NOTHING
                    """,
                    deny_rows,
                )

    print(
        f"Deleted {deleted_comedians} comedian record(s) and {deleted_items} lineup_item(s). "
        f"Added {len(deny_rows)} name(s) to comedian_deny_list."
    )
    if not_in_db_names:
        print(
            f"  Note: {len(not_in_db_names)} name(s) were not in the DB but added to deny list: "
            + ", ".join(f"'{n}'" for n in not_in_db_names)
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-remove comedians from the DB and add them to the deny list. "
            "Default is dry-run; pass --confirm to execute."
        )
    )
    parser.add_argument(
        '--name', metavar='NAME', dest='names', action='append', default=[],
        help='Comedian name to remove (repeatable).',
    )
    parser.add_argument(
        '--names-file', metavar='PATH',
        help='File with one comedian name per line (# comments and blank lines ignored).',
    )
    parser.add_argument(
        '--confirm', action='store_true',
        help='Execute the deletion and deny-list update (default is dry-run).',
    )
    args = parser.parse_args()

    names = list(args.names)
    if args.names_file:
        names.extend(_load_names_file(args.names_file))

    # Deduplicate while preserving order.
    seen: set = set()
    unique_names = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique_names.append(n)
    names = unique_names

    if not names:
        print("Error: provide at least one name via --name or --names-file.", file=sys.stderr)
        return 1

    # Preflight: check deny list for all names before any comedian table lookup.
    already_denied = _check_deny_list(names)
    if len(already_denied) == len(names):
        print(f"All {len(names)} name(s) are already in the deny list — nothing to do.")
        return 0

    # Look up remaining names in the comedians table.
    names_to_check = [n for n in names if n not in already_denied]
    found = _lookup_comedians(names_to_check)

    # Print status table.
    _print_status_table(names, already_denied, found)

    if not args.confirm:
        found_count = sum(1 for n in names if n in found)
        not_in_db_count = sum(1 for n in names if n not in already_denied and n not in found)
        print(
            f"Dry-run: {found_count} FOUND, {not_in_db_count} NOT IN DB, "
            f"{len(already_denied)} ALREADY DENIED. "
            "Pass --confirm to execute."
        )
        return 0

    _confirm_delete(names, already_denied, found)
    return 0


if __name__ == '__main__':
    sys.exit(main())
