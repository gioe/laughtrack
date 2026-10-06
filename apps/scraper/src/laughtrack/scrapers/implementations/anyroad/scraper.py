"""AnyRoad platform scraper.

AnyRoad (app.anyroad.com) is a reusable experiences-booking platform. A venue
embeds a widget keyed by a ``plugin_id``; the widget pulls its calendar from
``/plugins/api/v3/experiences?plugin_id=<id>&page=N``. That endpoint is
Cloudflare-gated to plain HTTP but is cleared by curl_cffi's Chrome
impersonation (the default ``fetch_json`` session), with the shared Playwright
browser as the automatic fallback.

The list endpoint's inline ``schedule`` carries only a placeholder slot time, so
for each experience the scraper also fetches its booking detail page
(``attributes.url``) and parses the embedded ``tour_availability.dates`` blob —
the real per-occurrence times and the full availability calendar. Detail fetches
fall back per-experience to the placeholder ``schedule`` for legacy sources.
Reviewed ``metadata.anyroad_venue_routes`` sources instead hold unavailable or
conflicting detail calendars and mark reconciliation incomplete. Routes pin
source/plugin/producer IDs, exact normalized location strings, and physical club
name/address/city/state/postal code/timezone. Blank locations retain home
assignment with uncertainty; explicit unknown locations never default home.

Wiring (``scraping_sources``): set ``scraper_key='anyroad'`` and put the plugin
id in ``metadata.plugin_id`` (the canonical wire — the ``scraping_sources``
schema has no ``external_id`` column, so ``ScrapingSource.from_dict`` never
populates it for ``platform='custom'``). ``source_url`` may hold the
human-facing widget URL (``https://app.anyroad.com/i/plugin/<id>``), from which
the plugin id is parsed as a fallback.
"""

from __future__ import annotations

import asyncio

from typing import List, Optional
from urllib.parse import urlparse

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.club.handler import ClubHandler
from .routing import AnyRoadVenueRouter
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.anyroad.data import AnyRoadPageData
from laughtrack.scrapers.implementations.anyroad.extractor import (
    extract_anyroad_events,
    extract_tour_availability,
    validate_tour_availability,
)
from laughtrack.scrapers.implementations.anyroad.transformer import AnyRoadTransformer
from laughtrack.scrapers.utils.comedy_filter import is_comedy_filter_enabled
from laughtrack.shared.types import ScrapingTarget

_EXPERIENCES_API = "https://app.anyroad.com/plugins/api/v3/experiences"

# Defensive upper bound on pagination so a misbehaving API (e.g. one that never
# returns an empty page) cannot spin forever. Rozzie's full calendar is 3 pages.
_MAX_PAGES = 50


