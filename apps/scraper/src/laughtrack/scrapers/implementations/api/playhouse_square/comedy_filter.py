"""Comedy isolation for the genre-less Playhouse Square feed.

Playhouse Square is a multi-genre performing-arts operator (Broadway, dance,
jazz, children's theatre, stand-up). Its feed exposes **no genre/comedy tag** in
the markup and **none on the detail pages** — the only "comedy" string anywhere
is boilerplate meta text. Since there is no downstream comedy-relevance gate in
the scraper persist path (every emitted Show is persisted as a comedy show), the
scraper itself must isolate comedy before emitting, or it would flood LaughTrack
with concerts/musicals/symphony.

The isolation is a **known-comedian big-name heuristic** (the approach the task
scoped): keep an event only when its title contains a credible whole-name match
to a known comedian (the same credibility check the lineup-enrichment path uses,
``LineupHandler.get_comedians_from_show_names``) AND that comedian's STORED
popularity clears a configurable floor. The popularity floor drops data-quality
false positives — e.g. a junk "The Nutcracker" comedian row (ballet) or a
miscategorised "Professor Brian Cox" (science lecture) — whose popularity sits
well below real touring comedians (all observed real PHS acts scored >= 0.40;
the false positives scored < 0.20). The matched comedian is NOT attached to the
lineup here — the normal nightly enrichment pass re-derives the lineup from the
persisted show name.
"""

from typing import Dict, List, Set

from laughtrack.core.entities.comedian.handler import ComedianHandler
from laughtrack.core.entities.lineup.handler import LineupHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Floor on a matched comedian's stored popularity. Sits in the gap between the
# lowest observed real PHS comedian (~0.40) and the highest false positive
# (~0.19). Overridable per source via scraping_sources.metadata.min_comedian_popularity.
DEFAULT_MIN_COMEDIAN_POPULARITY = 0.30


def select_comedy_titles(
    titles: List[str],
    *,
    lineup_handler: LineupHandler,
    comedian_handler: ComedianHandler,
    min_popularity: float = DEFAULT_MIN_COMEDIAN_POPULARITY,
) -> Set[str]:
    """Return the subset of ``titles`` that name a known, sufficiently-popular comedian.

    A title is kept when at least one credible matched comedian has stored
    popularity >= ``min_popularity``.
    """
    unique_titles = [t for t in dict.fromkeys(titles) if t]
    if not unique_titles:
        return set()

    # {title: [Comedian, ...]} — already filtered by the credibility check
    # (>= 2 words, whole-word match, false-positive denylist).
    matches: Dict[str, list] = lineup_handler.get_comedians_from_show_names(
        [(t,) for t in unique_titles]
    )
    if not matches:
        return set()

    matched_names = sorted({c.name for comedians in matches.values() for c in comedians})
    popularity = comedian_handler.get_stored_popularity_by_names(matched_names)

    comedy_titles: Set[str] = set()
    dropped: list = []
    for title, comedians in matches.items():
        if any(popularity.get(c.name, 0.0) >= min_popularity for c in comedians):
            comedy_titles.add(title)
        else:
            # Matched a known comedian but every match is below the floor — kept
            # out of comedy. Log it so under-coverage (a real act below the floor)
            # is diagnosable rather than silent.
            best = max((popularity.get(c.name, 0.0) for c in comedians), default=0.0)
            dropped.append(f"{title!r} (best matched popularity {best:.3f} < {min_popularity})")
    if dropped:
        Logger.debug(
            f"playhouse_square comedy filter dropped {len(dropped)} below-floor "
            f"name-match(es): {'; '.join(dropped)}"
        )
    return comedy_titles
