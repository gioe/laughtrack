"""
Shared utilities for Crowdwork/Fourthwall Tickets venue scrapers.
"""

import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.philly_improv import PhillyImprovShow

# Common mapping from Rails-style timezone names to IANA equivalents.
# Venues whose Crowdwork API returns Rails names (e.g. "Central Time (US & Canada)")
# should pass this dict as ``rails_to_iana``.  Venues that already return IANA names
# (e.g. PHIT which returns "America/New_York") should pass ``rails_to_iana=None``.
RAILS_TO_IANA: Dict[str, str] = {
    "Central Time (US & Canada)": "America/Chicago",
    "Eastern Time (US & Canada)": "America/New_York",
    "Pacific Time (US & Canada)": "America/Los_Angeles",
    "Mountain Time (US & Canada)": "America/Denver",
}

_LINEUP_SECTION_RE = re.compile(
    r"\b(?:cast|line\s*up|lineup|featuring(?:\s+(?:artists|performers|comedians))?|"
    r"starring|performers|artists)\b",
    re.IGNORECASE,
)
_STOP_SECTION_RE = re.compile(
    r"\b(?:follow|instagram|facebook|tiktok|website|tickets?|duration|when|where|"
    r"about|produced by|directed by|created by|hosted by|doors?|showtime)\b",
    re.IGNORECASE,
)
_NAME_SPLIT_RE = re.compile(r"\s*(?:,|&|\band\b|\+)\s*")
_TITLE_FEATURE_RE = re.compile(r"\b(?:ft\.?|feat\.?|featuring|with)\s+(.+)$", re.IGNORECASE)
_INLINE_FEATURE_RE = re.compile(
    r"(?:\(|\b)(?:featuring|starring|hosted by|with)\s+([^).!]+)", re.IGNORECASE
)
_TRAILING_NOISE_RE = re.compile(
    r"\b(?:two|three|four|five|\d+)\s+(?:opening\s+)?(?:guest\s+)?teams?\b.*",
    re.IGNORECASE,
)
_GENERIC_TITLE_RE = re.compile(
    r"\b(?:open\s+mic|class|jam|pass(?:es)?|festival|student|grad\s+show|"
    r"workshop|audition|signup|sign\s+up)\b",
    re.IGNORECASE,
)


def extract_lineup_names(description_html: str, title: Optional[str] = None) -> List[str]:
    """Extract lineup names from Crowdwork event description HTML."""
    lines = _description_lines(description_html)
    names: List[str] = _names_from_title(title)
    in_lineup_section = False

    for line in lines:
        names.extend(_inline_feature_names(line))

    for line in lines:
        if _LINEUP_SECTION_RE.search(line) and len(line.split()) <= 8:
            in_lineup_section = True
            trailing = line.split(":", 1)[1] if ":" in line else ""
            names.extend(_candidate_names_from_line(trailing))
            continue

        if not in_lineup_section:
            continue

        if _STOP_SECTION_RE.search(line):
            break

        line_names = _candidate_names_from_line(line)
        if not line_names:
            if names:
                break
            continue
        names.extend(line_names)

    deduped = _dedupe_names(names)
    if deduped:
        return deduped
    return _names_from_title_fallback(title)


