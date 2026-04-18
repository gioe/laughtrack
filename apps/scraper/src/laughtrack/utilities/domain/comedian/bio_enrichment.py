"""Extract a short About-section bio for a comedian from Wikipedia's REST summary.

The Wikipedia REST API (``/api/rest_v1/page/summary/{title}``) returns a
JSON payload with a curated plain-text ``extract`` field and a ``description``
line. This module validates the response to ensure the page is actually about
a comedian (not a disambiguation page or an unrelated person who happens to
share the name) and trims the extract to an About-section-sized bio.

The extractor is intentionally conservative: we only accept a page when its
short description or opening prose mentions comedy-adjacent language. A
plain ``"standard"`` Wikipedia page for someone named "Mike Birbiglia" still
gets rejected if neither the description nor the extract mentions anything
comedy-related — better to leave the bio NULL than to publish the wrong
person's biography.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_MAX_BIO_LENGTH = 600

# Keywords that signal the subject works in comedy. Matched case-insensitively
# as whole words so we don't accidentally match "comedic relief" in an article
# about a dramatic actor. Includes ``actor`` because many stand-ups are
# primarily described by Wikipedia as "actor and comedian" with ``actor``
# appearing first — dropping ``actor`` would reject too many real matches.
_COMEDY_KEYWORDS = [
    "comedian",
    "comedienne",
    "comic",
    "comedy",
    "stand-up",
    "standup",
    "stand up",
    "sketch",
    "improv",
    "humorist",
    "satirist",
    "funnyman",
    "funnywoman",
]

_COMEDY_KEYWORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _COMEDY_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Sentence-boundary split: period/question/exclamation followed by whitespace
# and a capital letter or digit. Good enough for Wikipedia prose — we don't
# need full NLP here, just a preference for clean truncation.
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def extract_bio(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return a cleaned bio string, or ``None`` if the payload is not usable.

    Rejects disambiguation pages, pages with no prose, and pages whose
    description + extract never mention comedy-related keywords.
    """
    if not isinstance(payload, dict):
        return None

    page_type = payload.get("type")
    if page_type == "disambiguation":
        return None

    extract = payload.get("extract")
    if not isinstance(extract, str) or not extract.strip():
        return None

    description = payload.get("description")
    description_str = description if isinstance(description, str) else ""

    if not _mentions_comedy(f"{description_str}\n{extract}"):
        return None

    return _truncate_to_bio(extract)


def _mentions_comedy(text: str) -> bool:
    return bool(_COMEDY_KEYWORD_RE.search(text))


def _truncate_to_bio(extract: str, max_length: int = _MAX_BIO_LENGTH) -> str:
    """Collapse internal whitespace and trim to the last full sentence under ``max_length``.

    Wikipedia extracts can run long (3+ paragraphs for famous subjects). The
    About section is a compact widget, so we prefer 1–3 sentences. Falls back
    to a hard character cap with an ellipsis when no sentence boundary fits.
    """
    cleaned = re.sub(r"\s+", " ", extract).strip()
    if len(cleaned) <= max_length:
        return cleaned

    # Walk sentence boundaries and keep the last cut that fits.
    sentences = _SENTENCE_END_RE.split(cleaned)
    accumulated = ""
    for sentence in sentences:
        candidate = f"{accumulated} {sentence}".strip() if accumulated else sentence
        if len(candidate) > max_length:
            break
        accumulated = candidate

    if accumulated:
        return accumulated

    # No sentence fits — hard truncate with ellipsis.
    return cleaned[: max_length - 1].rstrip() + "\u2026"
