"""Conservative show type classification for discovery filters."""

import re
from typing import Any, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show

SHOW_TYPE_UNKNOWN = "unknown"

_OPEN_MIC_RE = re.compile(r"\bopen[\s-]?mic\b", re.IGNORECASE)
_IMPROV_RE = re.compile(r"\bimprov(?:isation|isational|isational)?\b|\bimprovised\b", re.IGNORECASE)
_SKETCH_RE = re.compile(r"\bsketch(?:es)?\b", re.IGNORECASE)
_STANDUP_RE = re.compile(
    r"\bstand[\s-]?up\b|\bcomedy\b|\bcomed(?:ian|ians|y)\b|\bcomic(?:s)?\b|\blaughs?\b",
    re.IGNORECASE,
)
_THEATER_RE = re.compile(
    r"\b(?:play|plays|theatre|theater|shakespeare|hamlet|musical|broadway|drama)\b",
    re.IGNORECASE,
)
_MUSIC_RE = re.compile(
    r"\b(?:concert|concerts|music|live music|band|orchestra|symphony|jazz|rock|folk|brass band)\b",
    re.IGNORECASE,
)
_PODCAST_RE = re.compile(r"\b(?:podcast|live taping|taping)\b", re.IGNORECASE)
_CLASS_WORKSHOP_RE = re.compile(r"\b(?:class|workshop|clinic|course|intensive)\b", re.IGNORECASE)
_VARIETY_RE = re.compile(r"\b(?:variety|cabaret|burlesque|revue)\b", re.IGNORECASE)

_STANDUP_DEFAULT_DOMAINS = frozenset(
    {
        "standupny.com",
        "standuplive.com",
        "grislypearstandup.com",
        "newyorkcomedyclub.com",
        "comedycellar.com",
    }
)
_IMPROV_DEFAULT_DOMAINS = frozenset(
    {
        "ucbcomedy.com",
        "bitimprov.org",
        "secondcity.com",
        "comedysportz.com",
    }
)


def classify_show_type(
    show: Show,
    *,
    club: Optional[Club] = None,
    source_metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Return a conservative normalized show type for discovery.

    The classifier intentionally prefers ``unknown`` over weak guesses. Callers
    can pass source metadata from a platform/category API and, when safe, a
    club for high-confidence venue defaults.
    """
    metadata_text = _metadata_text(source_metadata)
    text = _classification_text(show, metadata_text)

    # Specific comedy forms before broad "comedy"/"laughs" matching.
    if _OPEN_MIC_RE.search(text):
        return "open_mic"
    if _CLASS_WORKSHOP_RE.search(text):
        return "class_workshop"
    if _IMPROV_RE.search(text):
        return "improv"
    if _SKETCH_RE.search(text):
        return "sketch"
    if _PODCAST_RE.search(text):
        return "podcast"
    if _VARIETY_RE.search(text):
        return "variety"

    category_type = _classify_platform_category(metadata_text)
    if category_type is not None:
        return category_type

    if _STANDUP_RE.search(text):
        return "standup"
    if _THEATER_RE.search(text):
        return "theater"
    if _MUSIC_RE.search(text):
        return "music"

    default_type = _classify_high_confidence_venue_default(club)
    if default_type is not None:
        return default_type

    return SHOW_TYPE_UNKNOWN


def apply_show_type(
    show: Show,
    *,
    club: Optional[Club] = None,
    source_metadata: Optional[dict[str, Any]] = None,
) -> Show:
    """Stamp ``show.show_type`` when it is blank and return the same object."""
    if not getattr(show, "show_type", None):
        show.show_type = classify_show_type(show, club=club, source_metadata=source_metadata)
    return show


def _classification_text(show: Show, metadata_text: str) -> str:
    values = [
        show.name,
        show.description,
        " ".join(show.supplied_tags or []),
        metadata_text,
    ]
    return " ".join(str(value) for value in values if value)


def _metadata_text(source_metadata: Optional[dict[str, Any]]) -> str:
    if not source_metadata:
        return ""
    values = []
    for key in ("category", "categories", "genre", "genres", "subcategory", "tags"):
        value = source_metadata.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value if item)
        elif value:
            values.append(str(value))
    return " ".join(values)


def _classify_platform_category(metadata_text: str) -> Optional[str]:
    if not metadata_text:
        return None
    if _MUSIC_RE.search(metadata_text):
        return "music"
    if _THEATER_RE.search(metadata_text):
        return "theater"
    return None


def _classify_high_confidence_venue_default(club: Optional[Club]) -> Optional[str]:
    if club is None:
        return None

    domain = _club_domain(club)
    if domain in _STANDUP_DEFAULT_DOMAINS:
        return "standup"
    if domain in _IMPROV_DEFAULT_DOMAINS:
        return "improv"

    name = (club.name or "").casefold()
    if "stand up" in name or "standup" in name:
        return "standup"
    if "improv" in name and "improv comedy club" not in name:
        return "improv"
    return None


def _club_domain(club: Club) -> str:
    raw = (club.website or "").strip().lower()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw
