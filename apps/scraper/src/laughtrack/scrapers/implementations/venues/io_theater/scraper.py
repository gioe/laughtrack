"""
iO Theater Chicago scraper.

iO Theater (ImprovOlympic) uses the Crowdwork/Fourthwall Tickets platform for
show ticketing.  Their homepage embeds a Fourthwall widget that calls:

  https://crowdwork.com/api/v2/iotheater/shows

Response shape (when shows are present):
  {
    "message": "Shows fetched successfully",
    "status": 200,
    "type": "success",
    "data": [
      {
        "id": 13225,
        "name": "Show Title",
        "url": "https://www.crowdwork.com/e/<slug>",
        "timezone": "Central Time (US & Canada)",
        "dates": ["2026-03-21T19:00:00.000-05:00"],
        "next_date": null,
        "cost": {"formatted": "$23.40 (includes fees)"},
        "description": {"body": "<p>...</p>"},
        "badges": {"spots": null}
      },
      ...
    ]
  }

When no shows are scheduled, ``data`` is an empty list ``[]``.

Note: the ``timezone`` field uses Rails-style timezone names (e.g.
"Central Time (US & Canada)") rather than IANA names.  Date strings from
this API include a UTC offset (e.g. ``-05:00``), so the timezone string
is only used as a fallback when the offset is absent.  The scraper
normalises known Rails names to their IANA equivalents before storing them.

Pipeline:
  1. collect_scraping_targets() → returns [scraping_url] (default)
  2. get_data(url)              → calls Crowdwork API, expands multi-date shows
                                  into individual PhillyImprovShow instances
  3. transformation_pipeline    → PhillyImprovShow.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import (
    RAILS_TO_IANA,
    extract_performances,
)

from .data import IOTheaterPageData
from .transformer import IOTheaterTransformer


class IOTheaterScraper(BaseScraper):
    """Scraper for iO Theater Chicago via Crowdwork/Fourthwall API."""

    key = "io_theater"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(IOTheaterTransformer(club))

    async def get_data(self, url: str) -> Optional[IOTheaterPageData]:
        """
        Fetch shows from the Crowdwork API and expand into per-date PhillyImprovShow instances.

        Args:
            url: Crowdwork API URL (club.scraping_url)

        Returns:
            IOTheaterPageData with one PhillyImprovShow per performance date,
            or None if the API returns no data.
        """
        try:
            response = await self.fetch_json(url)
            if not response:
                Logger.warn(
                    f"iO Theater: empty response from Crowdwork API ({url})",
                    self.logger_context,
                )
                return None

            if response.get("type") == "error" or response.get("status", 200) != 200:
                Logger.warn(
                    f"iO Theater: Crowdwork API returned non-success response "
                    f"(status={response.get('status')}, type={response.get('type')}) at {url}",
                    self.logger_context,
                )
                return None

            data = response.get("data")
            if not data:
                Logger.info(
                    "iO Theater: no shows currently listed on Crowdwork API",
                    self.logger_context,
                )
                return None

            # ``data`` is a list of show dicts for iO Theater; handle dict-keyed
            # format as well for forward-compatibility with other Crowdwork venues.
            shows_iterable = data.values() if isinstance(data, dict) else data

            performances: List[PhillyImprovShow] = []
            for show in shows_iterable:
                if not isinstance(show, dict):
                    continue
                extracted = extract_performances(show, default_timezone="America/Chicago", rails_to_iana=RAILS_TO_IANA)
                performances.extend(extracted)

            if not performances:
                Logger.info(
                    "iO Theater: no upcoming performances parsed from Crowdwork API",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"iO Theater: extracted {len(performances)} performance(s)",
                self.logger_context,
            )
            return IOTheaterPageData(event_list=performances)

        except Exception as e:
            Logger.error(f"iO Theater: get_data failed: {e}", self.logger_context)
            return None

