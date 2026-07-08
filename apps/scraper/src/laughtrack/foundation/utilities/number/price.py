"""
Shared price-text parsing.

Fifteen scrapers hand-rolled slightly different variants of "pull a dollar
amount out of a human-facing price string". They drifted per copy (some handled
"Free", some handled ranges, some stripped thousands separators, some did not).
This is the single canonical parser they all route through.

Pure utility with no domain dependencies so it can be imported anywhere without
risking circular imports.

IMPORTANT: this parser is for *text* prices only. Platforms that expose an
integer cents amount (e.g. dojour, 1234ticket) must NOT route through here —
convert their cents ints directly. See ``scrapers/utils/ticket_enrichment.py``
for the None (unknown) vs 0.0 (free) convention every caller preserves.
"""

import re
from typing import Optional

# A dollar-anchored amount, e.g. "$25", "$ 25", "$1234.50". The ``$`` anchor lets
# us pick real prices out of noisier strings and take the minimum across a range.
_DOLLAR_AMOUNT_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")

# A bare numeric amount, used only as a fallback when the text carries no ``$``.
_BARE_AMOUNT_RE = re.compile(r"(\d+(?:\.\d{1,2})?)")

# "free" as a whole word — a word boundary avoids false-positives on price
# strings that merely contain the letters (e.g. "freezing", "freestyle night").
_FREE_RE = re.compile(r"\bfree\b", re.IGNORECASE)


def parse_price_text(text: str) -> Optional[float]:
    """Parse a human-facing price string into a float dollar amount.

    Behaviour (the union the 15 hand-rolled copies collectively implemented):

    - Explicit "free" text returns ``0.0``.
    - Ranges ("$20-$30", "$20 to $30") return the **minimum** advertised price.
    - Thousands separators are stripped ("$1,234.50" -> ``1234.5``).
    - When several ``$`` amounts appear, the lowest is returned; otherwise the
      first bare number is used.
    - Returns ``None`` when there is no numeric price signal (unknown), which
      callers keep distinct from ``0.0`` (explicitly free).

    Args:
        text: Raw price string from a listing (may be ``None``/empty).

    Returns:
        The parsed dollar amount, ``0.0`` for free, or ``None`` when unknown.
    """
    if not text:
        return None

    if _FREE_RE.search(text):
        return 0.0

    # Strip thousands separators so "1,234.50" parses as one number.
    cleaned = text.replace(",", "")

    dollar_amounts = _DOLLAR_AMOUNT_RE.findall(cleaned)
    if dollar_amounts:
        return min(float(amount) for amount in dollar_amounts)

    match = _BARE_AMOUNT_RE.search(cleaned)
    if not match:
        return None
    return float(match.group(1))
