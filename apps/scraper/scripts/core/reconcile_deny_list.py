"""
Reconcile deleted false-positive comedian entries against legitimate records.

For each deny list entry, extracts embedded real comedian names using multiple
pattern-matching strategies and cross-references them against existing legitimate
comedian records in the database.

Pattern categories handled:
  1. PREFIX:        "Comedian X ..." / "Comedy Magician X ..." → X
  2. LIVE_SUFFIX:   "X Live!" / "X Live in <city>" → X
  3. COMEDY_SUFFIX: "X Comedy" → X
  4. MULTI_AND:     "X & Y" / "X and Y" → [X, Y]
  5. MULTI_WITH:    "X with Y" / "X w/ Y" / "X Featuring Y" → [X, Y]
  6. MULTI_SLASH:   "X / Y" → [X, Y]
  7. AKA:           "X AKA Y" / "X aka Y" → [X, Y]
  8. POSSESSIVE:    "X's <Show Name>" → X
  9. PROMO:         "X Returns to ..." / "X Makes His ... Debut!" → X
 10. NORMALIZE:     Fallback via ComedianUtils.normalize_name

Usage:
    cd apps/scraper

    # Dry-run — prints matches, no DB changes:
    .venv/bin/python scripts/core/reconcile_deny_list.py

    # Execute — re-inserts as aliases, removes from deny list:
    .venv/bin/python scripts/core/reconcile_deny_list.py --confirm
"""

import argparse
import os
import re
import sys
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from laughtrack.infrastructure.database.connection import get_connection  # noqa: E402

# ---------------------------------------------------------------------------
# Name extraction patterns
# ---------------------------------------------------------------------------

# Prefix: "Comedian X ..." or "Comedy Magician X ..."
_PREFIX_RE = re.compile(r'^(?:Comedian|Comedy\s+Magician)\s+(.+)', re.IGNORECASE)

# "X Live in <City>, <State>!" or "X Live in <City>!"
_LIVE_IN_RE = re.compile(r'^(.+?)\s+Live\s+in\s+.+', re.IGNORECASE)

# "X Live!" (trailing)
_LIVE_BANG_RE = re.compile(r'^(.+?)\s+Live!$', re.IGNORECASE)

# "X Comedy" (but not "X Comedy <other words>" to avoid show titles)
_COMEDY_SUFFIX_RE = re.compile(r'^(.+?)\s+Comedy$', re.IGNORECASE)

# Multi-comedian: "X & Y", "X and Y" (not preceded by letters forming a word)
_AND_SPLIT_RE = re.compile(r'\s+(?:&|and)\s+', re.IGNORECASE)

# "X with Y", "X w/ Y", "X With Special Guest Y", "X Featuring Y", "X ft Y"
_WITH_RE = re.compile(
    r'^(.+?)\s+(?:with(?:\s+Special\s+Guest)?|w/|[Ff]eaturing|ft\.?)\s+(.+)',
    re.IGNORECASE,
)

# "X / Y" (slash-separated)
_SLASH_SPLIT_RE = re.compile(r'\s*/\s*')

# "X AKA Y" or "X aka @handle"
_AKA_RE = re.compile(r'^(.+?)\s+(?:AKA|aka|a\.k\.a\.?)\s+(.+)', re.IGNORECASE)

# Possessive: "X's <Show Title>" — only if Show Title is 2+ words
_POSSESSIVE_RE = re.compile(r"^(.+?)'s\s+\w+\s+\w+")

# Promo: "X Returns to ...", "X Makes His ... Debut!", "X Is Back ..."
_PROMO_RE = re.compile(
    r'^(.+?)\s+(?:Returns?\s+to|Makes?\s+(?:His|Her|Their)|Is\s+Back|'
    r'Triumphant\s+Return|From\s+(?:SNL|"[^"]+"|\'[^\']+\'))',
    re.IGNORECASE,
)

