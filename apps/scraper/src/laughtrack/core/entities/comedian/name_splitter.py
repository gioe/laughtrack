"""
Split multi-comedian name strings into individual comedian names.

Detects patterns where two or more comedian names are combined into a single
lineup entry (e.g. "Kiki Yeung & Esther Ku") and splits them into separate
names so each comedian gets their own lineup item.

Patterns handled:
  - "X & Y" or "X and Y"
  - "X with Y", "X w/ Y", "X With Special Guest Y", "X Featuring Y", "X ft Y"
  - "X / Y" (slash-separated)

Reuses the same regex patterns proven by reconcile_deny_list.py.
"""

import re
from typing import List

# "X & Y" or "X and Y"
_AND_SPLIT_RE = re.compile(r'\s+(?:&|and)\s+', re.IGNORECASE)

# "X with Y", "X w/ Y", "X With Special Guest Y", "X Featuring Y", "X ft Y"
_WITH_RE = re.compile(
    r'^(.+?)\s+(?:with(?:\s+Special\s+Guest)?|w/|[Ff]eaturing|ft\.?)\s+(.+)',
    re.IGNORECASE,
)

# "X / Y" (slash-separated)
_SLASH_SPLIT_RE = re.compile(r'\s*/\s*')

# Noise words that indicate the string is an event title, not combined comedian names
_EVENT_NOISE = frozenset({
    'comedy', 'show', 'night', 'live', 'tour', 'special', 'event',
    'party', 'battle', 'club', 'hour', 'open mic', 'bingo', 'karaoke',
    'drag', 'magic', 'class', 'camp', 'fundraiser', 'brunch',
    'brewery', 'winery', 'tavern', 'bar', 'lounge', 'pub',
    'trivia', 'improv', 'sketch', 'variety', 'burlesque', 'podcast',
    'music', 'band', 'sing', 'dance', 'paint', 'sip', 'workshop',
    'celebration', 'tribute', 'karaoke',
})


def _looks_like_name(text: str) -> bool:
    """Heuristic: does this look like a person's name (2-6 words, no event noise)."""
    text = text.strip()
    if not text or len(text) < 4:
        return False
    words = text.split()
    if len(words) < 2 or len(words) > 6:
        return False
    if not words[0][0].isupper():
        return False
    lower = text.lower()
    for noise in _EVENT_NOISE:
        if noise in lower:
            return False
    return True


def _clean_part(name: str) -> str:
    """Clean up a split name part: strip punctuation, trailing '!'."""
    name = name.strip().rstrip('!')
    name = re.sub(r'\([^)]*\)', '', name).strip()
    name = name.strip('"\'').strip()
    return name


def split_combined_name(name: str) -> List[str]:
    """Split a multi-comedian name string into individual names.

    Returns:
        A list of individual comedian names. If the name does not match any
        multi-comedian pattern, returns a single-element list with the
        original name unchanged.
    """
    stripped = name.strip()

    # Try "X & Y" or "X and Y"
    if _AND_SPLIT_RE.search(stripped):
        parts = _AND_SPLIT_RE.split(stripped)
        # Further split comma-separated parts (e.g. "A, B & C" → [A, B, C])
        expanded = []
        for p in parts:
            if ',' in p:
                expanded.extend(sub.strip() for sub in p.split(',') if sub.strip())
            else:
                expanded.append(p)
        cleaned = [_clean_part(p) for p in expanded]
        name_parts = [p for p in cleaned if _looks_like_name(p)]
        if len(name_parts) >= 2:
            return name_parts

    # Try "X with Y", "X Featuring Y", etc.
    m = _WITH_RE.match(stripped)
    if m:
        left = _clean_part(m.group(1))
        right = _clean_part(m.group(2))
        if _looks_like_name(left) and _looks_like_name(right):
            return [left, right]

    # Try "X / Y"
    if '/' in stripped and not stripped.startswith('http'):
        parts = _SLASH_SPLIT_RE.split(stripped)
        if len(parts) == 2:
            cleaned = [_clean_part(p) for p in parts]
            name_parts = [p for p in cleaned if _looks_like_name(p)]
            if len(name_parts) == 2:
                return name_parts

    return [stripped]
