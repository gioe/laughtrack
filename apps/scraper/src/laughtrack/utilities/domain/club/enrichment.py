"""Extract a club's description and opening hours from its website HTML.

The extractor is intentionally conservative — it only returns values when
they can be parsed unambiguously from a structured source.  Supported
sources, in priority order:

* ``description`` — schema.org JSON-LD ``description`` on a
  LocalBusiness-style node, then HTML ``<meta name="description">`` and
  ``<meta property="og:description">``.
* ``hours`` — schema.org JSON-LD ``openingHoursSpecification`` (structured
  objects) or ``openingHours`` (string form ``"Mo 17:00-23:00"``).

The output ``hours`` shape matches what ``apps/web/ui/pages/entity/club/
social/index.tsx`` expects: a flat ``Record<str, str>`` keyed by lowercase
day name (``monday``..``sunday``) with human-friendly 12-hour range values
(e.g. ``"5pm-11pm"``).
"""

from __future__ import annotations

import html as _html
import json
import re
from typing import Any, Dict, Iterable, List, Optional

_MAX_DESCRIPTION_LENGTH = 1000

_DAY_ORDER = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Accepts both ISO short codes (Mo, Tu, …) and the long forms returned by
# schema.org ``dayOfWeek`` URLs (http://schema.org/Monday).
_DAY_CODE_MAP: Dict[str, str] = {
    "mo": "monday", "mon": "monday", "monday": "monday",
    "tu": "tuesday", "tue": "tuesday", "tues": "tuesday", "tuesday": "tuesday",
    "we": "wednesday", "wed": "wednesday", "weds": "wednesday", "wednesday": "wednesday",
    "th": "thursday", "thu": "thursday", "thur": "thursday", "thurs": "thursday", "thursday": "thursday",
    "fr": "friday", "fri": "friday", "friday": "friday",
    "sa": "saturday", "sat": "saturday", "saturday": "saturday",
    "su": "sunday", "sun": "sunday", "sunday": "sunday",
    # PublicHoliday is listed by some venues — drop it rather than mis-mapping.
    "publicholiday": "",
}

_LDJSON_SCRIPT_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

# "Mo 09:00-17:00" / "Mo-Fr 09:00-17:00" / "Mo,We,Fr 09:00-17:00"
_OPENING_HOURS_RE = re.compile(
    r"^\s*([A-Za-z][A-Za-z,\-\s]*?)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*$"
)


def extract_description(html: Optional[str]) -> Optional[str]:
    """Return a cleaned description, or ``None`` when nothing usable is found.

    Tries JSON-LD first (a LocalBusiness node's ``description`` is more
    editorial than an SEO-tuned meta tag), then falls back to the standard
    HTML meta tags.
    """
    if not html:
        return None

    for node in _iter_ldjson_nodes(html):
        desc = node.get("description")
        if isinstance(desc, str) and desc.strip():
            return _clean_text(desc)

    meta_desc = _extract_meta_content(html, [
        ("name", "description"),
        ("property", "og:description"),
        ("name", "og:description"),
        ("name", "twitter:description"),
    ])
    if meta_desc:
        return _clean_text(meta_desc)

    return None


def extract_hours(html: Optional[str]) -> Optional[Dict[str, str]]:
    """Return hours in the ``Record<day, range>`` shape, or ``None``.

    Falls through the JSON-LD nodes searching first for a structured
    ``openingHoursSpecification``; if that yields nothing, tries the
    string-form ``openingHours`` on any node.
    """
    if not html:
        return None

    for node in _iter_ldjson_nodes(html):
        hours = _parse_opening_hours_spec(node.get("openingHoursSpecification"))
        if hours:
            return hours

    for node in _iter_ldjson_nodes(html):
        hours = _parse_opening_hours_strings(node.get("openingHours"))
        if hours:
            return hours

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_ldjson_nodes(html: str) -> Iterable[Dict[str, Any]]:
    """Yield every dict found inside any ``application/ld+json`` block.

    Walks ``@graph`` collections and nested objects so LocalBusiness nodes
    buried inside a WebPage or Organization graph are still discoverable.
    """
    for raw in _LDJSON_SCRIPT_RE.findall(html):
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        yield from _walk(data)