# "X MSSP" — podcast reference suffix
_MSSP_RE = re.compile(r'^(.+?)\s+MSSP$')

# "Sun May 24 X" — date prefix
_DATE_PREFIX_RE = re.compile(
    r'^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+'
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+\s+(.+)',
    re.IGNORECASE,
)

# "SNL's X" — show possessive prefix
_SHOW_POSSESSIVE_PREFIX_RE = re.compile(
    r"^(?:SNL|Chappelle\s+Show|Kill\s+Tony)'s\s+(.+)", re.IGNORECASE
)

# "X From 'Show'" or 'X From "Show"' — strip From-suffix
_FROM_SHOW_RE = re.compile(
    r'^(.+?)\s+From\s+(?:"[^"]+"|\'[^\']+\'|[A-Z][\w\s]*(?:\'s)?).*$',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Inline normalize_name — mirrors ComedianUtils.normalize_name
# ---------------------------------------------------------------------------

_NORM_PREFIX_RE = re.compile(r'^(?:Comedian|Comedy\s+Magician)\s+', re.IGNORECASE)
_NORM_SUFFIX_RE = re.compile(
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
    canonical = name.strip()
    canonical = _NORM_PREFIX_RE.sub("", canonical).strip()
    canonical = canonical.split(":")[0].strip()
    m = _NORM_SUFFIX_RE.search(canonical)
    if m:
        canonical = canonical[: m.start()].strip()
    canonical = re.sub(r'\([^)]*\)', '', canonical).strip()
    if canonical.isupper() or canonical.islower():
        canonical = canonical.title()
    return canonical


def _clean_extracted(name: str) -> str:
    """Clean up an extracted name: strip punctuation, whitespace, trailing '!'."""
    name = name.strip().rstrip('!')
    name = re.sub(r'\([^)]*\)', '', name).strip()
    # Remove trailing quotes/punctuation
    name = name.strip('"\'').strip()
    # Remove leading "Comedian " if still present
    name = _NORM_PREFIX_RE.sub("", name).strip()
    return name


# ---------------------------------------------------------------------------
# Extraction engine
# ---------------------------------------------------------------------------


def extract_candidate_names(deny_entry: str) -> list[tuple[str, str]]:
    """Extract candidate comedian names from a deny list entry.

    Returns a list of (candidate_name, pattern_category) tuples.
    A single entry can produce multiple candidates (e.g. multi-comedian splits).
    """
    candidates: list[tuple[str, str]] = []
    entry = deny_entry.strip()

    # 1. Multi-comedian splits (do these first — they produce multiple names)
    # "X & Y" or "X and Y"
    if _AND_SPLIT_RE.search(entry):
        parts = _AND_SPLIT_RE.split(entry)
        # Filter: only if each part looks like a name (2-4 words, no structural keywords)
        name_parts = [_clean_extracted(p) for p in parts if _looks_like_name(p.strip())]
        if len(name_parts) >= 2:
            for p in name_parts:
                candidates.append((p, "MULTI_AND"))

    # "X with Y" / "X Featuring Y"
    m = _WITH_RE.match(entry)
    if m:
        left = _clean_extracted(m.group(1))
        right = _clean_extracted(m.group(2))
        if _looks_like_name(left):
            candidates.append((left, "MULTI_WITH"))
        if _looks_like_name(right):
            candidates.append((right, "MULTI_WITH"))

    # "X / Y"
    if '/' in entry and not entry.startswith('http'):
        parts = _SLASH_SPLIT_RE.split(entry)
        if len(parts) == 2:
            name_parts = [_clean_extracted(p) for p in parts if _looks_like_name(p.strip())]
            if len(name_parts) == 2:
                for p in name_parts:
                    candidates.append((p, "MULTI_SLASH"))

    # "X AKA Y"
    m = _AKA_RE.match(entry)
    if m:
        left = _clean_extracted(m.group(1))
        right = _clean_extracted(m.group(2))
        if _looks_like_name(left):
            candidates.append((left, "AKA"))
        if _looks_like_name(right) and not right.startswith('@'):
            candidates.append((right, "AKA"))

    # Skip remaining single-name patterns if we already found multi-comedian matches
    if candidates:
        return candidates

    # 2. "Comedian X Live in ..." — apply prefix first, then live-in
    m = _PREFIX_RE.match(entry)
    if m:
        inner = m.group(1).strip()
        # Check for "Live in" within the inner part
        m2 = _LIVE_IN_RE.match(inner)
        if m2:
            name = _clean_extracted(m2.group(1))
            if _looks_like_name(name):
                candidates.append((name, "PREFIX_LIVE_IN"))
        else:
            name = _clean_extracted(inner)
            if _looks_like_name(name):
                candidates.append((name, "PREFIX"))

    # 3. "X Live!" or "X Live in ..."
    if not candidates:
        m = _LIVE_BANG_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "LIVE_SUFFIX"))

        m = _LIVE_IN_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "LIVE_IN"))

    # 4. "X Comedy"
    if not candidates:
        m = _COMEDY_SUFFIX_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "COMEDY_SUFFIX"))

    # 5. Show possessive prefix: "SNL's X", "Kill Tony's X"
    if not candidates:
        m = _SHOW_POSSESSIVE_PREFIX_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "SHOW_PREFIX"))

    # 6. "X From 'Show'" / 'X From "Show"'
    if not candidates:
        m = _FROM_SHOW_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "FROM_SHOW"))

    # 7. Promo: "X Returns to ...", "X Is Back ..."
    if not candidates:
        m = _PROMO_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "PROMO"))

    # 8. "X MSSP" — podcast suffix
    if not candidates:
        m = _MSSP_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "MSSP_SUFFIX"))

    # 9. Date prefix: "Sun May 24 X"
    if not candidates:
        m = _DATE_PREFIX_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "DATE_PREFIX"))

    # 10. Possessive: "X's Show Title"
    if not candidates:
        m = _POSSESSIVE_RE.match(entry)
        if m:
            name = _clean_extracted(m.group(1))
            if _looks_like_name(name):
                candidates.append((name, "POSSESSIVE"))

    # 11. Fallback: normalize_name
    if not candidates:
        normalized = _normalize_name(entry)
        if normalized and normalized != entry.strip() and _looks_like_name(normalized):
            candidates.append((normalized, "NORMALIZE"))

    return candidates


