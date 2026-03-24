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

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .page_data import PhillyImprovPageData
from .transformer import PhillyImprovTransformer


class PhillyImprovTheaterScraper(BaseScraper):
    """Scraper for Philly Improv Theater (PHIT) via Crowdwork/Fourthwall API."""

    key = "philly_improv_theater"

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
        try:
            response = await self.fetch_json(url)
            if not response:
                Logger.warn("PHIT: empty response from Crowdwork API", self.logger_context)
                return None

            data = response.get("data")
            if not data:
                Logger.info("PHIT: no shows currently listed on Crowdwork API", self.logger_context)
                return None

            # ``data`` is an object keyed by show slug when shows are present;
            # it may also be provided as a list for forward-compatibility.
            shows_iterable = data.values() if isinstance(data, dict) else data

            performances: List[PhillyImprovShow] = []
            for show in shows_iterable:
                if not isinstance(show, dict):
                    continue
                extracted = _extract_performances(show)
                performances.extend(extracted)

            if not performances:
                Logger.info("PHIT: no upcoming performances parsed from Crowdwork API", self.logger_context)
                return None

            Logger.info(f"PHIT: extracted {len(performances)} performance(s)", self.logger_context)
            return PhillyImprovPageData(event_list=performances)

        except Exception as e:
            Logger.error(f"PHIT: get_data failed: {e}", self.logger_context)
            return None


def _extract_performances(show: dict) -> List[PhillyImprovShow]:
    """
    Convert one Crowdwork show dict into one PhillyImprovShow per performance date.

    A single show may have multiple performance dates in its ``dates`` array.
    """
    name = show.get("name") or "Comedy Show"
    url = show.get("url") or ""
    timezone = show.get("timezone") or "America/New_York"

    cost_obj = show.get("cost") or {}
    cost_formatted = cost_obj.get("formatted") or "" if isinstance(cost_obj, dict) else ""

    desc_obj = show.get("description") or {}
    description = desc_obj.get("body") or "" if isinstance(desc_obj, dict) else ""

    badges_obj = show.get("badges") or {}
    spots = badges_obj.get("spots") or "" if isinstance(badges_obj, dict) else ""
    sold_out = "sold" in spots.lower() if spots else False

    dates = show.get("dates") or []
    if not dates:
        # Fall back to next_date if dates array is absent
        next_date = show.get("next_date")
        if next_date:
            dates = [next_date]

    performances = []
    for date_str in dates:
        if not date_str:
            continue
        performances.append(
            PhillyImprovShow(
                name=name,
                date_str=str(date_str),
                timezone=timezone,
                url=url,
                cost_formatted=cost_formatted,
                sold_out=sold_out,
                description=description,
            )
        )

    return performances
