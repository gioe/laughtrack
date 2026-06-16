"""Google Places API (New) client — venue photo + nearby-discovery lookups.

Wraps two ``places:searchText`` use cases:

* ``fetch_photo`` — resolve a venue's first Google photo (plus its place_id
  and required author attributions) for club image sourcing.
* ``search_nearby`` — text-search biased toward a circle, used to discover
  comedy venues geographically (see ``bin/discover-nearby``).

Pricing: Text Search bills under the "Text Search" SKUs (~$32 per 1k requests
as of 2025); each request is drawn from ``GOOGLE_PLACES_DAILY_LIMIT``.

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from laughtrack.foundation.infrastructure.logger.logger import Logger

_API_BASE = "https://places.googleapis.com/v1"
_API_URL = f"{_API_BASE}/places:searchText"

# Photo search only needs the place identity plus its photo references; the
# image bytes are fetched in a follow-up media call keyed off photos[*].name.
_PHOTO_FIELD_MASK = "places.id,places.displayName,places.photos"

# Place Details lookup for timezone/location backfill — the formatted address,
# coordinates, and structured address components (used to pull the state code
# off administrative_area_level_1 and the city off locality).
_DETAILS_FIELD_MASK = "formattedAddress,location,addressComponents"

# find_place_id only needs the top match's identifier.
_FIND_PLACE_FIELD_MASK = "places.id"

# Nearby/discovery search returns identity + location so callers can dedupe on
# place_id and filter by true distance. ``websiteUri`` and ``primaryType`` ride
# along in the same call (no extra billing) to power downstream triage — the
# website is the entry point for both comedy-likelihood scoring and later
# scraper onboarding. ``nextPageToken`` is top-level (not under ``places``) so
# it must be named explicitly in the mask to paginate.
_NEARBY_FIELD_MASK = (
    "nextPageToken,"
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.websiteUri,"
    "places.primaryType"
)

# Text Search ``locationBias`` circle radius is capped at 50 km by the API.
_MAX_BIAS_RADIUS_M = 50_000.0
_METERS_PER_MILE = 1609.344
# Text Search returns at most 20 results per page; pagination tops out at 60.
_NEARBY_PAGE_SIZE = 20


@dataclass
class PlacesPhotoResult:
    """Outcome of one ``fetch_photo`` call.

    ``photo_uri`` is the key-free, directly-downloadable image URL (the same
    value ``fetch_photo_url`` returns). ``place_id`` is the resolved Places
    identifier for the venue — callers persist it on ``clubs.google_place_id``
    so the venue can be re-queried without re-resolving. ``attributions`` is
    the list of author attributions Google requires to be displayed alongside
    the photo; each entry is a ``{"displayName", "uri", "photoUri"}`` dict of
    string values (empty list when the API provided none).
    """

    photo_uri: str
    place_id: Optional[str]
    attributions: List[Dict[str, str]]


@dataclass
class PlacesNearbyVenue:
    """One venue returned by :meth:`GooglePlacesClient.search_nearby`.

    ``lat``/``lng`` are the venue's own coordinates (not the search center),
    so callers can compute the true great-circle distance from an origin and
    discard results the soft ``locationBias`` pulled in from beyond the ring.
    ``address`` is Google's ``formattedAddress`` (``None`` when absent).
    ``website`` is Google's ``websiteUri`` and ``primary_type`` its
    ``primaryType`` (both ``None`` when absent) — triage signals for whether a
    hit is a real comedy venue and where its calendar lives.
    """

    place_id: str
    name: str
    address: Optional[str]
    lat: float
    lng: float
    website: Optional[str] = None
    primary_type: Optional[str] = None


@dataclass
class PlaceDetails:
    """Structured fields from one ``fetch_place_details`` (Place Details) call.

    Used by the club timezone backfill to resolve a venue's IANA timezone from
    its US state and to opportunistically fill ``clubs.state/address/lat/lng``.
    ``state_code`` is the two-letter ``shortText`` of the
    ``administrative_area_level_1`` address component; ``city`` is the
    ``locality`` component (``shortText``/``longText``). All non-id fields are
    optional — Google may omit any of them.
    """

    place_id: str
    formatted_address: Optional[str]
    state_code: Optional[str]
    city: Optional[str]
    lat: Optional[float]
    lng: Optional[float]


def _normalize_attributions(raw: Any) -> List[Dict[str, str]]:
    """Reduce Places ``authorAttributions`` to JSON-serializable string triples.

    Keeps only ``displayName`` / ``uri`` / ``photoUri`` entries whose values are
    non-empty strings, dropping anything else, so the result can be stored
    directly in the ``clubs.google_place_attribution`` JSONB column. Non-list
    input (or a missing field) yields ``[]``.
    """
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entry = {
            key: item[key]
            for key in ("displayName", "uri", "photoUri")
            if isinstance(item.get(key), str) and item.get(key)
        }
        if entry:
            out.append(entry)
    return out


class GooglePlacesClient:
    """Client for Google Places API (New) text-search + hours lookup."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
        self._calls_made = 0
        # Guards _calls_made under concurrent ``asyncio.to_thread`` workers —
        # the enrichment script dispatches up to 8 in parallel, and a
        # naive ``+= 1`` would race past the daily cap by a handful of calls.
        self._counter_lock = threading.Lock()
        try:
            self._daily_limit = int(os.environ.get("GOOGLE_PLACES_DAILY_LIMIT", "500"))
        except ValueError:
            self._daily_limit = 500
        try:
            self._delay_s = float(os.environ.get("GOOGLE_PLACES_DELAY_S", "0.15"))
        except ValueError:
            self._delay_s = 0.15
        try:
            self._timeout_s = float(os.environ.get("GOOGLE_PLACES_TIMEOUT_S", "10"))
        except ValueError:
            self._timeout_s = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def calls_made(self) -> int:
        return self._calls_made

    @property
    def calls_remaining(self) -> int:
        return max(0, self._daily_limit - self._calls_made)

    def _reserve_call_slot(self) -> bool:
        """Atomically check the cap and reserve a slot if room remains.

        Returning ``True`` commits the slot — the caller MUST proceed to
        make the HTTP request, since the increment is already accounted
        for.  Returning ``False`` means the cap was hit; do not call the
        API.  Holding the lock around both check and increment is what
        makes the cap a hard ceiling under concurrent workers.
        """
        with self._counter_lock:
            if self._calls_made >= self._daily_limit:
                return False
            self._calls_made += 1
            return True

    def _release_call_slot(self) -> None:
        """Roll back a reserved slot when the request never reached the API."""
        with self._counter_lock:
            if self._calls_made > 0:
                self._calls_made -= 1

    def search_nearby(
        self,
        query: str,
        lat: float,
        lng: float,
        radius_miles: float,
        max_pages: int = 3,
    ) -> List[PlacesNearbyVenue]:
        """Text-search ``query`` biased toward a circle and return venues.

        Runs ``places:searchText`` with a ``locationBias`` circle centered on
        (``lat``, ``lng``). The bias radius is clamped to the API's 50 km
        ceiling; a wider ``radius_miles`` should be covered by tiling multiple
        calls and deduping on ``place_id``. Note the bias is *soft* — Google
        may return venues outside the circle — so callers MUST filter results
        by true distance from their origin.

        Paginates up to ``max_pages`` pages (20 results each, 60 max) via
        ``nextPageToken``. Each HTTP request consumes one daily-quota slot.
        Returns the accumulated venues (de-duplicated on ``place_id`` within
        this call); an empty list on missing key, blank query, quota breach,
        or any HTTP/parse error.
        """
        if not self.is_configured or not query or not query.strip():
            return []

        radius_m = min(max(radius_miles, 0.0) * _METERS_PER_MILE, _MAX_BIAS_RADIUS_M)
        if radius_m <= 0:
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _NEARBY_FIELD_MASK,
        }
        base_payload: Dict[str, Any] = {
            "textQuery": query,
            "pageSize": _NEARBY_PAGE_SIZE,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_m,
                }
            },
        }

        out: List[PlacesNearbyVenue] = []
        seen: set = set()
        page_token: Optional[str] = None
        for _ in range(max(1, max_pages)):
            payload = dict(base_payload)
            if page_token:
                payload["pageToken"] = page_token

            page = self._fetch_nearby_page(payload, headers, query)
            if page is None:
                break
            venues, page_token = page

            for venue in venues:
                if venue.place_id not in seen:
                    seen.add(venue.place_id)
                    out.append(venue)

            if not page_token:
                break

        return out

    def _fetch_nearby_page(
        self, payload: Dict[str, Any], headers: Dict[str, str], query: str
    ) -> Optional[tuple[List[PlacesNearbyVenue], Optional[str]]]:
        """Fetch and parse one nearby-search page.

        Returns ``(venues, next_page_token)`` on success (token is ``None``
        when there are no more pages), or ``None`` to signal pagination should
        stop — quota breach, network error, non-200, or unparseable JSON. Each
        successful reservation consumes one daily-quota slot; a slot reserved
        for a request that never reached the API is refunded.
        """
        if not self._reserve_call_slot():
            Logger.warn(
                f"[places] daily limit reached ({self._daily_limit}) — " f"stopping nearby search for '{query}'"
            )
            return None

        if self._delay_s > 0:
            time.sleep(self._delay_s)

        try:
            resp = requests.post(_API_URL, json=payload, headers=headers, timeout=self._timeout_s)
        except requests.RequestException as exc:
            self._release_call_slot()
            Logger.warn(f"[places] nearby search failed for '{query}': {exc}")
            return None

        if resp.status_code == 429:
            Logger.warn(f"[places] rate limited (HTTP 429) on nearby '{query}'")
            return None
        if resp.status_code != 200:
            Logger.warn(f"[places] HTTP {resp.status_code} on nearby '{query}': {resp.text[:200]}")
            return None

        try:
            data = resp.json()
        except ValueError as exc:
            Logger.warn(f"[places] bad JSON on nearby '{query}': {exc}")
            return None

        token = data.get("nextPageToken") if isinstance(data, dict) else None
        next_token = token if isinstance(token, str) and token else None
        return self._parse_nearby_places(data), next_token

    @staticmethod
    def _parse_nearby_places(data: Any) -> List[PlacesNearbyVenue]:
        """Pull well-formed venues from one nearby-search response page.

        Skips any entry missing a string ``id`` or numeric lat/lng — those
        can't be deduped or distance-filtered, so they're dropped rather than
        carried forward with placeholder coordinates.
        """
        places = data.get("places") if isinstance(data, dict) else None
        if not isinstance(places, list):
            return []
        out: List[PlacesNearbyVenue] = []
        for place in places:
            if not isinstance(place, dict):
                continue
            place_id = place.get("id")
            if not isinstance(place_id, str) or not place_id:
                continue
            location = place.get("location")
            if not isinstance(location, dict):
                continue
            lat = location.get("latitude")
            lng = location.get("longitude")
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                continue
            display = place.get("displayName")
            name = ""
            if isinstance(display, dict) and isinstance(display.get("text"), str):
                name = display["text"]
            address = place.get("formattedAddress")
            website = place.get("websiteUri")
            primary_type = place.get("primaryType")
            out.append(
                PlacesNearbyVenue(
                    place_id=place_id,
                    name=name,
                    address=address if isinstance(address, str) else None,
                    lat=float(lat),
                    lng=float(lng),
                    website=website if isinstance(website, str) and website else None,
                    primary_type=(primary_type if isinstance(primary_type, str) and primary_type else None),
                )
            )
        return out

    def fetch_photo(self, query: str, max_width_px: int = 500) -> Optional[PlacesPhotoResult]:
        """Resolve a venue photo for ``query`` plus its place_id and attribution.

        Two requests under the daily cap: a ``places:searchText`` to find the
        top match's place_id, first photo reference, and required author
        attributions, then a photo ``media`` call with ``skipHttpRedirect=true``
        so Google returns a JSON ``photoUri`` (a short-lived, key-free
        ``lh3.googleusercontent.com`` URL) instead of the raw bytes. The
        key-free ``photoUri`` keeps the API key out of the caller's download
        path and logs; ``place_id`` and ``attributions`` are returned so callers
        can persist them (``clubs.google_place_id`` /
        ``clubs.google_place_attribution``).

        Returns ``None`` on missing key, blank query, quota breach, any HTTP
        or network error, no match, or a match with no photos.
        """
        if not self.is_configured:
            return None
        if not query or not query.strip():
            return None
        if not self._reserve_call_slot():
            Logger.warn(f"[places] daily limit reached ({self._daily_limit}) — skipping photo query '{query}'")
            return None

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _PHOTO_FIELD_MASK,
        }
        payload: Dict[str, Any] = {"textQuery": query, "pageSize": 1}

        if self._delay_s > 0:
            time.sleep(self._delay_s)

        try:
            resp = requests.post(_API_URL, json=payload, headers=headers, timeout=self._timeout_s)
        except requests.RequestException as exc:
            self._release_call_slot()
            Logger.warn(f"[places] photo search failed for '{query}': {exc}")
            return None

        if resp.status_code == 429:
            Logger.warn(f"[places] rate limited (HTTP 429) on photo query '{query}'")
            return None
        if resp.status_code != 200:
            Logger.warn(f"[places] HTTP {resp.status_code} on photo query '{query}': {resp.text[:200]}")
            return None

        try:
            data = resp.json()
        except ValueError as exc:
            Logger.warn(f"[places] bad JSON on photo query '{query}': {exc}")
            return None

        place_id, photo_name, attributions = self._extract_photo_fields(data)
        if not photo_name:
            return None

        photo_uri = self._resolve_photo_uri(photo_name, max_width_px, query)
        if not photo_uri:
            return None
        return PlacesPhotoResult(photo_uri=photo_uri, place_id=place_id, attributions=attributions)

    def fetch_photo_url(self, query: str, max_width_px: int = 500) -> Optional[str]:
        """Resolve a venue photo for ``query`` to a directly-downloadable URL.

        Thin wrapper over :meth:`fetch_photo` that returns only the key-free
        ``photoUri``. Prefer :meth:`fetch_photo` when the resolved ``place_id``
        or the photo's required attribution must be persisted.
        """
        result = self.fetch_photo(query, max_width_px)
        return result.photo_uri if result else None

    def find_place_id(self, query: str) -> Optional[str]:
        """Resolve the top text-search match for ``query`` to its place_id.

        One ``places:searchText`` request under the daily cap (field mask
        ``places.id``, ``pageSize=1``). Returns the top result's ``id``, or
        ``None`` on missing key, blank query, quota breach, any HTTP/network
        error, unparseable JSON, or no match. Mirrors ``fetch_photo``'s search
        half so callers can resolve a place_id before ``fetch_place_details``.
        """
        if not self.is_configured:
            return None
        if not query or not query.strip():
            return None
        if not self._reserve_call_slot():
            Logger.warn(f"[places] daily limit reached ({self._daily_limit}) — skipping find_place_id '{query}'")
            return None

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIND_PLACE_FIELD_MASK,
        }
        payload: Dict[str, Any] = {"textQuery": query, "pageSize": 1}

        if self._delay_s > 0:
            time.sleep(self._delay_s)

        try:
            resp = requests.post(_API_URL, json=payload, headers=headers, timeout=self._timeout_s)
        except requests.RequestException as exc:
            self._release_call_slot()
            Logger.warn(f"[places] find_place_id search failed for '{query}': {exc}")
            return None

        if resp.status_code == 429:
            Logger.warn(f"[places] rate limited (HTTP 429) on find_place_id '{query}'")
            return None
        if resp.status_code != 200:
            Logger.warn(f"[places] HTTP {resp.status_code} on find_place_id '{query}': {resp.text[:200]}")
            return None

        try:
            data = resp.json()
        except ValueError as exc:
            Logger.warn(f"[places] bad JSON on find_place_id '{query}': {exc}")
            return None

        places = data.get("places") if isinstance(data, dict) else None
        if not isinstance(places, list) or not places:
            return None
        top = places[0]
        if not isinstance(top, dict):
            return None
        place_id = top.get("id")
        return place_id if isinstance(place_id, str) and place_id else None

    def fetch_place_details(self, place_id: str) -> Optional[PlaceDetails]:
        """Fetch structured address + location for a known ``place_id``.

        One Place Details ``GET /places/{place_id}`` request under the daily
        cap (field mask ``formattedAddress,location,addressComponents``).
        Parses the ``administrative_area_level_1`` component's ``shortText``
        into ``state_code`` and the ``locality`` component into ``city``, plus
        the location's lat/lng. Returns ``None`` on missing key, blank
        place_id, quota breach, any HTTP/network error, or unparseable JSON.
        """
        if not self.is_configured:
            return None
        if not place_id or not place_id.strip():
            return None
        if not self._reserve_call_slot():
            Logger.warn(
                f"[places] daily limit reached ({self._daily_limit}) — skipping place details for '{place_id}'"
            )
            return None

        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _DETAILS_FIELD_MASK,
        }

        if self._delay_s > 0:
            time.sleep(self._delay_s)

        try:
            resp = requests.get(f"{_API_BASE}/places/{place_id}", headers=headers, timeout=self._timeout_s)
        except requests.RequestException as exc:
            self._release_call_slot()
            Logger.warn(f"[places] place details fetch failed for '{place_id}': {exc}")
            return None

        if resp.status_code == 429:
            Logger.warn(f"[places] rate limited (HTTP 429) on place details '{place_id}'")
            return None
        if resp.status_code != 200:
            Logger.warn(f"[places] HTTP {resp.status_code} on place details '{place_id}': {resp.text[:200]}")
            return None

        try:
            data = resp.json()
        except ValueError as exc:
            Logger.warn(f"[places] bad JSON on place details '{place_id}': {exc}")
            return None

        return self._parse_place_details(place_id, data)

    @staticmethod
    def _parse_place_details(place_id: str, data: Any) -> PlaceDetails:
        """Pull state/city/lat/lng/address out of a Place Details payload."""
        if not isinstance(data, dict):
            return PlaceDetails(place_id, None, None, None, None, None)

        formatted = data.get("formattedAddress")
        formatted_address = formatted if isinstance(formatted, str) and formatted else None

        state_code: Optional[str] = None
        city: Optional[str] = None
        components = data.get("addressComponents")
        if isinstance(components, list):
            for comp in components:
                if not isinstance(comp, dict):
                    continue
                types = comp.get("types")
                if not isinstance(types, list):
                    continue
                if "administrative_area_level_1" in types and state_code is None:
                    short = comp.get("shortText")
                    if isinstance(short, str) and short:
                        state_code = short
                if "locality" in types and city is None:
                    name = comp.get("shortText") or comp.get("longText")
                    if isinstance(name, str) and name:
                        city = name

        lat: Optional[float] = None
        lng: Optional[float] = None
        location = data.get("location")
        if isinstance(location, dict):
            raw_lat = location.get("latitude")
            raw_lng = location.get("longitude")
            if isinstance(raw_lat, (int, float)):
                lat = float(raw_lat)
            if isinstance(raw_lng, (int, float)):
                lng = float(raw_lng)

        return PlaceDetails(
            place_id=place_id,
            formatted_address=formatted_address,
            state_code=state_code,
            city=city,
            lat=lat,
            lng=lng,
        )

    @staticmethod
    def _extract_photo_fields(
        data: Any,
    ) -> tuple[Optional[str], Optional[str], List[Dict[str, str]]]:
        """Pull (place_id, first photo name, author attributions) from a search.

        ``place_id`` may be present even when the match carries no photos (then
        ``photo_name`` is ``None``). Attributions are normalized to
        JSON-serializable string triples and default to ``[]``.
        """
        places = data.get("places") if isinstance(data, dict) else None
        if not isinstance(places, list) or not places:
            return None, None, []
        top = places[0]
        if not isinstance(top, dict):
            return None, None, []
        place_id = top.get("id") if isinstance(top.get("id"), str) else None
        photos = top.get("photos")
        if not isinstance(photos, list) or not photos:
            return place_id, None, []
        first = photos[0]
        if not isinstance(first, dict):
            return place_id, None, []
        name = first.get("name")
        photo_name = name if isinstance(name, str) and name else None
        attributions = _normalize_attributions(first.get("authorAttributions"))
        return place_id, photo_name, attributions

    def _resolve_photo_uri(self, photo_name: str, max_width_px: int, query: str) -> Optional[str]:
        """Resolve a ``photos/*`` reference to its key-free ``photoUri``."""
        if not self._reserve_call_slot():
            Logger.warn(
                f"[places] daily limit reached ({self._daily_limit}) — " f"skipping photo media fetch for '{query}'"
            )
            return None

        media_url = f"{_API_BASE}/{photo_name}/media"
        if self._delay_s > 0:
            time.sleep(self._delay_s)

        try:
            resp = requests.get(
                media_url,
                params={"maxWidthPx": max_width_px, "skipHttpRedirect": "true"},
                headers={"X-Goog-Api-Key": self._api_key},
                timeout=self._timeout_s,
            )
        except requests.RequestException as exc:
            self._release_call_slot()
            Logger.warn(f"[places] photo media fetch failed for '{query}': {exc}")
            return None

        if resp.status_code != 200:
            Logger.warn(f"[places] HTTP {resp.status_code} on photo media for '{query}': {resp.text[:200]}")
            return None

        try:
            media = resp.json()
        except ValueError as exc:
            Logger.warn(f"[places] bad JSON on photo media for '{query}': {exc}")
            return None

        uri = media.get("photoUri") if isinstance(media, dict) else None
        return uri if isinstance(uri, str) and uri else None