def _looks_like_name(text: str) -> bool:
    """Heuristic: does this look like a person's name?

    A name is 2-5 words, each starting with a capital letter (or a known
    lowercase particle like "de", "von", etc.), and at least 4 characters total.
    """
    text = text.strip()
    if not text or len(text) < 4:
        return False

    words = text.split()
    if len(words) < 2 or len(words) > 6:
        return False

    # At least the first word should be capitalized
    if not words[0][0].isupper():
        return False

    # Reject if it contains common non-name indicators
    lower = text.lower()
    noise = [
        'comedy', 'show', 'night', 'live', 'tour', 'special', 'event',
        'party', 'battle', 'club', 'hour', 'open mic', 'bingo', 'karaoke',
        'drag', 'magic', 'class', 'camp', 'fundraiser', 'brunch',
        'brewery', 'winery', 'tavern', 'bar', 'lounge', 'pub',
    ]
    for n in noise:
        if n in lower:
            return False

    return True


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _fetch_deny_list(cur) -> list[str]:
    """Fetch all names from the comedian deny list."""
    cur.execute("SELECT name FROM comedian_deny_list ORDER BY name")
    return [row[0] for row in cur.fetchall()]


def _fetch_legitimate_comedians(cur) -> list[dict]:
    """Fetch comedians that are NOT aliases (canonical records)."""
    cur.execute(
        "SELECT id, uuid, name FROM comedians "
        "WHERE parent_comedian_id IS NULL "
        "ORDER BY name"
    )
    return [{"id": row[0], "uuid": row[1], "name": row[2]} for row in cur.fetchall()]


