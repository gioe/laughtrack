"""Generic Salesforce PatronTicket scraper.

Reads per-club config from ``scraping_sources``:

  source_url  → the venue's PatronTicket ticket page
                (e.g. ``https://reillyartscenter.my.salesforce-sites.com/ticket``).
                The apexremote endpoint is derived by appending ``/apexremote``.

  metadata.patronticket_venue_id
              → Salesforce venue ID (or list of IDs) whose instances should be
                returned. Required.

  metadata.patronticket_categories (optional)
              → CSV (or JSON list) of category tokens to keep. Defaults to
                ``"Comedy"``. Matching is token-exact against the venue's
                semicolon-separated ``category`` field (with surrounding
                whitespace stripped per token), so the default ``"Comedy"``
                filter matches ``"Comedy"`` and ``"Comedy;Stand-Up"`` but NOT
                ``"Tragicomedy"`` or ``"Comedy Music Festival"``. Pass an empty
                string or the literal ``"*"`` to disable category filtering for
                venues that tag comedy differently.

  metadata.patronticket_name_strip_suffixes (optional)
              → CSV (or JSON list) of trailing strings to strip from show names
                during Show conversion. Some venues append ``" - <City>"`` to
                upstream event names; this lets a single shared scraper preserve
                each venue's previous title cleanup behavior.
"""

import json
from typing import List, Optional, Sequence

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.shared.types import ScrapingTarget

from .data import PatronTicketPageData
from .extractor import PatronTicketExtractor
from .transformer import PatronTicketEventTransformer


_VENUE_ID_METADATA_KEY = "patronticket_venue_id"
_CATEGORY_METADATA_KEY = "patronticket_categories"
_NAME_STRIP_METADATA_KEY = "patronticket_name_strip_suffixes"
_DEFAULT_CATEGORIES: tuple = ("Comedy",)


def _coerce_string_list(value: object) -> List[str]:
    """Coerce a JSON metadata value into a list of non-empty strings.

    - Python list / tuple: preserve each entry verbatim (entries may contain
      leading/trailing whitespace, which is meaningful for some keys —
      ``patronticket_name_strip_suffixes`` entries like " - San Francisco"
      depend on that leading space to match the upstream event name).
    - JSON-array string: same as above (decode then preserve verbatim).
    - CSV string: split on ',' and strip per chunk, since the surrounding
      whitespace there is formatting around the delimiter, not data.
    - Anything else: best-effort single-element list, empty if blank.

    Only strictly-empty entries are filtered out in every branch.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item) != ""]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
            except ValueError:
                parsed = None
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item) != ""]
        return [chunk.strip() for chunk in stripped.split(",") if chunk.strip()]
    return [str(value)] if str(value) != "" else []


class PatronTicketScraper(BaseScraper):
    """Generic Salesforce PatronTicket scraper, configured per-club via scraping_sources."""

    key = "patron_ticket"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)

        source_url = (club.scraping_url or "").strip()
        if not source_url:
            raise ValueError(
                f"PatronTicketScraper: club id={club.id} name={club.name!r} has no "
                "source_url in scraping_sources — cannot build apexremote endpoint."
            )

        venue_ids = _coerce_string_list(
            club.source_metadata.get(_VENUE_ID_METADATA_KEY)
        )
        if not venue_ids:
            raise ValueError(
                f"PatronTicketScraper: club id={club.id} name={club.name!r} has no "
                f"metadata.{_VENUE_ID_METADATA_KEY} — every PatronTicket source must "
                "be scoped to one or more Salesforce venue IDs to avoid leaking "
                "events from sibling rooms hosted on the same org."
            )

        category_value = club.source_metadata.get(_CATEGORY_METADATA_KEY)
        if category_value in (None, ""):
            categories: Sequence[str] = _DEFAULT_CATEGORIES
        else:
            tokens = _coerce_string_list(category_value)
            # "*" is the explicit "no filter" sentinel.
            categories = tuple() if tokens == ["*"] else tuple(tokens)

        name_strip_suffixes = _coerce_string_list(
            club.source_metadata.get(_NAME_STRIP_METADATA_KEY)
        )

        self._source_url = source_url.rstrip("/")
        self._apexremote_url = f"{self._source_url}/apexremote"
        self._venue_ids: List[str] = venue_ids
        self._categories: Sequence[str] = categories
        self._name_strip_suffixes: List[str] = name_strip_suffixes

        self.transformation_pipeline.register_transformer(
            PatronTicketEventTransformer(club)
        )

    def collect_scraping_targets_sync(self) -> List[ScrapingTarget]:
        return [self._source_url]

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        return self.collect_scraping_targets_sync()

    def build_fetch_events_payload(self, auth_config: dict) -> dict:
        """Build the Visualforce Remoting payload for the fetchEvents call.

        Exposed for testing. The payload mirrors what the PatronTicket SPA sends
        from the browser; ``data`` carries the (origin URL, opaque, opaque)
        positional args the apex method expects.
        """
        return {
            "action": "PatronTicket.Controller_PublicTicketApp",
            "method": "fetchEvents",
            "data": [f"{self._source_url}/", "", ""],
            "type": "rpc",
            "tid": 5,
            "ctx": {
                "csrf": auth_config["csrf"],
                "vid": auth_config["vid"],
                "ns": auth_config["ns"],
                "ver": auth_config["ver"],
                "authorization": auth_config["authorization"],
            },
        }

    async def get_data(self, url: str) -> Optional[PatronTicketPageData]:
        """Fetch the PatronTicket page, extract auth config, and call fetchEvents."""
        try:
            page_html = await self.fetch_html(self._source_url)
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: failed to fetch PatronTicket page: {e}",
                self.logger_context,
            )
            return None

        if not page_html:
            Logger.warn(
                f"{self._log_prefix}: empty response from PatronTicket page",
                self.logger_context,
            )
            return None

        auth_config = PatronTicketExtractor.extract_auth_config(page_html)
        if not auth_config:
            Logger.warn(
                f"{self._log_prefix}: could not extract fetchEvents auth config from page",
                self.logger_context,
            )
            return None

        payload = self.build_fetch_events_payload(auth_config)

        try:
            api_response = await self.post_json(
                self._apexremote_url,
                payload,
                headers={"Referer": self._source_url},
            )
        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: fetchEvents API call failed: {e}",
                self.logger_context,
            )
            return None

        if not api_response:
            Logger.warn(
                f"{self._log_prefix}: empty response from fetchEvents API",
                self.logger_context,
            )
            return None

        events = PatronTicketExtractor.extract_events(
            api_response,
            venue_ids=self._venue_ids,
            categories=self._categories,
            name_strip_suffixes=self._name_strip_suffixes,
            logger_context=self.logger_context,
        )

        if not events:
            Logger.info(
                f"{self._log_prefix}: no upcoming events found",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {len(events)} upcoming events",
            self.logger_context,
        )
        return PatronTicketPageData(event_list=events)
