"""Opt-in comedy isolation for mixed-use venue scrapers (etix, ticketleap, …).

Mixed-use venues (performing-arts theaters, music venues, event spaces) host
comedy alongside concerts, plays, dance classes, etc. Their platform scrapers
pull the venue's whole calendar, so a venue that should surface comedy ONLY opts
in via ``scraping_sources.metadata``::

    {"comedy_filter": true,
     "min_comedian_popularity": 0.30,                 # optional, default 0.30
     "comedy_title_allowlist": ["open mic", "showcase"]}  # optional substrings

A title is kept as comedy when ANY of these hold:

  1. **keyword** — title (or description) matches :func:`is_comedy_event`
     (comedy / comedian / stand-up / improv / sketch / open mic / roast).
  2. **allowlist** — title contains a configured case-insensitive substring
     (per-source escape hatch for comedy the keyword/name signals miss).
  3. **known comedian** — title names a credible comedian whose STORED
     popularity clears ``min_comedian_popularity``. This catches name-only
     touring shows that carry no comedy keyword (e.g. "Sean Patton",
     "Nick Vatterott") while a popularity floor drops data-quality false
     positives (a junk "The Nutcracker" comedian row, a science lecturer, …).

(3) generalises the playhouse_square known-comedian heuristic; (1)+(2) mirror the
wix_events / ice_house keyword filter. Combining all three covers both keyword-y
titles ("Cutthroat Improv") and name-only touring titles ("Guy Branum").

The DB-backed handlers are injected by the caller (dependency injection) so this
module stays import-light and unit-testable without a database.
"""

from typing import Dict, List, Optional, Sequence, Set

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.show.factory import is_comedy_event

# Floor on a matched comedian's stored popularity. Mirrors playhouse_square's
# default; sits in the gap between real touring comedians (observed >= ~0.40) and
# data-quality false positives (< ~0.20). Override per source via
# scraping_sources.metadata.min_comedian_popularity.
DEFAULT_MIN_COMEDIAN_POPULARITY = 0.30

COMEDY_FILTER_METADATA_KEY = "comedy_filter"


def is_comedy_filter_enabled(metadata: Optional[dict]) -> bool:
    """True when a source opts into comedy-only filtering."""
    return bool((metadata or {}).get(COMEDY_FILTER_METADATA_KEY))


def resolve_min_popularity(metadata: Optional[dict]) -> float:
    """Read the per-source popularity floor, defaulting safely."""
    try:
        return float((metadata or {}).get("min_comedian_popularity", DEFAULT_MIN_COMEDIAN_POPULARITY))
    except (TypeError, ValueError):
        return DEFAULT_MIN_COMEDIAN_POPULARITY


def resolve_allowlist(metadata: Optional[dict]) -> List[str]:
    """Read the per-source title allowlist (list of substrings)."""
    raw = (metadata or {}).get("comedy_title_allowlist")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(s) for s in raw if str(s).strip()]


def select_comedy_titles(
    titles: Sequence[str],
    *,
    lineup_handler,
    comedian_handler,
    descriptions: Optional[Dict[str, Optional[str]]] = None,
    min_popularity: float = DEFAULT_MIN_COMEDIAN_POPULARITY,
    allowlist: Optional[List[str]] = None,
) -> Set[str]:
    """Return the subset of ``titles`` that qualify as comedy.

    ``lineup_handler`` / ``comedian_handler`` are only queried for titles that
    fail the cheap keyword + allowlist checks, and only when such titles exist.
    """
    unique = [t for t in dict.fromkeys(titles) if t]
    if not unique:
        return set()
    descriptions = descriptions or {}

    allow_subs = [s.strip().lower() for s in (allowlist or []) if s and s.strip()]

    kept: Set[str] = set()
    remaining: List[str] = []
    for title in unique:
        low = title.lower()
        if allow_subs and any(sub in low for sub in allow_subs):
            kept.add(title)
        elif is_comedy_event(title, descriptions.get(title)):
            kept.add(title)
        else:
            remaining.append(title)

    if not remaining:
        return kept

    # Known-comedian heuristic for the titles with no keyword/allowlist signal.
    try:
        matches: Dict[str, list] = lineup_handler.get_comedians_from_show_names(
            [(t,) for t in remaining]
        )
    except Exception as e:  # pragma: no cover - defensive; DB hiccup
        Logger.warn(f"comedy_filter: name-match lookup failed: {e}")
        return kept

    if not matches:
        return kept

    matched_names = sorted({c.name for comedians in matches.values() for c in comedians})
    try:
        popularity = comedian_handler.get_stored_popularity_by_names(matched_names)
    except Exception as e:  # pragma: no cover - defensive; DB hiccup
        Logger.warn(f"comedy_filter: popularity lookup failed: {e}")
        popularity = {}

    dropped: List[str] = []
    for title, comedians in matches.items():
        if any(popularity.get(c.name, 0.0) >= min_popularity for c in comedians):
            kept.add(title)
        else:
            best = max((popularity.get(c.name, 0.0) for c in comedians), default=0.0)
            dropped.append(f"{title!r} (best matched popularity {best:.3f} < {min_popularity})")

    if dropped:
        Logger.debug(
            f"comedy_filter dropped {len(dropped)} below-floor name-match(es): "
            f"{'; '.join(dropped)}"
        )
    return kept