def extract_performances(
    show: dict,
    default_timezone: str = "America/Chicago",
    rails_to_iana: Optional[Dict[str, str]] = None,
) -> List[PhillyImprovShow]:
    """
    Convert one Crowdwork show dict into one PhillyImprovShow per performance date.

    A single show may have multiple performance dates in its ``dates`` array.

    Args:
        show: A single show dict from the Crowdwork API ``data`` collection.
        default_timezone: IANA timezone string used when the show's ``timezone``
            field is absent.  Defaults to ``"America/Chicago"``.
        rails_to_iana: Optional mapping from Rails-style timezone names to IANA
            equivalents.  When provided, the show's ``timezone`` value is
            normalised through this mapping before use (pass ``RAILS_TO_IANA``
            for venues that return Rails names).  When ``None``, the raw value
            is used as-is (suitable for venues that already return IANA names).

    Returns:
        A list of ``PhillyImprovShow`` instances, one per performance date.
        Returns an empty list if the show has no dates.
    """
    name = show.get("name") or "Comedy Show"
    url = show.get("url") or ""

    raw_tz = show.get("timezone") or default_timezone
    if rails_to_iana is not None:
        timezone = rails_to_iana.get(raw_tz, raw_tz)
    else:
        timezone = raw_tz

    cost_obj = show.get("cost") or {}
    cost_formatted = (cost_obj.get("formatted") or "") if isinstance(cost_obj, dict) else ""

    description = _description_body(show)

    badges_obj = show.get("badges") or {}
    spots = (badges_obj.get("spots") or "") if isinstance(badges_obj, dict) else ""
    sold_out = spots.lower().startswith("sold out") if spots else False

    dates = show.get("dates") or []
    if not dates:
        next_date = show.get("next_date")
        if next_date:
            dates = [next_date]

    performances = []
    date_overrides = show.get("date_overrides") or {}

    for date_str in dates:
        if not date_str:
            continue
        description_for_date = _description_for_date(date_str, description, date_overrides)
        performances.append(
            PhillyImprovShow(
                name=name,
                date_str=str(date_str),
                timezone=timezone,
                url=url,
                cost_formatted=cost_formatted,
                sold_out=sold_out,
                description=description_for_date,
                lineup_names=extract_lineup_names(description_for_date, title=name),
            )
        )

    return performances


def _description_lines(description_html: str) -> List[str]:
    soup = BeautifulSoup(description_html or "", "html.parser")
    text = soup.get_text("\n")
    return [_clean_line(line) for line in text.splitlines() if _clean_line(line)]


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip(" -:\t")


def _candidate_names_from_line(line: str, require_capitalized: bool = False) -> List[str]:
    line = _clean_line(line)
    if not line:
        return []

    candidates = _NAME_SPLIT_RE.split(line)
    if len(candidates) == 1:
        candidates = [line]

    cleaned_candidates = (_strip_candidate_suffixes(_clean_line(part)) for part in candidates)
    return [
        candidate
        for candidate in cleaned_candidates
        if _looks_like_name(candidate, require_capitalized=require_capitalized)
    ]


def _names_from_title(title: Optional[str]) -> List[str]:
    if not title:
        return []
    match = _TITLE_FEATURE_RE.search(title)
    if not match:
        return []
    return _candidate_names_from_line(match.group(1), require_capitalized=True)


def _names_from_title_fallback(title: Optional[str]) -> List[str]:
    if not title:
        return []
    title = _clean_line(re.sub(r"\([^)]*\)", "", title))
    if not title or _GENERIC_TITLE_RE.search(title):
        return []
    title = re.sub(r"\s+and\s+friends$", "", title, flags=re.IGNORECASE)
    return _candidate_names_from_line(title, require_capitalized=True)[:1]


def _inline_feature_names(line: str) -> List[str]:
    names: List[str] = []
    for match in _INLINE_FEATURE_RE.finditer(line):
        names.extend(_candidate_names_from_line(match.group(1), require_capitalized=True))
    return names


def _looks_like_name(value: str, require_capitalized: bool = False) -> bool:
    if not value or len(value) > 60:
        return False
    if require_capitalized and value[0].islower():
        return False
    if "@" in value or "http" in value.lower() or "$" in value:
        return False
    if any(char in value for char in "{}[]<>"):
        return False
    if len(value.split()) > 6:
        return False
    if _TRAILING_NOISE_RE.search(value):
        return False
    return bool(re.search(r"[A-Za-z]", value))


def _strip_candidate_suffixes(value: str) -> str:
    return _clean_line(re.split(r"\s+with\s+", value, maxsplit=1, flags=re.IGNORECASE)[0])


def _dedupe_names(names: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _description_body(show: dict) -> str:
    desc_obj = show.get("description") or {}
    return (desc_obj.get("body") or "") if isinstance(desc_obj, dict) else ""


def _description_for_date(date_str: object, default_description: str, date_overrides: object) -> str:
    if not isinstance(date_overrides, dict):
        return default_description
    override = date_overrides.get(str(date_str))
    if not isinstance(override, dict):
        return default_description
    description = override.get("description")
    return str(description) if description else default_description