def _walk(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            if isinstance(value, (dict, list)):
                yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _extract_meta_content(html: str, attrs: List[tuple[str, str]]) -> Optional[str]:
    """Regex-based meta tag reader (BeautifulSoup-free to keep this module cheap).

    Tolerates attribute order and quoting variations since the tags we care
    about are standard enough to match with a loose pattern.
    """
    for attr_name, attr_value in attrs:
        pattern = re.compile(
            rf'<meta[^>]*{attr_name}\s*=\s*["\']{re.escape(attr_value)}["\'][^>]*>',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if not match:
            continue
        tag = match.group(0)
        content_match = re.search(
            r'content\s*=\s*["\']([^"\']*)["\']', tag, re.IGNORECASE
        )
        if content_match and content_match.group(1).strip():
            return content_match.group(1)
    return None


def _clean_text(text: str) -> str:
    # Decode HTML entities before collapsing whitespace so "&amp;"/"&nbsp;"
    # don't survive to the UI as literal character sequences.
    cleaned = _html.unescape(text).replace("\u00a0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > _MAX_DESCRIPTION_LENGTH:
        cleaned = cleaned[: _MAX_DESCRIPTION_LENGTH - 1].rstrip() + "\u2026"
    return cleaned


def _parse_opening_hours_spec(spec: Any) -> Optional[Dict[str, str]]:
    if spec is None:
        return None
    if isinstance(spec, dict):
        spec = [spec]
    if not isinstance(spec, list):
        return None

    out: Dict[str, str] = {}
    for entry in spec:
        if not isinstance(entry, dict):
            continue
        opens = entry.get("opens")
        closes = entry.get("closes")
        days = _normalize_days(entry.get("dayOfWeek"))
        if not (days and isinstance(opens, str) and isinstance(closes, str)):
            continue
        range_str = f"{_format_time(opens)}-{_format_time(closes)}"
        for day in days:
            # First spec for a day wins (schema.org allows multiple slots —
            # we keep the first rather than concatenating them, which is
            # good enough for the compact display).
            out.setdefault(day, range_str)
    return out or None


def _parse_opening_hours_strings(strings: Any) -> Optional[Dict[str, str]]:
    if isinstance(strings, str):
        strings = [strings]
    if not isinstance(strings, list):
        return None

    out: Dict[str, str] = {}
    for s in strings:
        if not isinstance(s, str):
            continue
        match = _OPENING_HOURS_RE.match(s)
        if not match:
            continue
        days_part, open_t, close_t = match.groups()
        days = _expand_day_part(days_part)
        if not days:
            continue
        range_str = f"{_format_time(open_t)}-{_format_time(close_t)}"
        for day in days:
            out.setdefault(day, range_str)
    return out or None


def _normalize_days(raw: Any) -> List[str]:
    """Map a schema.org ``dayOfWeek`` value to lowercase canonical day names."""
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, list):
        items = [x for x in raw if isinstance(x, str)]
    else:
        return []
    out: List[str] = []
    for item in items:
        key = item.rsplit("/", 1)[-1].strip().lower()
        mapped = _DAY_CODE_MAP.get(key)
        if mapped:
            out.append(mapped)
    return out


def _expand_day_part(part: str) -> List[str]:
    """Expand a day expression like ``Mo-Fr``/``Mo,We,Fr``/``Mo`` into day names."""
    part = part.strip()
    if not part:
        return []

    # Range form (Mo-Fr, Sa-Su, …)
    range_match = re.fullmatch(r"\s*([A-Za-z]+)\s*-\s*([A-Za-z]+)\s*", part)
    if range_match:
        head = _DAY_CODE_MAP.get(range_match.group(1).lower())
        tail = _DAY_CODE_MAP.get(range_match.group(2).lower())
        if not (head and tail):
            return []
        start = _DAY_ORDER.index(head)
        end = _DAY_ORDER.index(tail)
        if end >= start:
            return _DAY_ORDER[start : end + 1]
        # Wrap-around (e.g. "Fr-Mo") — Sunday marks the week boundary.
        return _DAY_ORDER[start:] + _DAY_ORDER[: end + 1]

    # Comma-separated list (Mo,We,Fr)
    codes = [c.strip().lower() for c in part.split(",") if c.strip()]
    expanded: List[str] = []
    for code in codes:
        mapped = _DAY_CODE_MAP.get(code)
        if mapped:
            expanded.append(mapped)
    return expanded


def _format_time(raw: str) -> str:
    """Render an ISO ``HH:MM`` time as a compact 12-hour string (``5pm``/``5:30pm``)."""
    if not isinstance(raw, str):
        return ""
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?(?::\d{2})?", raw.strip())
    if not match:
        return raw.strip()
    hour = int(match.group(1))
    minutes = int(match.group(2) or "0")
    if hour >= 24:
        hour -= 24
    suffix = "am" if hour < 12 else "pm"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    if minutes == 0:
        return f"{h12}{suffix}"
    return f"{h12}:{minutes:02d}{suffix}"
