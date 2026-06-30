"""Narrow extraction of explicit headliner names from show titles."""

from __future__ import annotations

import re
from typing import Optional

from laughtrack.core.entities.comedian.false_positive_detector import detect_false_positive
from laughtrack.utilities.domain.comedian.utils import ComedianUtils

_NAME_TOKEN = r"[A-Z][A-Za-z'’.-]+"
_NAME_RE = rf"{_NAME_TOKEN}(?:\s+(?:&|and)\s+{_NAME_TOKEN}|\s+{_NAME_TOKEN}){{1,2}}"
_NAME_RE_LAZY = rf"{_NAME_TOKEN}(?:\s+(?:&|and)\s+{_NAME_TOKEN}|\s+{_NAME_TOKEN}){{1,2}}?"
_LIVE_PREFIX_RE = re.compile(
    rf"^(?:SPECIAL EVENT\s+)?(?P<name>{_NAME_RE_LAZY})\s+"
    rf"(?:LIVE\s+(?:at|in)\b|[-\u2013]\s*Appearing\b|@\s+|at\b)",
    re.IGNORECASE,
)
_COMEDY_LEGEND_RE = re.compile(
    rf"\bComedy Legend\s+(?P<name>{_NAME_RE})\s+Returns\b",
    re.IGNORECASE,
)
_NAME_COMEDY_SUFFIX_RE = re.compile(
    rf"^(?P<name>{_NAME_RE})\s+Comedy(?:\s+Special)?$",
    re.IGNORECASE,
)
_DASH_NAME_COMEDY_SPECIAL_RE = re.compile(
    rf"[-\u2013]\s*(?P<name>{_NAME_RE})\s+Comedy\s+Special\b",
    re.IGNORECASE,
)
_TITLE_WORDS = frozenset(
    {
        "comedy",
        "comedysportz",
        "show",
        "shows",
        "showcase",
        "improv",
        "stand",
        "up",
        "open",
        "mic",
        "night",
        "late",
        "early",
        "friday",
        "saturday",
        "sunday",
        "thursday",
        "live",
        "event",
        "special",
        "drunk",
        "christmas",
        "dracula",
        "romeo",
        "juliet",
        "garage",
        "sale",
        "room",
    }
)


def extract_explicit_headliner_from_title(title: Optional[str]) -> Optional[str]:
    """Return a headliner name only when a title carries an explicit name signal.

    This is intentionally stricter than comedy-title filtering. It exists for
    venue/platform feeds that expose a show title but no structured performer
    field, and only covers common headliner-title shapes such as "Jane Smith
    LIVE at Venue" or "Jane Smith Comedy Special".
    """
    cleaned = _strip_title_noise(title)
    if not cleaned:
        return None

    for pattern in (
        _COMEDY_LEGEND_RE,
        _DASH_NAME_COMEDY_SPECIAL_RE,
        _LIVE_PREFIX_RE,
        _NAME_COMEDY_SUFFIX_RE,
    ):
        match = pattern.search(cleaned)
        if not match:
            continue
        candidate = _normalize_candidate(match.group("name"))
        if candidate:
            return candidate
    return None


def _strip_title_noise(title: Optional[str]) -> str:
    cleaned = " ".join((title or "").split())
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    cleaned = re.sub(
        r"\s*\|\s*\d{1,2}/\d{1,2}/\d{2,4}\s*-\s*\d{1,2}\s*[AP]M$",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned


def _normalize_candidate(candidate: str) -> Optional[str]:
    normalized = ComedianUtils.normalize_name(candidate)
    if not normalized:
        return None

    words = [word.lower().strip(".") for word in re.findall(r"[A-Za-z][A-Za-z'’.-]*", normalized)]
    if len(words) < 2 or len(words) > 4:
        return None
    if any(word in _TITLE_WORDS for word in words):
        return None
    if detect_false_positive(normalized):
        return None
    return normalized
