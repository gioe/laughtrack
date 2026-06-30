"""
Comedy Mothership scraper implementation.

Comedy Mothership (320 E 6th St, Austin TX) is Joe Rogan's comedy club.
Shows are listed at comedymothership.com/shows (server-rendered Next.js HTML).
The site uses Vercel hosting with bot protection; fetching with no custom
headers via curl_cffi's Chrome impersonation bypasses this protection.
When curl-cffi is rate-limited (HTTP 429) or bot-blocked, the request
automatically falls back to a Playwright headless browser via HttpClient.

Ticket purchases are handled through SquadUP, embedded on the show detail
page (comedymothership.com/shows/{id}).

Pipeline:
  1. collect_scraping_targets() → [scraping_url] (base class default)
  2. get_data(url)              → fetches all show pages (?page=N pagination),
                                  returns ComedyMothershipPageData
  3. transformation_pipeline   → ComedyMothershipEvent.to_show() → Show objects
"""

import asyncio
import os
import re
from typing import List, Optional

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_mothership import ComedyMothershipEvent
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .extractor import ComedyMothershipEventExtractor
from .data import ComedyMothershipPageData
from .transformer import ComedyMothershipEventTransformer

_MAX_PAGES = 10

# Detail-page price enrichment. Each show's detail page embeds the full
# SquadUP event object in its Next.js RSC flight payload; the price tiers live
# at event.event_dates[].price_tiers[]. The flight payload is an *escaped*
# JSON string (quotes appear as \"), not a clean application/json block, so we
# regex the tier prices out tolerantly rather than json.loads the whole page.
_DETAIL_URL_TEMPLATE = "https://comedymothership.com/shows/{show_id}"
_DEFAULT_PRICE_FETCH_CONCURRENCY = 5

# Locate each price_tiers array. ``\\*"`` tolerates the escaped (\") or plain
# (") quoting of the flight payload so the same pattern works on either form.
_PRICE_TIERS_RE = re.compile(r"price_tiers")
_TIER_PRICE_RE = re.compile(r'\\*"price\\*"\s*:\s*\\*"(\d+(?:\.\d+)?)\\*"')


def _balanced_bracket_slice(text: str, start: int, max_len: int = 8000) -> Optional[str]:
    """Return the ``[...]`` slice beginning at ``start`` (a ``[``), bracket-balanced.

    The flight payload escapes quotes but leaves ``[``/``]`` literal, so a
    simple depth counter recovers the price_tiers array. Bounded by
    ``max_len`` so a malformed payload can't run away. Returns ``None`` if no
    balanced close is found within the window.
    """
    depth = 0
    end = min(len(text), start + max_len)
    for i in range(start, end):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _extract_min_price(html: Optional[str]) -> Optional[float]:
    """Extract the minimum ticket price from a Comedy Mothership detail page.

    Locates each ``price_tiers`` array in the embedded SquadUP event object and
    returns the smallest tier price across all of them (e.g. GA 40.0 vs Booth
    50.0 → 40.0). Returns ``None`` when no price tier is found so the caller can
    degrade to a price-less ticket.
    """
    if not html:
        return None
    prices: List[float] = []
    for m in _PRICE_TIERS_RE.finditer(html):
        bracket = html.find("[", m.end(), m.end() + 64)
        if bracket == -1:
            continue
        array_str = _balanced_bracket_slice(html, bracket)
        if array_str is None:
            continue
        for pm in _TIER_PRICE_RE.finditer(array_str):
            try:
                prices.append(float(pm.group(1)))
            except (TypeError, ValueError):
                continue
    return min(prices) if prices else None


class ComedyMothershipScraper(BaseScraper):
    """
    Scraper for Comedy Mothership (Austin, TX).

    Bypasses Vercel Bot Protection by using curl_cffi Chrome impersonation
    with no custom request headers — the TLS fingerprint alone is sufficient.
    Falls back to Playwright on HTTP 429 or bot-block responses.
    """

    key = "comedy_mothership"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyMothershipEventTransformer(club)
        )

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

        async with AsyncSession(impersonate="chrome124") as session:
            for page in range(1, _MAX_PAGES + 1):
                page_url = base_url if page == 1 else f"{base_url}?page={page}"

                try:
                    html = await HttpClient.fetch_html(
                        session,
                        page_url,
                        headers=None,
                        logger_context=self.logger_context,
                        scraper_key=self.key,
                    )
                except Exception as e:
                    Logger.error(
                        f"{self._log_prefix}: error fetching {page_url}: {e}",
                        self.logger_context,
                    )
                    break

                if not html:
                    break

                events = ComedyMothershipEventExtractor.extract_shows(html, timezone)
                Logger.debug(
                    f"{self._log_prefix}: page {page}: {len(events)} events extracted",
                    self.logger_context,
                )

                if not events:
                    break

                for event in events:
                    if event.show_id not in seen_ids:
                        seen_ids.add(event.show_id)
                        all_events.append(event)

            if all_events:
                await self._enrich_prices(session, all_events)

        if not all_events:
            self._warn_empty_extraction(url, extra={"last_page": page})
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(all_events)} events total",
            self.logger_context,
        )
        return ComedyMothershipPageData(event_list=all_events)

    async def _enrich_prices(
        self, session: AsyncSession, events: List[ComedyMothershipEvent]
    ) -> None:
        """Fetch each show's detail page and set ``event.price`` to the min tier.

        Reuses the already-impersonated ``session`` (one extra GET per show).
        Concurrency is bounded by a semaphore so a slow or blocked detail page
        throttles rather than stampedes, and per-show failures are swallowed so
        one bad page leaves that show price-less rather than sinking the run.
        """
        try:
            concurrency = int(
                os.environ.get(
                    "COMEDY_MOTHERSHIP_PRICE_CONCURRENCY",
                    _DEFAULT_PRICE_FETCH_CONCURRENCY,
                )
            )
        except (TypeError, ValueError):
            concurrency = _DEFAULT_PRICE_FETCH_CONCURRENCY
        concurrency = max(1, concurrency)
        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(event: ComedyMothershipEvent) -> None:
            detail_url = _DETAIL_URL_TEMPLATE.format(show_id=event.show_id)
            async with sem:
                try:
                    html = await HttpClient.fetch_html(
                        session,
                        detail_url,
                        headers=None,
                        logger_context=self.logger_context,
                        scraper_key=self.key,
                    )
                except Exception as e:
                    Logger.debug(
                        f"{self._log_prefix}: price fetch failed for show "
                        f"{event.show_id}: {e}",
                        self.logger_context,
                    )
                    return
            price = _extract_min_price(html)
            if price is not None:
                event.price = price

        await asyncio.gather(*(_fetch_one(event) for event in events))
