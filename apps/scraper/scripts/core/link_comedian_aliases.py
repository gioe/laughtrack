"""
Link comedian alias records to their canonical parent.

For every comedian in the DB whose stored name normalizes to a *different* canonical
name, this script looks for a comedian whose name matches that canonical form and
sets parent_comedian_id on the alias record pointing to the canonical one.

The web app already filters `WHERE parent_comedian_id IS NULL` in all public queries,
so linked aliases are automatically hidden from the UI.

Usage:
    cd apps/scraper

    # Dry-run (shows proposed links, no DB changes):
    .venv/bin/python scripts/core/link_comedian_aliases.py

    # Execute:
    .venv/bin/python scripts/core/link_comedian_aliases.py --confirm
"""

import argparse
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from laughtrack.infrastructure.database.connection import get_connection, get_transaction  # noqa: E402

# ---------------------------------------------------------------------------
# Inline normalize_name — mirrors ComedianUtils.normalize_name exactly so we
# can run this script without pulling in the full package import chain.
# Keep in sync with src/laughtrack/utilities/domain/comedian/utils.py.
# ---------------------------------------------------------------------------

_PREFIX_NOISE_RE = re.compile(r'^(?:Comedian|Comedy\s+Magician)\s+', re.IGNORECASE)
_SUFFIX_NOISE_RE = re.compile(
    r'(?:'
    r'\s+[-–]\s+special[\s_]event|'
    r'\s+[-–]\s+special\s+show|'
    r'\s+[-–]\s+live\b|'
    r'\s+live\s+in\s+\w|'
    r'\s+from\s+[\"\'\u201c\u2018]|'
    r'\s+from\s+[A-Z]{2,}'
    r')',
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    """Canonical-name normalization (mirrors ComedianUtils.normalize_name)."""
    try:
        canonical = name.strip()
        canonical = _PREFIX_NOISE_RE.sub("", canonical).strip()
        canonical = canonical.split(":")[0].strip()
        m = _SUFFIX_NOISE_RE.search(canonical)
        if m:
            canonical = canonical[: m.start()].strip()
        # Remove parenthetical content
        canonical = re.sub(r'\([^)]*\)', '', canonical).strip()
        # Title-case only if entirely upper or lower
        if canonical.isupper() or canonical.islower():
            canonical = canonical.title()
        return canonical
    except Exception:
        return ""


def _fetch_all_comedians(cur) -> list[dict]:
    cur.execute(
        "SELECT id, name FROM comedians WHERE parent_comedian_id IS NULL ORDER BY name"
    )
    return [{"id": row[0], "name": row[1]} for row in cur.fetchall()]


def _build_name_index(comedians: list[dict]) -> dict[str, int]:
    """Map lowercase-stripped name → id for fast lookup."""
    return {c["name"].strip().lower(): c["id"] for c in comedians}


def _find_links(comedians: list[dict], index: dict[str, int]) -> list[dict]:
    """
    For each comedian, normalise its name. If the result differs from the stored
    name and matches another comedian in the index, record a parent→child link.
    """
    links = []
    for c in comedians:
        canonical = _normalize_name(c["name"])
        if not canonical or canonical.strip() == c["name"].strip():
            continue  # already canonical (exact match — case differences are intentional to catch)

        parent_id = index.get(canonical.strip().lower())
        if parent_id is None or parent_id == c["id"]:
            continue  # no canonical parent found in DB

        links.append({
            "child_id": c["id"],
            "child_name": c["name"],
            "parent_id": parent_id,
            "canonical_name": canonical,
        })

    return links


def _print_table(links: list[dict]) -> None:
    if not links:
        print("No alias relationships found.")
        return

    col_child = max(len(k["child_name"]) for k in links)
    col_child = max(col_child, len("Alias (child)"))
    col_canon = max(len(k["canonical_name"]) for k in links)
    col_canon = max(col_canon, len("Canonical (parent)"))

    header = f"{'Alias (child)':<{col_child}}  →  {'Canonical (parent)':<{col_canon}}"
    print(header)
    print("-" * len(header))
    for link in links:
        print(f"{link['child_name']:<{col_child}}  →  {link['canonical_name']}")

    print()
    print(f"Found {len(links)} alias relationship(s).")


def _apply_links(cur, links: list[dict]) -> int:
    """Set parent_comedian_id on each child. Returns number of rows updated."""
    if not links:
        return 0

    updated = 0
    for link in links:
        cur.execute(
            "UPDATE comedians SET parent_comedian_id = %s WHERE id = %s",
            (link["parent_id"], link["child_id"]),
        )
        updated += cur.rowcount

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Apply parent_comedian_id updates to the DB (default: dry-run only).",
    )
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            comedians = _fetch_all_comedians(cur)

    print(f"Loaded {len(comedians)} unlinked comedians.\n")

    index = _build_name_index(comedians)
    links = _find_links(comedians, index)

    _print_table(links)

    if not links:
        return

    if not args.confirm:
        print("\nDry-run: pass --confirm to apply.")
        return

    with get_transaction() as conn:
        with conn.cursor() as cur:
            updated = _apply_links(cur, links)

    print(f"\nLinked {updated} alias record(s) to their canonical parent.")


if __name__ == "__main__":
    main()
