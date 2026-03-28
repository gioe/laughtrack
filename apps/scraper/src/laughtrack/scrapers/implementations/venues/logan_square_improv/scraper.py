"""
Logan Square Improv (LSI) scraper.

Logan Square Improv uses the Crowdwork/Fourthwall Tickets platform for show
ticketing.  Their events page embeds a Fourthwall widget that calls:

  https://crowdwork.com/api/v2/lsi/shows

Response shape (when shows are present):
  {
    "message": "Shows fetched successfully",
    "status": 200,
    "type": "success",
    "data": [
      {
        "id": 11770,
        "name": "The Saturday Show",
        "url": "https://www.crowdwork.com/e/<slug>",
        "timezone": "Central Time (US & Canada)",
        "dates": ["2026-03-28T20:00:00.000-05:00"],
        "next_date": null,
        "cost": {"formatted": "$6.49 (includes fees)"},
        "description": {"body": "<p>...</p>"},
        "badges": {"spots": "Only 2 spots left"}
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

from .data import LoganSquareImprovPageData
from .transformer import LoganSquareImprovTransformer

# Mapping from Rails-style timezone names to IANA equivalents.
_RAILS_TO_IANA: dict = {
    "Central Time (US & Canada)": "America/Chicago",
    "Eastern Time (US & Canada)": "America/New_York",
    "Pacific Time (US & Canada)": "America/Los_Angeles",
    "Mountain Time (US & Canada)": "America/Denver",
}


class LoganSquareImprovScraper(BaseScraper):
    """Scraper for Logan Square Improv via Crowdwork/Fourthwall API."""

    key = "logan_square_improv"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(LoganSquareImprovTransformer(club))

    async def get_data(self, url: str) -> Optional[LoganSquareImprovPageData]:
        """
        Fetch shows from the Crowdwork API and expand into per-date PhillyImprovShow instances.

        Args:
            url: Crowdwork API URL (club.scraping_url)

        Returns:
            LoganSquareImprovPageData with one PhillyImprovShow per performance date,
            or None if the API returns no data.
        """
        try:
            response = await self.fetch_json(url)
            if not response:
                Logger.warn(
                    f"Logan Square Improv: empty response from Crowdwork API ({url})",
                    self.logger_context,
                )
                return None

            if response.get("type") == "error" or response.get("status", 200) != 200:
                Logger.warn(
                    f"Logan Square Improv: Crowdwork API returned non-success response "
                    f"(status={response.get('status')}, type={response.get('type')}) at {url}",
                    self.logger_context,
                )
                return None

            data = response.get("data")
            if not data:
                Logger.info(
                    "Logan Square Improv: no shows currently listed on Crowdwork API",
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
                extracted = _extract_performances(show)
                performances.extend(extracted)

            if not performances:
                Logger.info(
                    "Logan Square Improv: no upcoming performances parsed from Crowdwork API",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"Logan Square Improv: extracted {len(performances)} performance(s)",
                self.logger_context,
            )
            return LoganSquareImprovPageData(event_list=performances)

        except Exception as e:
            Logger.error(f"Logan Square Improv: get_data failed: {e}", self.logger_context)
            return None


def _extract_performances(show: dict) -> List[PhillyImprovShow]:
    """
    Convert one Crowdwork show dict into one PhillyImprovShow per performance date.

    A single show may have multiple performance dates in its ``dates`` array.
    Rails-style timezone names are normalised to IANA equivalents so that
    parse_datetime_with_timezone_fallback can use them as a fallback when
    date strings lack an embedded UTC offset.
    """
    name = show.get("name") or "Comedy Show"
    url = show.get("url") or ""

    raw_tz = show.get("timezone") or "America/Chicago"
    timezone = _RAILS_TO_IANA.get(raw_tz, raw_tz)

    cost_obj = show.get("cost") or {}
    cost_formatted = (cost_obj.get("formatted") or "") if isinstance(cost_obj, dict) else ""

    desc_obj = show.get("description") or {}
    description = (desc_obj.get("body") or "") if isinstance(desc_obj, dict) else ""

    badges_obj = show.get("badges") or {}
    spots = (badges_obj.get("spots") or "") if isinstance(badges_obj, dict) else ""
    sold_out = spots.lower().startswith("sold out") if spots else False

    dates = show.get("dates") or []
    if not dates:
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
