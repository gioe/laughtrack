"""
Shared false-positive comedian detection logic.

Importable by:
- ComedianHandler.insert_comedians() — rejects false positives at ingestion time
- audit_false_positive_comedians.py — builds SQL query fragments from these constants

Detection criteria (any one match → false positive):
  1. Exact match against PLACEHOLDER_NAMES (case-insensitive)
  2. Substring match against PLACEHOLDER_SUBSTRINGS (open mic, open-mic)
  3. Substring match against STRUCTURAL_KEYWORDS (showcase, variety, improv, etc.)
  4. Decoration pattern: name contains '***'
  5. Pipe character in name
  6. Name length > 60
  7. Name length < 4 (short tokens almost never real comedian names)
"""

from typing import Optional

# Exact-match placeholder names (checked case-insensitively against stripped input)
PLACEHOLDER_NAMES: frozenset[str] = frozenset({
    "tba",
    "tbd",
    "to be announced",
    "to be determined",
    "special guest",
    "special guests",
    "surprise guest",
    "surprise act",
    "mystery guest",
    "comedy show",
    "various artists",
    "headliner",
    "featured comedian",
    "local comedian",
    "guest comedian",
    "guest",
    "open mic",
    "host",
    "mc",
    "emcee",
    "opener",
    "opener tbd",
    "headliner tbd",
    "lineup tba",
    "more tba",
    "plus more",
    "and more",
    "and special guests",
    "comedian tba",
    "comedian tbd",
    "comics tba",
    "comics tbd",
})

# Substring matches (case-insensitive; a name *containing* these substrings is a false positive)
PLACEHOLDER_SUBSTRINGS: tuple[str, ...] = (
    "open mic",
    "open-mic",
)

# Structural keywords (case-insensitive substring match; names containing these are not real
# comedian names — they're event descriptions, show types, or venue categories)
STRUCTURAL_KEYWORDS: tuple[str, ...] = (
    "revue",
    "burlesque",
    "variety",
    "showcase",
    "production",
    "presents",
    "festival",
    "extravaganza",
    "theatre",
    "theater",
    "entertainment",
    "improv",
    "trivia",
    "graduation",
)

_MIN_NAME_LENGTH = 4
_MAX_NAME_LENGTH = 60


def detect_false_positive(name: str) -> Optional[str]:
    """Return a detection reason string if *name* is a false positive, else None.

    Checks are applied in order; the first matching check determines the reason.
    Returns None if the name passes all checks (i.e. it looks like a real comedian name).

    Args:
        name: The comedian name to evaluate.

    Returns:
        A reason string (for logging) when the name is a false positive, or None.
    """
    stripped = name.strip()
    lower = stripped.lower()

    if lower in PLACEHOLDER_NAMES:
        return f"placeholder_name"

    for sub in PLACEHOLDER_SUBSTRINGS:
        if sub in lower:
            return f"placeholder_substring:{sub!r}"

    for kw in STRUCTURAL_KEYWORDS:
        if kw in lower:
            return f"structural_keyword:{kw!r}"

    if "***" in stripped:
        return "decoration_pattern"

    if "|" in stripped:
        return "pipe_in_name"

    if len(stripped) > _MAX_NAME_LENGTH:
        return f"length_gt_60:{len(stripped)}"

    if len(stripped) < _MIN_NAME_LENGTH:
        return f"short_name:{len(stripped)}"

    return None
