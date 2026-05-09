"""Generic Crowdwork/Fourthwall Tickets scraper."""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.foundation.exceptions import NetworkError
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA, extract_performances
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


@dataclass
class CrowdworkPageData(EventListContainer[PhillyImprovShow]):
    """Raw extracted Crowdwork API data, expanded to one event per performance."""

    event_list: List[PhillyImprovShow]


class CrowdworkTransformer(DataTransformer[PhillyImprovShow]):
    """Transformer for events already normalized from Crowdwork payloads."""


class GenericCrowdworkScraper(BaseScraper):
    """Configurable scraper for Crowdwork/Fourthwall venue APIs."""

    key = "crowdwork"
    page_data_cls: Type[EventListContainer[PhillyImprovShow]] = CrowdworkPageData
    transformer_cls: Type[DataTransformer[PhillyImprovShow]] = CrowdworkTransformer
    default_timezone = "America/Chicago"
    rails_to_iana: Optional[Dict[str, str]] = None

    _RETRY_ATTEMPTS = 2
    _RETRY_DELAY = 3.0

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self._configure_from_source_metadata()
        self.transformation_pipeline.register_transformer(self.transformer_cls(club))

    def _configure_from_source_metadata(self) -> None:
        metadata = self.club.source_metadata or {}
        default_timezone = metadata.get("default_timezone")
        if isinstance(default_timezone, str) and default_timezone:
            self.default_timezone = default_timezone
        elif self.club.timezone:
            self.default_timezone = self.club.timezone

        rails_to_iana = metadata.get("rails_to_iana")
        if rails_to_iana is True:
            self.rails_to_iana = RAILS_TO_IANA
        elif isinstance(rails_to_iana, dict):
            self.rails_to_iana = {
                str(key): str(value)
                for key, value in rails_to_iana.items()
                if key is not None and value is not None
            }
        elif rails_to_iana is False:
            self.rails_to_iana = None

    async def get_data(self, url: str) -> Optional[EventListContainer[PhillyImprovShow]]:
        """Fetch Crowdwork API JSON and return expanded performance events."""
        response = await self._fetch_crowdwork_response(url)
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

        performances = self._extract_payload_performances(data)
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
        return self.page_data_cls(event_list=performances)

    async def _fetch_crowdwork_response(self, url: str) -> Optional[dict]:
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
                            f"{self._log_prefix}: HTTP {e.status_code} fetching Crowdwork API "
                            f"- retrying ({attempt}/{self._RETRY_ATTEMPTS})",
                            self.logger_context,
                        )
                        await asyncio.sleep(self._RETRY_DELAY)
                    else:
                        Logger.error(
                            f"{self._log_prefix}: Network error fetching {url} after "
                            f"{self._RETRY_ATTEMPTS} retries: {e}",
                            self.logger_context,
                        )
                        return None
                else:
                    Logger.error(
                        f"{self._log_prefix}: Network error fetching {url}: {e}",
                        self.logger_context,
                    )
                    return None
            except Exception as e:
                Logger.error(f"{self._log_prefix}: get_data failed: {e}", self.logger_context)
                return None
        return response

    def _extract_payload_performances(self, data: object) -> List[PhillyImprovShow]:
        shows_iterable = data.values() if isinstance(data, dict) else data
        if not isinstance(shows_iterable, list) and not hasattr(shows_iterable, "__iter__"):
            return []

        performances: List[PhillyImprovShow] = []
        for show in shows_iterable:
            if not isinstance(show, dict):
                continue
            performances.extend(
                extract_performances(
                    show,
                    default_timezone=self.default_timezone,
                    rails_to_iana=self.rails_to_iana,
                )
            )
        return performances
