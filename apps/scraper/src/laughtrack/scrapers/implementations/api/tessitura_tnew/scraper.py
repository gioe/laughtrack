"""Generic Tessitura TNEW event-listing scraper.

TNEW storefronts render list pages from ``/api/products/productionseasons``.
The browser first loads ``/events?view=list`` to receive Incapsula/session
cookies and a hidden request-verification token, then POSTs a form-encoded date
window to the production-seasons endpoint.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, List, Optional
from urllib.parse import urlencode, urlparse

import pytz
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import TessituraTNEWPageData
from .extractor import extract_events
from .transformer import TessituraTNEWEventTransformer

_API_PATH = "/api/products/productionseasons"
_VAR_RE = re.compile(r"\b(?P<name>listingStartDate|listingEndDate)\s*=\s*[\"'](?P<value>[^\"']+)")


@dataclass(frozen=True)
class TNEWListingConfig:
    events_url: str
    api_url: str


@dataclass(frozen=True)
class TNEWListingState:
    request_token: str
    start_date: datetime
    end_date: datetime


class TessituraTNEWScraper(BaseScraper):
    """Production-season API scraper for Tessitura TNEW storefronts."""

    key = "tessitura_tnew"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(TessituraTNEWEventTransformer(club))

    def _metadata(self) -> dict[str, Any]:
        return getattr(self.club, "source_metadata", None) or {}

    def _keyword_ids(self) -> str:
        """Optional TNEW genre/keyword filter for mixed-use storefronts.

        Single-purpose comedy storefronts (e.g. Groundlings) leave this empty
        and ingest every production. A performing-arts center that runs comedy
        alongside concerts/theatre/ballet sets ``metadata.keyword_ids`` to its
        Comedy genre id(s) so the production-seasons API returns only comedy
        server-side (e.g. Gallo Center ``keyword_ids="78"``). Accepts a string,
        int, or list of ids; serialized comma-separated for the form body.
        """
        raw = self._metadata().get("keyword_ids")
        if raw is None:
            return ""
        if isinstance(raw, (list, tuple)):
            return ",".join(str(part).strip() for part in raw if str(part).strip())
        return str(raw).strip()

    def _config(self) -> Optional[TNEWListingConfig]:
        meta = self._metadata()
        raw_events_url = meta.get("events_url") or self.club.scraping_url
        if not raw_events_url:
            return None
        events_url = URLUtils.normalize_url(str(raw_events_url))
        raw_api_url = meta.get("api_url")
        if raw_api_url:
            api_url = URLUtils.normalize_url(str(raw_api_url))
        else:
            parsed = urlparse(events_url)
            api_url = f"{parsed.scheme}://{parsed.netloc}{_API_PATH}"
        return TNEWListingConfig(events_url=events_url, api_url=api_url)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        config = self._config()
        if config is None:
            Logger.warn(
                f"{self._log_prefix}: no TNEW events_url/source_url configured",
                self.logger_context,
            )
            return []
        return [config.events_url]

    async def get_data(self, target: ScrapingTarget) -> Optional[TessituraTNEWPageData]:
        config = self._config()
        if config is None:
            return None
        events_url = str(target) if target else config.events_url

        listing_html = await self.fetch_html(events_url)
        if not listing_html:
            Logger.warn(
                f"{self._log_prefix}: TNEW listing returned empty HTML: {events_url}",
                self.logger_context,
            )
            return None

        state = self._parse_listing_state(listing_html)
        if state is None:
            Logger.warn(
                f"{self._log_prefix}: could not extract TNEW token/date window from {events_url}",
                self.logger_context,
            )
            return None

        productions = await self._fetch_productions(config.api_url, events_url, state)
        if not productions:
            Logger.warn(
                f"{self._log_prefix}: TNEW production-seasons endpoint returned no productions",
                self.logger_context,
            )
            return None

        events = extract_events(productions, base_url=events_url)
        if not events:
            Logger.warn(
                f"{self._log_prefix}: no TNEW performances extracted from production seasons",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: extracted {len(events)} TNEW performance(s)",
            self.logger_context,
        )
        return TessituraTNEWPageData(event_list=events)

    def _parse_listing_state(self, html: str) -> Optional[TNEWListingState]:
        soup = BeautifulSoup(html or "", "html.parser")
        token_input = soup.find("input", attrs={"name": "__RequestVerificationToken"})
        token = str(token_input.get("value") or "").strip() if token_input else ""
        if not token:
            return None

        values = {match.group("name"): match.group("value") for match in _VAR_RE.finditer(html)}
        timezone_name = self.club.timezone or "America/New_York"
        start_dt = self._parse_listing_date(values.get("listingStartDate"), timezone_name, end=False)
        end_dt = self._parse_listing_date(values.get("listingEndDate"), timezone_name, end=True)
        if start_dt is None or end_dt is None:
            return None
        return TNEWListingState(request_token=token, start_date=start_dt, end_date=end_dt)

    @staticmethod
    def _parse_listing_date(
        raw: Optional[str], timezone_name: str, *, end: bool
    ) -> Optional[datetime]:
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.strip())
        except ValueError:
            return None
        try:
            tz = pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("America/New_York")

        local_time = time(23, 59, 59) if end else time(0, 0, 0)
        local_naive = datetime.combine(parsed.date(), local_time)
        return tz.localize(local_naive)

    async def _fetch_productions(
        self, api_url: str, events_url: str, state: TNEWListingState
    ) -> list[dict[str, Any]]:
        body = urlencode(
            {
                "keywordIds": self._keyword_ids(),
                "startDate": state.start_date.isoformat(timespec="seconds"),
                "endDate": state.end_date.isoformat(timespec="seconds"),
            }
        )
        parsed = urlparse(events_url)
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "origin": f"{parsed.scheme}://{parsed.netloc}",
            "referer": events_url,
            "requestverificationtoken": state.request_token,
            "x-requested-with": "XMLHttpRequest",
        }
        text = await self.post_form(api_url, body, headers=headers)
        try:
            payload = json.loads(text)
        except (TypeError, ValueError):
            Logger.warn(
                f"{self._log_prefix}: TNEW API returned non-JSON response from {api_url}",
                self.logger_context,
            )
            return []
        if not isinstance(payload, list):
            Logger.warn(
                f"{self._log_prefix}: TNEW API returned {type(payload).__name__}, expected list",
                self.logger_context,
            )
            return []
        return [item for item in payload if isinstance(item, dict)]
