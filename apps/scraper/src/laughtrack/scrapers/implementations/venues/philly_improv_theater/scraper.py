"""
Philly Improv Theater (PHIT) scraper.

PHIT uses the Crowdwork/Fourthwall Tickets platform for show ticketing.
Their homepage embeds a Fourthwall widget that calls:

  https://crowdwork.com/api/v2/phillyimprovtheater/shows

Response shape (when shows are present):
  {
    "status": 200,
    "data": {
      "<slug>": {
        "name": "SPRING PHEST 2026",
        "url": "https://crowdwork.com/e/<slug>",
        "timezone": "America/New_York",
        "dates": ["2026-05-15T19:00:00", "2026-05-16T19:00:00"],
        "cost": {"formatted": "$15"},
        "description": {"body": "<p>...</p>"},
        "badges": {"spots": "Sold Out"}
      },
      ...
    }
  }

When no shows are scheduled, ``data`` is an empty list ``[]``.

Pipeline:
  1. collect_scraping_targets() → returns [scraping_url] (default)
  2. get_data(url)              → calls Crowdwork API, expands multi-date shows
                                  into individual PhillyImprovShow instances
  3. transformation_pipeline    → PhillyImprovShow.to_show() → Show objects
"""

import asyncio
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.foundation.exceptions import NetworkError
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import extract_performances

from .page_data import PhillyImprovPageData
from .transformer import PhillyImprovTransformer


class PhillyImprovTheaterScraper(BaseScraper):
    """Scraper for Philly Improv Theater (PHIT) via Crowdwork/Fourthwall API."""

    key = "philly_improv_theater"
    _RETRY_ATTEMPTS = 2   # retries after the initial attempt
    _RETRY_DELAY = 3.0    # seconds between retries

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(PhillyImprovTransformer(club))

    async def get_data(self, url: str) -> Optional[PhillyImprovPageData]:
        """
        Fetch shows from the Crowdwork API and expand into per-date PhillyImprovShow instances.

        Args:
            url: Crowdwork API URL (club.scraping_url)

        Returns:
            PhillyImprovPageData with one PhillyImprovShow per performance date,
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
            Logger.info(f"{self._log_prefix}: no shows currently listed on Crowdwork API", self.logger_context)
            return None

        # ``data`` is an object keyed by show slug when shows are present;
        # it may also be provided as a list for forward-compatibility.
        shows_iterable = data.values() if isinstance(data, dict) else data

        performances: List[PhillyImprovShow] = []
        for show in shows_iterable:
            if not isinstance(show, dict):
                continue
            extracted = extract_performances(show, default_timezone="America/New_York")
            performances.extend(extracted)

        if not performances:
            Logger.info(f"{self._log_prefix}: no upcoming performances parsed from Crowdwork API", self.logger_context)
            return None

        Logger.info(f"{self._log_prefix}: extracted {len(performances)} performance(s)", self.logger_context)
        return PhillyImprovPageData(event_list=performances)

