"""
Comedy Mothership scraper implementation.

Comedy Mothership (320 E 6th St, Austin TX) is Joe Rogan's comedy club.
Shows are listed at comedymothership.com/shows (server-rendered Next.js HTML).
The site uses Vercel hosting with bot protection; fetching with no custom
headers via curl_cffi's Chrome impersonation bypasses this protection.

Ticket purchases are handled through SquadUP, embedded on the show detail
page (comedymothership.com/shows/{id}).

Pipeline:
  1. collect_scraping_targets() → [scraping_url] (base class default)
  2. get_data(url)              → fetches all show pages (?page=N pagination),
                                  returns ComedyMothershipPageData
  3. transformation_pipeline   → ComedyMothershipEvent.to_show() → Show objects
"""

from typing import Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import ComedyMothershipEventExtractor
from .page_data import ComedyMothershipPageData
from .transformer import ComedyMothershipEventTransformer

_MAX_PAGES = 10


class ComedyMothershipScraper(BaseScraper):
    """
    Scraper for Comedy Mothership (Austin, TX).

    Bypasses Vercel Bot Protection by using curl_cffi Chrome impersonation
    with no custom request headers — the TLS fingerprint alone is sufficient.
    """

    key = "comedy_mothership"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyMothershipEventTransformer(club)
        )

    async def _fetch_shows_html(self, url: str) -> Optional[str]:
        """
        Fetch shows page HTML using bare Chrome impersonation (no app headers).

        Vercel's bot protection blocks requests that include common scraper
        header combinations. Sending no extra headers avoids this.
        """
        try:
            async with AsyncSession(impersonate="chrome124") as session:
                response = await session.get(url)
                if response.status_code != 200:
                    Logger.warn(
                        f"ComedyMothershipScraper: HTTP {response.status_code} fetching {url}",
                        self.logger_context,
                    )
                    return None
                return response.text
        except Exception as e:
            Logger.error(
                f"ComedyMothershipScraper: error fetching {url}: {e}",
                self.logger_context,
            )
            return None

    async def get_data(self, url: str) -> Optional[ComedyMothershipPageData]:
        """
        Fetch all Comedy Mothership show pages (paginated) and extract events.

        Args:
            url: The shows listing URL (e.g., https://comedymothership.com/shows)

        Returns:
            ComedyMothershipPageData containing all events, or None
        """
        timezone = self.club.timezone or "America/Chicago"
        base_url = url.split("?")[0]

        all_events = []
        seen_ids: set = set()

        for page in range(1, _MAX_PAGES + 1):
            page_url = base_url if page == 1 else f"{base_url}?page={page}"

            html = await self._fetch_shows_html(page_url)
            if not html:
                break

            events = ComedyMothershipEventExtractor.extract_shows(html, timezone)
            Logger.debug(
                f"ComedyMothershipScraper: page {page}: {len(events)} events extracted",
                self.logger_context,
            )

            if not events:
                break

            for event in events:
                if event.show_id not in seen_ids:
                    seen_ids.add(event.show_id)
                    all_events.append(event)

        if not all_events:
            Logger.info(
                f"ComedyMothershipScraper: no events found at {url}",
                self.logger_context,
            )
            return None

        Logger.info(
            f"ComedyMothershipScraper: extracted {len(all_events)} events total",
            self.logger_context,
        )
        return ComedyMothershipPageData(event_list=all_events)