def _build_name_index(comedians: list[dict]) -> dict[str, dict]:
    """Map lowercase name → comedian dict for fast lookup."""
    index: dict[str, dict] = {}
    for c in comedians:
        key = c["name"].strip().lower()
        index[key] = c
    return index


def _match_candidate(
    candidate: str,
    index: dict[str, dict],
) -> dict | None:
    """Try to match a candidate name against the comedian index."""
    key = candidate.strip().lower()
    if key in index:
        return index[key]

    # Also try normalize_name on the candidate
    normalized = _normalize_name(candidate)
    norm_key = normalized.strip().lower()
    if norm_key in index:
        return index[norm_key]

    return None


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


_MULTI_PATTERNS = frozenset({"MULTI_AND", "MULTI_WITH", "MULTI_SLASH"})


def _classify_matches(matches: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split matches into aliasable (single comedian) and multi-comedian (document only).

    A deny entry that maps to multiple distinct comedians can't become a single alias.
    Those are reported separately as candidates for lineup-splitting enhancement.
    """
    # Group matches by deny entry
    by_entry: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_entry[m["deny_entry"]].append(m)

    aliasable = []
    multi_only = []

    for entry, group in by_entry.items():
        unique_parents = {m["parent_id"] for m in group}
        is_multi_pattern = any(m["pattern"] in _MULTI_PATTERNS for m in group)

        if len(unique_parents) == 1 and not is_multi_pattern:
            # Single comedian match — can create alias
            aliasable.append(group[0])  # take first (all point to same parent)
        elif len(unique_parents) == 1 and is_multi_pattern:
            # Multi pattern but only one comedian found — can create alias
            # (e.g., "Adam Cayton-Holland & Ben Roy" where only Adam is in DB)
            aliasable.append(group[0])
        else:
            # Multiple distinct comedians — document only
            multi_only.extend(group)

    return aliasable, multi_only


def _print_section(title: str, matches: list[dict]) -> None:
    """Print a formatted section of matches grouped by pattern."""
    by_pattern: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_pattern[m["pattern"]].append(m)

    for pattern, group in sorted(by_pattern.items()):
        print(f"\n--- {pattern} ({len(group)} match{'es' if len(group) != 1 else ''}) ---\n")

        col_deny = max(len(m["deny_entry"]) for m in group)
        col_deny = max(col_deny, 20)
        col_deny = min(col_deny, 55)
        col_match = max(len(m["matched_name"]) for m in group)
        col_match = max(col_match, 20)

        header = f"  {'Deny List Entry':<{col_deny}}  →  {'Matched Comedian':<{col_match}}"
        print(header)
        print(f"  {'-' * len(header.strip())}")

        for m in sorted(group, key=lambda x: x["deny_entry"]):
            deny_display = m["deny_entry"]
            if len(deny_display) > col_deny:
                deny_display = deny_display[: col_deny - 3] + "..."
            print(f"  {deny_display:<{col_deny}}  →  {m['matched_name']}")


def _print_report(
    aliasable: list[dict], multi_only: list[dict],
) -> None:
    """Print a formatted report of deny list → comedian matches."""
    total = len(aliasable) + len(multi_only)
    if total == 0:
        print("\nNo matches found between deny list entries and legitimate comedians.")
        return

    print(f"\n{'=' * 80}")
    print(f"RECONCILIATION REPORT")
    print(f"{'=' * 80}")

    if aliasable:
        print(f"\n## ALIASABLE — {len(aliasable)} entries → single comedian alias records")
        print("   (will be re-inserted as alias records with parent_comedian_id)")
        _print_section("Aliasable", aliasable)

    if multi_only:
        print(f"\n\n## MULTI-COMEDIAN — {len(multi_only)} matches (document only)")
        print("   (deny entry maps to 2+ comedians — needs lineup splitting, not aliasing)")
        _print_section("Multi-comedian", multi_only)

    print(f"\n{'=' * 80}")
    print(f"Aliasable: {len(aliasable)} | Multi-comedian (doc only): {len(multi_only)}")
    print(f"{'=' * 80}")


# ---------------------------------------------------------------------------
# Apply changes
# ---------------------------------------------------------------------------


def _apply_aliases(cur, aliasable: list[dict]) -> tuple[int, int]:
    """Re-insert aliasable deny list entries as alias comedian records.

    Only processes single-comedian matches (one deny entry → one parent).
    Multi-comedian entries are skipped (they need lineup splitting, not aliasing).

    Returns (aliases_created, deny_entries_removed).
    """
    aliases_created = 0
    deny_removed = 0

    for m in aliasable:
        deny_name = m["deny_entry"]
        parent_id = m["parent_id"]

        # Check if the name already exists in comedians (shouldn't, but guard)
        cur.execute("SELECT id FROM comedians WHERE name = %s", (deny_name,))
        if cur.fetchone():
            continue

        # Insert as alias comedian record with parent_comedian_id set.
        # UUID is derived from the deny-list name (not the parent's UUID) so
        # future scrapes that encounter this exact string find the alias record
        # and the ON CONFLICT path sets parent_comedian_id.
        # The web app filters WHERE parent_comedian_id IS NULL, hiding aliases.
        cur.execute(
            """
            INSERT INTO comedians (uuid, name, parent_comedian_id, sold_out_shows, total_shows)
            VALUES (
                md5(lower(regexp_replace(%s, '[^a-zA-Z0-9]', '', 'g'))),
                %s,
                %s,
                0, 0
            )
            ON CONFLICT (uuid) DO UPDATE SET parent_comedian_id = %s
            RETURNING id
            """,
            (deny_name, deny_name, parent_id, parent_id),
        )
        result = cur.fetchone()
        if result:
            aliases_created += 1

        # Remove from deny list so future scrapes aren't blocked
        cur.execute(
            "DELETE FROM comedian_deny_list WHERE name = %s",
            (deny_name,),
        )
        deny_removed += cur.rowcount

    return aliases_created, deny_removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Apply changes: re-insert aliases and remove from deny list (default: dry-run).",
    )
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            deny_entries = _fetch_deny_list(cur)
            comedians = _fetch_legitimate_comedians(cur)

    print(f"Loaded {len(deny_entries)} deny list entries.")
    print(f"Loaded {len(comedians)} legitimate comedians.")

    index = _build_name_index(comedians)

    matches = []
    for entry in deny_entries:
        candidates = extract_candidate_names(entry)
        for candidate_name, pattern in candidates:
            matched = _match_candidate(candidate_name, index)
            if matched:
                matches.append({
                    "deny_entry": entry,
                    "candidate": candidate_name,
                    "matched_name": matched["name"],
                    "parent_id": matched["id"],
                    "parent_uuid": matched["uuid"],
                    "pattern": pattern,
                })

    aliasable, multi_only = _classify_matches(matches)
    _print_report(aliasable, multi_only)

    if not aliasable:
        print("\nNo aliasable matches to apply.")
        return

    if not args.confirm:
        print(f"\nDry-run: pass --confirm to apply {len(aliasable)} alias(es).")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            aliases_created, deny_removed = _apply_aliases(cur, aliasable)
        conn.commit()

    print(f"\nCreated {aliases_created} alias comedian record(s).")
    print(f"Removed {deny_removed} entries from deny list.")
    if multi_only:
        entries = {m["deny_entry"] for m in multi_only}
        print(f"\n{len(entries)} multi-comedian entries were NOT aliased (need lineup splitting).")


if __name__ == "__main__":
    main()
