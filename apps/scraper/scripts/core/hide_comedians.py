"""
Batch comedian hide tool — replaces remove_comedians.py per
docs/comedian-visible-consolidation.md Decision 1.

Accepts comedian names (via --name or --names-file), classifies each name
against comedians.visible and comedian_deny_list, and on --confirm:

- Names matching a comedians row with visible=true → flip to visible=false.
  lineup_items, favorites, podcast appearances, and social handles are
  preserved.
- Names with no matching comedians row → INSERT into comedian_deny_list as
  an orphan name-only block (the residual table path).
- Names matching a comedians row that is ALREADY visible=false → no-op.
- Names already on comedian_deny_list → no-op.

Status table columns:
    VISIBLE          — comedian exists and is currently visible (will be hidden on --confirm)
    ALREADY HIDDEN   — comedian exists with visible=false (no change needed)
    NOT IN DB        — no matching comedians row (will be added to deny list on --confirm)
    ALREADY DENIED   — already in comedian_deny_list (no-op)

Usage:
    cd apps/scraper

    # Dry-run (status table only, no DB changes):
    .venv/bin/python scripts/core/hide_comedians.py --name "John Doe"
    .venv/bin/python scripts/core/hide_comedians.py --names-file names.txt

    # Execute:
    .venv/bin/python scripts/core/hide_comedians.py --name "John Doe" --confirm

For confirmed false positives where the comedian row itself is garbage
(placeholders, structural artifacts), use scripts/core/audit_false_positive_comedians.py
instead — that path hard-deletes and is the explicit override per the ADR.
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
    """Return {name: {uuid, lineup_count, visible}} for names found in comedians.

    visible is reported as the live column value so the dry-run table can
    distinguish VISIBLE candidates (will flip) from ALREADY HIDDEN (no-op).
    """
    if not names:
        return {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, c.uuid, c.visible, COUNT(li.show_id) AS lineup_count
                FROM comedians c
                LEFT JOIN lineup_items li ON li.comedian_id = c.uuid
                WHERE c.name = ANY(%s)
                GROUP BY c.name, c.uuid, c.visible
                """,
                (names,),
            )
            return {
                row[0]: {'uuid': row[1], 'visible': row[2], 'lineup_count': row[3]}
                for row in cur.fetchall()
            }


def _classify(name: str, already_denied: set, found: dict) -> str:
    """Return one of VISIBLE, ALREADY HIDDEN, NOT IN DB, ALREADY DENIED."""
    if name in already_denied:
        return "ALREADY DENIED"
    if name in found:
        return "ALREADY HIDDEN" if found[name]['visible'] is False else "VISIBLE"
    return "NOT IN DB"


def _print_status_table(names: list, already_denied: set, found: dict) -> None:
    """Print the dry-run status table to stdout."""
    print(f"\n{'Name':<45} {'Status':<18} {'Lineup Items':>12}")
    print("-" * 78)
    for name in names:
        status = _classify(name, already_denied, found)
        lineup = str(found[name]['lineup_count']) if name in found else "-"
        print(f"{name:<45} {status:<18} {lineup:>12}")
    print()


def _confirm_hide(names: list, already_denied: set, found: dict) -> None:
    """Flip visible=false for VISIBLE names; add NOT IN DB names to deny list.

    Per ADR Decision 1 the two facilities are complementary: comedians rows
    use the visible flag (preserving lineup_items, favorites, etc.); orphan
    names that never had a comedians row stay in the residual deny-list.

    ALREADY HIDDEN and ALREADY DENIED names are skipped — no second flip,
    no duplicate deny-list insert.
    """
    visible_uuids = [
        found[n]['uuid']
        for n in names
        if n in found and found[n]['visible'] is not False
    ]
    not_in_db_names = [
        n for n in names if n not in found and n not in already_denied
    ]

    hidden = 0
    denied_count = 0

    with get_transaction() as conn:
        with conn.cursor() as cur:
            if visible_uuids:
                cur.execute(
                    "UPDATE comedians SET visible = false WHERE uuid = ANY(%s)",
                    (visible_uuids,),
                )
                hidden = cur.rowcount

            if not_in_db_names:
                deny_rows = [
                    (name, 'manual_removal', 'hide_comedians_script')
                    for name in not_in_db_names
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO comedian_deny_list (name, reason, added_by)
                    VALUES %s
                    ON CONFLICT (name) DO NOTHING
                    """,
                    deny_rows,
                )
                # Report actual inserts: ON CONFLICT DO NOTHING silently
                # skips pre-existing names, so len(deny_rows) would overstate.
                denied_count = cur.rowcount

    print(
        f"Hid {hidden} comedian record(s) (lineup_items preserved). "
        f"Added {denied_count} orphan name(s) to comedian_deny_list."
    )
    if not_in_db_names:
        print(
            f"  Note: {len(not_in_db_names)} name(s) were not in the DB; "
            f"recorded as orphan deny-list entries: "
            + ", ".join(f"'{n}'" for n in not_in_db_names)
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-hide comedians by flipping comedians.visible=false. "
            "Names with no matching comedians row are added to comedian_deny_list "
            "as orphan name-only blocks. Default is dry-run; pass --confirm to execute."
        )
    )
    parser.add_argument(
        '--name', metavar='NAME', dest='names', action='append', default=[],
        help='Comedian name to hide (repeatable).',
    )
    parser.add_argument(
        '--names-file', metavar='PATH',
        help='File with one comedian name per line (# comments and blank lines ignored).',
    )
    parser.add_argument(
        '--confirm', action='store_true',
        help='Execute the hide and deny-list update (default is dry-run).',
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

    already_denied = _check_deny_list(names)
    found = _lookup_comedians(names)

    _print_status_table(names, already_denied, found)

    if not args.confirm:
        counts = {"VISIBLE": 0, "ALREADY HIDDEN": 0, "NOT IN DB": 0, "ALREADY DENIED": 0}
        for n in names:
            counts[_classify(n, already_denied, found)] += 1
        print(
            f"Dry-run: {counts['VISIBLE']} VISIBLE (will hide), "
            f"{counts['ALREADY HIDDEN']} ALREADY HIDDEN, "
            f"{counts['NOT IN DB']} NOT IN DB (will add to deny list), "
            f"{counts['ALREADY DENIED']} ALREADY DENIED. "
            "Pass --confirm to execute."
        )
        return 0

    _confirm_hide(names, already_denied, found)
    return 0


if __name__ == '__main__':
    sys.exit(main())