class AnyRoadScraper(BaseScraper):
    """Scraper for venues hosted on app.anyroad.com (experiences widget)."""

    key = "anyroad"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.venue_router = AnyRoadVenueRouter(club)
        self.transformation_pipeline.register_transformer(AnyRoadTransformer(club, self.venue_router))

    def _resolve_plugin_id(self) -> Optional[str]:
        """Resolve the AnyRoad plugin id from scraping-source config.

        Order: ``metadata.plugin_id`` (the canonical wire) -> ``external_id``
        (defensive/forward-compat — not populated by the current
        ``scraping_sources`` schema) -> last path segment of ``source_url``
        (handles ``/i/plugin/<id>`` and ``integrations.../<id>``).
        """
        source = self.club.scraping_source
        if source is not None:
            meta_id = source.metadata.get("plugin_id") if source.metadata else None
            if meta_id:
                return str(meta_id).strip()
            if source.external_id:
                return source.external_id.strip()

        url = self.club.scraping_url
        if url:
            path = urlparse(url if "://" in url else f"https://{url}").path
            segments = [seg for seg in path.split("/") if seg]
            if segments:
                # ".../i/plugin/<id>" or ".../i/plugin/<id>/tours" -> take the
                # segment after "plugin"; otherwise the final path segment.
                if "plugin" in segments:
                    idx = segments.index("plugin")
                    if idx + 1 < len(segments):
                        return segments[idx + 1]
                return segments[-1]
        return None

    @staticmethod
    def _experiences_url(plugin_id: str, page: int) -> str:
        return f"{_EXPERIENCES_API}?plugin_id={plugin_id}&page={page}"

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        plugin_id = self._resolve_plugin_id()
        if not plugin_id:
            Logger.warn(
                f"{self._log_prefix}: no AnyRoad plugin id configured " f"(set scraping_sources.metadata.plugin_id)",
                self.logger_context,
            )
            return []
        # Identifier-based target (like Comedy Cellar's date strings): get_data
        # turns the plugin id into the paginated API calls.
        return [plugin_id]

    async def get_data(self, target: ScrapingTarget) -> Optional[AnyRoadPageData]:
        plugin_id = str(target)
        try:
            if self.venue_router.enabled:
                ids = self.venue_router.destination_ids()
                destinations = await asyncio.to_thread(ClubHandler().get_physical_clubs_by_ids, ids)
                self.venue_router.destinations = {club.id: club for club in destinations}
                if set(ids) != set(self.venue_router.destinations):
                    raise ValueError("reviewed physical destinations missing")
            records = await self._fetch_all_experiences(plugin_id)
            if not records:
                self._warn_empty_extraction(
                    self._experiences_url(plugin_id, 1),
                    subject="experiences",
                    n_items=0,
                )
                return None

            availability_by_id = await self._fetch_availability_by_id(records)
            events = []
            for record in records:
                event_timezone = self.club.timezone
                if self.venue_router.enabled:
                    try:
                        attrs = record["attributes"]
                        exp_id = str(self._record_id(record) or "")
                        if attrs.get("id") is not None and str(attrs["id"]) != exp_id:
                            raise ValueError("conflicting experience IDs")
                        self.venue_router.validate_identity(exp_id, attrs.get("url", ""))
                        event_timezone = self.venue_router.destination(attrs.get("locationInfo", "")).timezone
                        if exp_id not in availability_by_id:
                            raise ValueError("detail calendar unavailable; placeholder times held")
                    except (ValueError, TypeError, KeyError, AttributeError) as exc:
                        self.venue_router.hold(str(exc))
                        continue
                events.extend(
                    extract_anyroad_events(
                        [record],
                        timezone=event_timezone,
                        comedy_filter=is_comedy_filter_enabled(self.club.source_metadata),
                        availability_by_id=availability_by_id,
                    )
                )
            if not events:
                self._warn_empty_extraction(
                    self._experiences_url(plugin_id, 1),
                    subject="events",
                    n_items=len(records),
                )
                return None
            return AnyRoadPageData(events)
        except Exception as e:
            if self.venue_router.enabled:
                self.venue_router.hold("experience fetch or routing preparation failed")
            Logger.error(
                f"{self._log_prefix}: Error fetching AnyRoad experiences for " f"plugin '{plugin_id}': {e}",
                self.logger_context,
            )
            return None

    async def _fetch_all_experiences(self, plugin_id: str) -> List[dict]:
        """Walk pages until an empty ``experiences.data`` array (no links/meta).

        Stops early if a page returns only experience ids already seen — guards
        against an API that ignores the ``page`` param and re-serves page 1, which
        would otherwise append duplicates until ``_MAX_PAGES``. Warns (rather than
        truncating silently) if the cap is reached, so a venue larger than the
        bound surfaces in logs instead of looking like a complete scrape.
        """
        records: List[dict] = []
        seen_ids: set = set()
        conflicting_ids: set[str] = set()
        for page in range(1, _MAX_PAGES + 1):
            payload = await self.fetch_json(self._experiences_url(plugin_id, page))
            if self.venue_router.enabled and (
                not isinstance(payload, dict)
                or not isinstance(payload.get("experiences"), dict)
                or not isinstance(payload["experiences"].get("data"), list)
            ):
                self.venue_router.hold("malformed or unavailable experiences page")
            data = self._page_records(payload)
            if not data:
                return [r for r in records if str(self._record_id(r)) not in conflicting_ids]
            if self.venue_router.enabled:
                by_id = {str(self._record_id(record)): record for record in records}
                for record in data:
                    record_id = str(self._record_id(record) or "")
                    if not record_id or not isinstance(record, dict) or not isinstance(record.get("attributes"), dict):
                        self.venue_router.hold("malformed experience record")
                    elif record_id in by_id and by_id[record_id] != record:
                        self.venue_router.hold("conflicting duplicate experience ID")
                        conflicting_ids.add(record_id)
                    by_id[record_id] = record
            fresh = [r for r in data if self._record_id(r) not in seen_ids]
            if not fresh:
                if self.venue_router.enabled:
                    self.venue_router.hold("pagination repeated a page before exhaustion")
                # API re-served an already-seen page — stop rather than loop.
                return [r for r in records if str(self._record_id(r)) not in conflicting_ids]
            seen_ids.update(self._record_id(r) for r in fresh)
            records.extend(fresh)
        if self.venue_router.enabled:
            self.venue_router.hold("pagination reached the safety cap")
        Logger.warn(
            f"{self._log_prefix}: AnyRoad pagination hit the {_MAX_PAGES}-page cap "
            f"for plugin '{plugin_id}'; calendar may be truncated",
            self.logger_context,
        )
        return [r for r in records if str(self._record_id(r)) not in conflicting_ids]

    async def _fetch_availability_by_id(self, records: List[dict]) -> dict:
        """Fetch each experience's booking detail page and parse real times.

        Returns ``{experience_id: dates_map}`` from the embedded
        ``tour_availability.dates`` blob. A per-experience fetch/parse failure is
        logged and skipped (no entry) so the extractor falls back to that
        experience's placeholder ``schedule`` in legacy mode. Reviewed routing
        holds that experience instead; unknown times must not replace real slots.
        """
        availability: dict = {}
        fallback_action = "holding experience" if self.venue_router.enabled else "using placeholder schedule"
        for record in records:
            attrs = record.get("attributes") if isinstance(record, dict) else None
            if not isinstance(attrs, dict):
                continue
            exp_id = self._record_id(record)
            url = attrs.get("url")
            if not exp_id or not url:
                continue
            try:
                if self.venue_router.enabled:
                    if attrs.get("id") is not None and str(attrs["id"]) != str(exp_id):
                        raise ValueError("conflicting experience IDs")
                    self.venue_router.validate_identity(str(exp_id), str(url))
                html = await self.fetch_html(str(url))
                if self.venue_router.enabled:
                    self.venue_router.validate_detail(html, exp_id, attrs.get("locationInfo", ""))
            except Exception as e:
                if self.venue_router.enabled:
                    self.venue_router.hold(f"experience {exp_id}: detail unavailable or identity conflict")
                Logger.warn(
                    f"{self._log_prefix}: AnyRoad detail fetch failed for "
                    f"experience {exp_id} ({url}): {e}; {fallback_action}",
                    self.logger_context,
                )
                continue
            dates = extract_tour_availability(html)
            if dates is not None:
                if self.venue_router.enabled:
                    try:
                        validate_tour_availability(dates)
                    except (ValueError, TypeError) as exc:
                        self.venue_router.hold(f"experience {exp_id}: {exc}; holding experience")
                        continue
                availability[str(exp_id)] = dates
            else:
                Logger.warn(
                    f"{self._log_prefix}: no tour_availability parsed from "
                    f"AnyRoad detail page for experience {exp_id} ({url}); "
                    f"{fallback_action}",
                    self.logger_context,
                )
        return availability

    def scrape_with_result(self):
        self.venue_router.errors.clear()
        result = super().scrape_with_result()
        if self.venue_router.enabled:
            try:
                result.production_company_id = self.venue_router.configuration()["producer_id"]
                result.is_synthetic = True
            except (ValueError, TypeError, KeyError) as exc:
                self.venue_router.hold(str(exc))
            if self.venue_router.errors:
                message = f"AnyRoad routing incomplete: {len(self.venue_router.errors)} held/error items"
                result.error = f"{result.error}; {message}" if result.error else message
        return result

    @staticmethod
    def _record_id(record: dict):
        """Stable per-experience id for de-duplicating re-served pages."""
        if isinstance(record, dict):
            attrs = record.get("attributes")
            return record.get("id") or (attrs.get("id") if isinstance(attrs, dict) else None)
        return None

    @staticmethod
    def _page_records(payload) -> List[dict]:
        if not isinstance(payload, dict):
            return []
        experiences = payload.get("experiences")
        if not isinstance(experiences, dict):
            return []
        data = experiences.get("data")
        return data if isinstance(data, list) else []
