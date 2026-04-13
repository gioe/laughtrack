"""
Rails Comedy scraper.

Rails Comedy is a DC-based sketch and improv theater at the DC Arts Center
(2438 18th St NW, Washington DC).  Their shows page embeds a Crowdwork/Fourthwall
Tickets widget that calls:

  https://crowdwork.com/api/v2/railscomedy/shows

Response shape (when shows are present):
  {
    "message": "Shows fetched successfully",
    "status": 200,
    "type": "success",
    "data": [
      {
        "id": 9539,
        "name": "Meet Cute: Live Blind Date Show",
        "url": "https://www.crowdwork.com/e/<slug>",
        "timezone": "Eastern Time (US & Canada)",
        "dates": ["2026-05-02T19:00:00.000-04:00"],
        "next_date": "2026-05-02T19:00:00.000-04:00",
        "cost": {"formatted": "$15"},
        "description": {"body": "<p>...</p>"},
        "badges": {"spots": "Only 2 spots left"}
      },
      ...
    ]
  }

When no shows are scheduled, ``data`` is an empty list ``[]``.

Note: the ``timezone`` field uses Rails-style timezone names (e.g.
"Eastern Time (US & Canada)") rather than IANA names.  Date strings from
this API include a UTC offset (e.g. ``-04:00``), so the timezone string
is only used as a fallback when the offset is absent.  The scraper
normalises known Rails names to their IANA equivalents before storing them.

Pipeline:
  1. collect_scraping_targets() -> returns [scraping_url] (default)
  2. get_data(url)              -> calls Crowdwork API, expands multi-date shows
                                   into individual PhillyImprovShow instances
  3. transformation_pipeline    -> PhillyImprovShow.to_show() -> Show objects
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.foundation.exceptions import NetworkError
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import (
    RAILS_TO_IANA,
    extract_performances,
)

from .data import RailsComedyPageData
from .transformer import RailsComedyTransformer


class RailsComedyScraper(BaseScraper):
    """Scraper for Rails Comedy via Crowdwork/Fourthwall API."""

    key = "rails_comedy"
    _RETRY_ATTEMPTS = 2   # retries after the initial attempt
    _RETRY_DELAY = 3.0    # seconds between retries

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(RailsComedyTransformer(club))

    async def get_data(self, url: str) -> Optional[RailsComedyPageData]:
        """
        Fetch shows from the Crowdwork API and expand into per-date PhillyImprovShow instances.

        Args:
            url: Crowdwork API URL (club.scraping_url)

        Returns:
            RailsComedyPageData with one PhillyImprovShow per performance date,
            or None if the API returns no data.
        """
        response = None
        attempt = 0
        while attempt <= self._RETRY_ATTEMPTS:
            try:
                response = await self.fetch_json(url)
                break
            except NetworkError as e:
                if e.status_code is not None and 500 <= e.status_code < 600:
                    attempt += 1
                    if attempt <= self._RETRY_ATTEMPTS:
                        Logger.warning(
                            f"{self._log_prefix}: HTTP {e.status_code} fetching Crowdwork API — retrying ({attempt}/{self._RETRY_ATTEMPTS})",
                            self.logger_context,
                        )
                        await asyncio.sleep(self._RETRY_DELAY)
                    else:
                        Logger.error(
                            f"{self._log_prefix}: Network error fetching {url} after {self._RETRY_ATTEMPTS} retries: {e}",
                            self.logger_context,
                        )
                        return None
                else:
                    Logger.error(f"{self._log_prefix}: Network error fetching {url}: {e}", self.logger_context)
                    return None
            except Exception as e:
                Logger.error(f"{self._log_prefix}: get_data failed: {e}", self.logger_context)
                return None

        if not response:
            Logger.warn(
                f"{self._log_prefix}: empty response from Crowdwork API ({url})",
                self.logger_context,
            )
            return None

        if response.get("type") == "error" or response.get("status", 200) != 200:
            Logger.warn(
                f"{self._log_prefix}: Crowdwork API returned non-success response "
                f"(status={response.get('status')}, type={response.get('type')}) at {url}",
                self.logger_context,
            )
            return None

        data = response.get("data")
        if not data:
            Logger.info(
                f"{self._log_prefix}: no shows currently listed on Crowdwork API",
                self.logger_context,
            )
            return None

        # ``data`` is a list of show dicts; handle dict-keyed format as well
        # for forward-compatibility with other Crowdwork venues.
        shows_iterable = data.values() if isinstance(data, dict) else data

        performances: List[PhillyImprovShow] = []
        for show in shows_iterable:
            if not isinstance(show, dict):
                continue
            extracted = extract_performances(show, default_timezone="America/New_York", rails_to_iana=RAILS_TO_IANA)
            performances.extend(extracted)

        if not performances:
            Logger.info(
                f"{self._log_prefix}: no upcoming performances parsed from Crowdwork API",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(performances)} performance(s)",
            self.logger_context,
        )
        return RailsComedyPageData(event_list=performances)
