"""Parsing helpers for the 1234ticket landing-data API.

The 1234ticket platform (api.1234ticket.com/api_040/landing-data) returns every
event across the platform's venues. Each event carries:
  - ``title``     — often an abbreviated lowercase first name (e.g. "willy",
                    "edy"); unreliable as a display name.
  - ``description`` — a short tagline.
  - ``link``      — ``live.1234ticket.com/events/<slug>-<hash>``; the slug is the
                    richest text (e.g. "el-show-de-george-harris").
  - ``date``      — the show DATE, expressed as midnight venue-local in UTC
                    (e.g. "2026-06-27T04:00:00Z" = midnight EDT on Jun 27).
  - ``time``      — the show TIME OF DAY as a true-UTC instant on a throwaway
                    date (e.g. "...T00:30:00Z" = 8:30 PM EDT). Only the
                    time-of-day is meaningful.
  - ``venue``     — nested venue object with ``id`` (UUID) and ``name``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from dateutil import parser as dateutil_parser

# Trailing "-<hash>" segment 1234ticket appends to every event slug.
_SLUG_HASH_RE = re.compile(r"-[0-9a-f]{8,}$", re.IGNORECASE)
# Normalize separators so substring filters match slug text ("george-harris"
# -> "george harris") and title/description alike.
_SEP_RE = re.compile(r"[-_]+")


def event_slug(link: str) -> str:
    """Return the event slug (last path segment, trailing hash stripped)."""
    if not link:
        return ""
    slug = link.rstrip("/").rsplit("/", 1)[-1]
    return _SLUG_HASH_RE.sub("", slug)


def display_name(title: Optional[str], link: str) -> str:
    """Best human-readable show name.

    Prefer a multi-word title (e.g. "El Show De George Harris"); otherwise
    de-slugify the link tail, since the bare ``title`` is frequently an
    abbreviated single word ("willy", "edy").
    """
    title = (title or "").strip()
    if len(title.split()) >= 2:
        return title
    slug = event_slug(link)
    if slug:
        return slug.replace("-", " ").replace("_", " ").title()
    return title or "1234ticket Event"


def normalize_for_match(*parts: Optional[str]) -> str:
    """Lowercase, hyphen/underscore-collapsed text for substring filtering."""
    joined = " ".join(p for p in parts if p)
    return _SEP_RE.sub(" ", joined).lower()


def show_datetime(date_raw: str, time_raw: Optional[str], tz_name: str) -> Optional[datetime]:
    """Combine the event's DATE (from ``date``) with its TIME OF DAY (from
    ``time``) into a single timezone-aware UTC datetime.

    The venue-local calendar date comes from ``date`` and the venue-local clock
    time comes from ``time`` (both source fields are UTC instants; only the date
    of the former and the time of the latter are meaningful). Falls back to a
    venue-local default of 20:00 when ``time`` is absent/unparseable.
    """
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/New_York")

    try:
        local_date = dateutil_parser.parse(date_raw).astimezone(tz).date()
    except (ValueError, TypeError):
        return None

    local_time = None
    if time_raw:
        try:
            local_time = dateutil_parser.parse(time_raw).astimezone(tz).timetz()
        except (ValueError, TypeError):
            local_time = None

    if local_time is not None:
        local_dt = datetime.combine(local_date, local_time.replace(tzinfo=None), tzinfo=tz)
    else:
        local_dt = datetime(local_date.year, local_date.month, local_date.day, 20, 0, tzinfo=tz)

    return local_dt.astimezone(timezone.utc)


def parse_events(payload: object) -> List[dict]:
    """Pull the events list out of a landing-data response payload."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    events = data.get("events")
    return [e for e in events if isinstance(e, dict)] if isinstance(events, list) else []
