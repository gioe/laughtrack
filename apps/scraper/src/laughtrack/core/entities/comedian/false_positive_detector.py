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
  8. Starts with a quote (straight or smart) — show titles like '"Big Irish" Jay ...'
  9. Starts with a digit — event titles like '5th ANNUAL ...', '90 Day Fiance: ...'
 10. Starts with '@' — social handles, not names

Note: an all-caps rule was considered but omitted. ComedianUtils.normalize_name()
already title-cases fully-upper input before insertion, so the rule is dead code
in the normal path — and historical all-caps rows in the DB include real comedians
(e.g. 'CLARE BOWEN', 'JAMES DAVIS') that must not be rejected.
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
    "private event",
    "free show",
    "talent",
    "test talent",
    "test event talent",
    "unknown artist",
    "se test",
    "fourth of july",
    "all new",
    "half",
    "couples",
    "lovers",
    "culture",
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
    " fest",
    "extravaganza",
    "theatre",
    "theater",
    "entertainment",
    "improv",
    "trivia",
    "graduation",
    "favorites",
    "comedy show",
    "comedy night",
    "comedy hour",
    "comedy jam",
    "comedy event",
    "comedy class",
    "comedy camp",
    "comedy academy",
    "comedy competition",
    "comedy allstars",
    "comedy all-stars",
    "comedy queens",
    "comedy gold",
    "comedy madness",
    "comedy invasion",
    "comedy break",
    "comedy cabaret",
    "stand up comedy",
    "stand-up comedy",
    "standup comedy",
    "fundraiser",
    "brunch",
    "happy hour",
    "night out",
    "ladies night",
    "game night",
    "date night",
    "after-party",
    "afterparty",
    "watch party",
    "ticket transfer",
    "general admission",
    "night mic",
    "night laughs",
    "night live",
    "night funnies",
    "kick off show",
    "late night show",
    "& friends",
    "one night only",
    "poetry night",
    "groove night",
    "hypnosis",
    "wrestling",
    "hosted by",
    "auditions",
    "lounge",
    # Venue type words — breweries, wineries, etc. are not comedian names
    "brewery",
    "winery",
    "vineyard",
    "distillery",
    "tavern",
    # Show format / event type keywords
    "roast battle",
    "game show",
    "gameshow",
    "drag show",
    "all stars",
    "all-stars",
    "allstars",
    "piano show",
    "magic show",
    "talent show",
    "bingo",
    "karaoke",
    "open jam",
    "day party",
    "private event",
    "closed for",
    # Promotional suffixes from venue scrapers
    "live in naples",
    "semi-finals",
    "prelim round",
    "special event",
)

_MIN_NAME_LENGTH = 4
_MAX_NAME_LENGTH = 60

# Straight and curly quotes (open/close, single/double). Real names don't start with any of these.
_LEADING_QUOTE_CHARS: tuple[str, ...] = ("\"", "'", "\u201c", "\u201d", "\u2018", "\u2019")


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

    if stripped.startswith(_LEADING_QUOTE_CHARS):
        return "starts_with_quote"

    if stripped[0].isdigit():
        return "starts_with_digit"

    if stripped.startswith("@"):
        return "starts_with_at_sign"

    return None
