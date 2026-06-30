"""Indy Systems GraphQL scraper for The Lyric (Fort Collins, CO).

The Lyric (lyriccinema.com) is an indie cinema / live-events venue on the Indy
Systems ticketing platform (api-*.indy.systems). Its Quasar SPA talks to a
same-origin GraphQL proxy at ``https://www.lyriccinema.com/graphql``. Tenant and
read scope are selected by request HEADERS, not the URL:

- ``site-id: <n>``      selects the venue (The Lyric is site 7)
- ``client-type: consumer`` grants public reads (omitting it returns permission
  code 102)

Indy models every screening — films AND live events — as a "movie". This scraper:

1. queries ``currentAndUpcomingMovies`` (the ~220-title current+upcoming catalog,
   a ``MovieList`` whose ``data[]`` holds the movies),
2. keeps only live comedy by event NAME (stand-up / comedy / improv / sketch /
   comedian), dropping the ~220 film titles and the mixed "Open Mic" variety
   night, then
3. pulls each comedy movie's dated showings via ``publicShowingsForMovie`` (a
   ``ShowingList`` whose ``data[]`` holds ``Showing`` objects with a ``time``
   ISO-8601 start), producing one Show per showing.

``show_page_url`` points at the venue's own ``/movie/<urlSlug>`` page.
"""

import re
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.venues.the_lyric.data import TheLyricPageData
from laughtrack.scrapers.implementations.venues.the_lyric.event import TheLyricEvent
from laughtrack.scrapers.implementations.venues.the_lyric.transformer import (
    TheLyricEventTransformer,
)

# Comedy title allowlist — Indy mixes ~220 film titles into the same catalog, so
# only event names matching one of these survive.
_COMEDY_INCLUDE = re.compile(r"(comedy|comedian|stand[\s-]?up|improv|sketch)", re.IGNORECASE)
# The Lyric's "Open Mic" is a mixed music/poetry/comedy variety night, not a
# stand-up showcase — drop it by default (extendable via metadata).
_DEFAULT_EXCLUDE = re.compile(r"open\s*mic", re.IGNORECASE)

_MOVIES_QUERY = "{ currentAndUpcomingMovies { data { id name urlSlug } } }"
_SHOWINGS_QUERY = (
    "query($movieId: ID!) { publicShowingsForMovie(movieId: $movieId) { data { id time } } }"
)


class TheLyricScraper(BaseScraper):
    """Scraper for The Lyric (Fort Collins, CO) on the Indy Systems platform."""

    key = "the_lyric"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.default_timezone = club.timezone or "America/Denver"
        self.transformation_pipeline.register_transformer(TheLyricEventTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Single target: the venue's Indy Systems GraphQL endpoint."""
        return [self.club.scraping_url]

    def _headers(self) -> dict:
        """Tenant/scope headers — site-id selects the venue, client-type grants reads."""
        site_id = str((self.club.source_metadata or {}).get("indy_site_id", "")).strip()
        return {
            "content-type": "application/json",
            "site-id": site_id,
            "client-type": "consumer",
        }

    def _exclude_pattern(self) -> Optional[re.Pattern]:
        """Resolve the title-exclusion regex (metadata override, else 'Open Mic')."""
        raw = (self.club.source_metadata or {}).get("exclude_title_patterns")
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            terms = [str(p).strip() for p in raw if str(p).strip()]
            if terms:
                return re.compile("|".join(terms), re.IGNORECASE)
        return _DEFAULT_EXCLUDE

    def _is_comedy(self, name: Optional[str], exclude: Optional[re.Pattern]) -> bool:
        title = name or ""
        if exclude and exclude.search(title):
            return False
        return bool(_COMEDY_INCLUDE.search(title))

    def _page_url(self, url_slug: str) -> str:
        """The venue's own /movie/<urlSlug> page, derived from the GraphQL host.

        Falls back to the venue website if a movie is missing its slug, so we
        never emit a degenerate ``…/movie/`` URL as the show page / ticket link.
        """
        base = (self.club.scraping_url or "").split("/graphql", 1)[0].rstrip("/")
        if not url_slug:
            return self.club.website or base
        return f"{base}/movie/{url_slug}"

    async def get_data(self, target: str) -> Optional[TheLyricPageData]:
        """Fetch comedy movies + their showings from the Indy Systems GraphQL proxy."""
        url = self.club.scraping_url
        headers = self._headers()

        movies_resp = await self.post_json(url, {"query": _MOVIES_QUERY}, headers=headers)
        movies = (
            (((movies_resp or {}).get("data") or {}).get("currentAndUpcomingMovies") or {}).get(
                "data"
            )
            or []
        )
        if not movies:
            Logger.info(f"{self._log_prefix}: no current/upcoming movies returned", self.logger_context)
            return None

        exclude = self._exclude_pattern()
        comedy_movies = [m for m in movies if self._is_comedy(m.get("name"), exclude)]
        if not comedy_movies:
            Logger.info(
                f"{self._log_prefix}: no comedy titles among {len(movies)} current/upcoming movies",
                self.logger_context,
            )
            return None

        events: List[TheLyricEvent] = []
        for movie in comedy_movies:
            movie_id = movie.get("id")
            if movie_id is None:
                continue
            showings_resp = await self.post_json(
                url,
                {"query": _SHOWINGS_QUERY, "variables": {"movieId": str(movie_id)}},
                headers=headers,
            )
            showings = (
                (((showings_resp or {}).get("data") or {}).get("publicShowingsForMovie") or {}).get(
                    "data"
                )
                or []
            )
            page_url = self._page_url(movie.get("urlSlug") or "")
            for showing in showings:
                start = showing.get("time")
                if not start:
                    continue
                events.append(
                    TheLyricEvent(
                        name=movie.get("name") or "Comedy Show",
                        start_dt=start,
                        show_page_url=page_url,
                        timezone_name=self.default_timezone,
                    )
                )

        if not events:
            Logger.info(
                f"{self._log_prefix}: {len(comedy_movies)} comedy title(s) had no upcoming showings",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} comedy showing(s) "
            f"from {len(comedy_movies)} comedy title(s)",
            self.logger_context,
        )
        return TheLyricPageData(event_list=events)
