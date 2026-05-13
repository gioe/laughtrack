"""Club database handler for club-specific operations."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sql.club_queries import ClubQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Club


def _normalize_venue_text_for_match(value: str) -> str:
    """Normalize one venue/location text fragment for exact match comparisons."""
    s = (value or "").lower().replace("&", " and ")
    for abbreviation, expanded in (
        ("ft", "fort"),
        ("st", "saint"),
        ("mt", "mount"),
    ):
        s = re.sub(rf"\b{abbreviation}\.?(?=\W|$)", expanded, s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _normalize_venue_name_for_match(name: str, city: str = "", state: str = "") -> str:
    """Reduce a venue name to a comparable core form for same-(city, state) merge detection.

    The transformation chain is intentionally deterministic — no edit-distance, no
    token-set ratio, no learned thresholds. Two names match iff their normalized
    forms are byte-equal. This is the conservative knob: typos or genuinely
    different brands ('Big Couch' vs 'Bog Couch') stay distinct because no fuzzy
    distance metric is applied.

    The chain captures the dominant Eventbrite organizer-side pattern observed in
    the TASK-1916 audit: one physical venue spelled both as 'Brand' and 'Brand
    <City>' (TASK-1919: 'Big Couch' / 'Big Couch New Orleans'). It does not
    attempt to fold every conceivable variation — middle-of-string city tokens
    and uncommon abbreviations like 'NYC' for 'New York' are out of scope and
    get a separate clubs row, which is acceptable per the per-incident
    manual-merge precedent (TASK-1925).

    Steps:
      1. Lowercase, expand common venue abbreviations ('Ft.'/'St.'/'Mt.'),
         expand '&' to 'and', then collapse all non-alphanumeric runs to single
         spaces. This normalizes punctuation, em-dashes, and unicode whitespace.
      2. Strip leading 'the ' (so 'The Comedy Cellar' folds to 'comedy cellar').
      3. Strip a trailing ' <city>', ' <state>', or ' <city> <state>' suffix —
         longest match first so 'big couch new orleans la' strips before
         'big couch new orleans'. Only the END of the string is considered;
         middle/prefix occurrences are preserved (a venue genuinely named
         'New Orleans Comedy Club' must NOT collapse to 'comedy club').
      4. Refuse to reduce the name to an empty string — if stripping the suffix
         would consume the entire name (e.g. a venue literally named after its
         city), keep the pre-strip form.
    """
    s = _normalize_venue_text_for_match(name)
    if s.startswith("the "):
        s = s[4:]

    norm_city = _normalize_venue_text_for_match(city or "")
    norm_state = _normalize_venue_text_for_match(state or "")

    suffix_candidates = []
    if norm_city and norm_state:
        suffix_candidates.append(f"{norm_city} {norm_state}")
    if norm_city:
        suffix_candidates.append(norm_city)
    if norm_state:
        suffix_candidates.append(norm_state)
    suffix_candidates.sort(key=len, reverse=True)

    for suffix in suffix_candidates:
        if s == suffix:
            # Stripping would empty the name — keep the original.
            break
        if s.endswith(" " + suffix):
            s = s[: -(len(suffix) + 1)].strip()
            break  # one strip per call; nested suffix structure is handled by ordering

    return s


def _string_list(values: Any) -> list[str]:
    if isinstance(values, str):
        raw_values = [values]
    elif isinstance(values, list):
        raw_values = values
    else:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped and stripped not in seen:
            result.append(stripped)
            seen.add(stripped)
    return result


def _comedian_refs(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []

    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        uuid = str(value.get("uuid") or "").strip()
        name = str(value.get("name") or "").strip()
        if not uuid and not name:
            continue
        key = (uuid, name)
        if key in seen:
            continue
        ref: dict[str, str] = {}
        if uuid:
            ref["uuid"] = uuid
        if name:
            ref["name"] = name
        refs.append(ref)
        seen.add(key)
    return refs


def _build_tour_date_discovery_metadata(venue: dict) -> str:
    raw = venue.get("discovery_metadata") or {}
    if not isinstance(raw, dict):
        raw = {}

    now = datetime.now(tz=timezone.utc).isoformat()
    metadata: dict[str, Any] = {
        "source": (raw.get("source") or "tour_dates"),
        "first_seen_at": now,
        "last_seen_at": now,
        "reference_count": 1,
    }

    for key in ("sample_urls", "event_urls", "platform_hints"):
        values = _string_list(raw.get(key))
        if values:
            metadata[key] = values

    refs = _comedian_refs(raw.get("comedian_refs"))
    if refs:
        metadata["comedian_refs"] = refs

    return json.dumps(metadata, sort_keys=True)


class ClubHandler(BaseDatabaseHandler[Club]):
    """Handler for club database operations."""

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "club"

    def get_entity_class(self) -> type[Club]:
        """Return the Club class for instantiation."""
        return Club

    def get_all_clubs(self) -> List[Club]:
        """
        Fetch all clubs with non-null scrapers from database.

        Returns:
            List[Club]: List of all active clubs
        """
        try:
            results = self.execute_with_cursor(ClubQueries.GET_ALL_CLUBS, return_results=True)
            if not results:
                raise ValueError("No clubs found in database")

            Logger.info(f"Retrieved {len(results)} clubs from database")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs: {str(e)}")
            raise

    def get_all_clubs_json(self) -> List[Dict[str, Optional[str]]]:
        """Fetch all clubs (including those without scrapers) with name, city, state, website."""
        results = self.execute_with_cursor(ClubQueries.GET_ALL_CLUBS_JSON, return_results=True)
        if not results:
            return []
        return [{"name": r["name"], "city": r["city"], "state": r["state"], "website": r["website"]} for r in results]

    def get_clubs_by_ids(self, club_ids: List[int]) -> List[Club]:
        """
        Fetch clubs by their IDs.

        Args:
            club_ids: List of club IDs to retrieve, or a single ID in a list

        Returns:
            List[Club]: List of clubs matching the provided IDs
        """
        if not club_ids:
            Logger.info("No club IDs provided")
            return []

        try:
            results = self.execute_with_cursor(ClubQueries.GET_CLUB_BY_IDS, (club_ids,), return_results=True)
            if not results:
                raise ValueError(f"No clubs found for IDs: {club_ids}")

            Logger.info(f"Retrieved {len(results)} clubs for {len(club_ids)} requested IDs")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs {club_ids}: {str(e)}")
            raise

    def get_club_by_id(self, club_id: int) -> Optional[Club]:
        """
        Fetch a single club by its ID.

        Args:
            club_id: The club ID to retrieve

        Returns:
            Club | None: The club if found, None otherwise
        """
        if not club_id:
            raise ValueError("No club ID provided")

        clubs = self.get_clubs_by_ids([club_id])
        return clubs[0] if clubs else None

    def get_specific_clubs(self, club_ids: List[int]) -> List[Club]:
        """
        Fetch specific clubs by their IDs.

        Deprecated: Use get_clubs_by_ids instead.

        Args:
            club_ids: List of club IDs to retrieve

        Returns:
            List[Club]: List of clubs matching the provided IDs
        """
        return self.get_clubs_by_ids(club_ids)

    def upsert_for_eventbrite_venue(self, venue) -> Optional[Club]:
        """
        Upsert a clubs row for an Eventbrite venue discovered via the national
        search API.  On conflict (name), preserves any existing eventbrite_id
        and scraper values rather than overwriting them.

        Fuzzy-name reconciliation (TASK-1926):
            Eventbrite organizer feeds emit multiple venue.id values for one
            physical venue, sometimes under inconsistent name spellings — TASK-1919
            saw 'Big Couch' (90 events) and 'Big Couch New Orleans' (44 events)
            sharing city='New Orleans', state='LA'. The SQL UPSERT below keys
            ON CONFLICT (name) only, so two name spellings produce two distinct
            clubs rows for the same venue.

            Before falling through to the SQL UPSERT, this method checks for an
            existing clubs row in the same (city, state) whose name normalizes
            (via _normalize_venue_name_for_match: lowercase, strip 'the ',
            strip trailing city/state token) to the same core form. Match is
            EXACT equality of normalized strings — no edit-distance threshold,
            no token-set ratio, no learned similarity score. The conservative
            knob is the matching algorithm, not a tunable threshold:
              - The (city, state) gate prevents cross-city brand collisions
                ('Laugh Factory' Hollywood will never match 'Laugh Factory'
                San Diego because their cities differ).
              - Exact-equality on the post-normalization form means typos and
                genuinely different brands stay distinct ('Big Couch' /
                'Bog Couch' or 'Big Couch' / 'Big Smile' won't merge).
              - Same-city distinct brands ('Comedy Cellar' / 'Comedy Cellar
                Village' both in NY, NY) stay distinct because their cores
                differ after the suffix-only city strip.
            Edge cases beyond the dominant 'Brand' / 'Brand <City>' pattern
            (mid-string city tokens and uncommon abbreviations) intentionally
            still produce two rows; they fall back to the per-incident manual-merge
            precedent (TASK-1925's fold script).

        Args:
            venue: EventbriteVenue from the API response

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        if not venue or not getattr(venue, "id", None) or not getattr(venue, "name", None):
            return None

        from laughtrack.utilities.domain.club.quality_filter import is_junk_venue  # noqa: PLC0415
        if is_junk_venue(venue.name):
            return None

        address = ""
        zip_code = ""
        city = None
        state = None
        if venue.address:
            parts = [
                p for p in [venue.address.address_1, venue.address.city, venue.address.region]
                if p
            ]
            address = ", ".join(parts)
            zip_code = venue.address.postal_code or ""
            city = venue.address.city or None
            state = venue.address.region or None

        fuzzy_match = self._find_fuzzy_match_in_location(venue.name, city, state)
        if fuzzy_match is not None:
            # Returning early skips the upserted_source CTE in
            # UPSERT_CLUB_BY_EVENTBRITE_VENUE, so the existing club's
            # scraping_sources rows are NOT touched: a disabled per-venue
            # source stays disabled (organizer-mode dispatch via /o/ keeps
            # routing the events anyway), and the new venue.id is not
            # registered against the existing scraping_sources.eventbrite_id.
            # Any consumer that relies on (eventbrite_id → club_id) reverse
            # lookup will see only the original venue.id; folding the
            # alternate ids requires an explicit alternate_eventbrite_id
            # column we do not have today.
            self._log_fuzzy_match_reuse("Eventbrite", venue.name, venue.id, city, state, fuzzy_match)
            return fuzzy_match

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE,
                (venue.name, address, zip_code, city, state, venue.id),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for Eventbrite venue {venue.id}: {e}")
            raise

    def _find_fuzzy_match_in_location(
        self, name: str, city: Optional[str], state: Optional[str]
    ) -> Optional[Club]:
        """Look for an existing clubs row in (city, state) whose name normalizes
        to the same core form as `name`.

        The (city, state) gate is mandatory — it is the structural guarantee that
        prevents cross-city brand-name false positives (e.g. 'Laugh Factory'
        Hollywood vs San Diego). Without both fields, this pre-check is skipped
        and the caller falls through to the regular ON CONFLICT (name) UPSERT.

        Returns None when no match is found, when (city, state) is incomplete,
        or when the location query fails — in every None case the caller falls
        through to the regular UPSERT path, so a fuzzy-match miss never blocks
        ingestion.
        """
        if not city or not state:
            return None

        norm_alias = _normalize_venue_text_for_match(name)
        norm_city = _normalize_venue_text_for_match(city)
        norm_state = _normalize_venue_text_for_match(state)
        norm_target = _normalize_venue_name_for_match(name, city, state)
        if not norm_alias or not norm_city or not norm_state or not norm_target:
            return None

        try:
            results = self.execute_with_cursor(
                ClubQueries.GET_CLUBS_BY_LOCATION,
                (city, state),
                return_results=True,
            ) or []
        except Exception as e:
            Logger.warn(
                f"fuzzy-match lookup failed for ({city}, {state}): {e} — "
                f"falling through to UPSERT"
            )
            return None

        for row in results:
            aliases = row.get("aliases") or []
            if isinstance(aliases, str):
                try:
                    aliases = json.loads(aliases)
                except json.JSONDecodeError:
                    aliases = []
            if not isinstance(aliases, list):
                continue
            for alias in aliases:
                if not isinstance(alias, dict):
                    continue
                if (
                    alias.get("normalized_alias_name") == norm_alias
                    and alias.get("normalized_city") == norm_city
                    and alias.get("normalized_state") == norm_state
                ):
                    alias_match = Club.from_db_row(row)
                    self._log_alias_match_reuse("Club alias", name, name, city, state, alias_match)
                    return alias_match

        if any((row.get("name") or "").strip().lower() == name.strip().lower() for row in results):
            return None

        for row in results:
            existing_name = row.get("name") or ""
            if not existing_name:
                continue
            norm_existing = _normalize_venue_name_for_match(
                existing_name, row.get("city") or "", row.get("state") or ""
            )
            if norm_existing and norm_existing == norm_target:
                return Club.from_db_row(row)

        return None

    def _log_alias_match_reuse(
        self,
        source: str,
        venue_name: str,
        venue_id: str,
        city: Optional[str],
        state: Optional[str],
        alias_match: Club,
    ) -> None:
        Logger.info(
            f"{source} venue '{venue_name}' (venue.id={venue_id}) "
            f"alias-matched to canonical club {alias_match.id} "
            f"'{alias_match.name}' in ({city}, {state}); "
            f"reusing existing row instead of inserting a duplicate."
        )

    def _log_fuzzy_match_reuse(
        self,
        source: str,
        venue_name: str,
        venue_id: str,
        city: Optional[str],
        state: Optional[str],
        fuzzy_match: Club,
    ) -> None:
        # Returning early skips the upserted_source CTE, so the existing club's
        # scraping_sources rows are not touched. This is deliberate: preventing
        # a duplicate clubs row is safer than re-enabling or rewriting a source
        # row that may carry task disposition metadata.
        Logger.info(
            f"{source} venue '{venue_name}' (venue.id={venue_id}) "
            f"fuzzy-matched to existing club {fuzzy_match.id} "
            f"'{fuzzy_match.name}' in ({city}, {state}); "
            f"reusing existing row instead of inserting a duplicate."
        )

    def upsert_for_seatengine_venue(self, venue: dict) -> Optional[Club]:
        """
        Upsert a clubs row for a SeatEngine venue discovered via the national
        enumeration job.  On conflict (name), preserves any existing seatengine_id
        and scraper values rather than overwriting them.

        Args:
            venue: dict with at minimum 'id' and 'name' keys from SeatEngine API

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        venue_id = str(venue.get("id", "")).strip()
        name = (venue.get("name") or "").strip()
        if not venue_id or not name:
            return None

        address = (venue.get("address") or "").strip()
        website = (venue.get("website") or "").strip()
        zip_code = (venue.get("zip") or venue.get("postal_code") or "").strip()

        from laughtrack.utilities.domain.club.quality_filter import is_junk_venue  # noqa: PLC0415
        if is_junk_venue(name, website):
            return None

        from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address  # noqa: PLC0415
        city, state = parse_city_state_from_address(address)

        fuzzy_match = self._find_fuzzy_match_in_location(name, city, state)
        if fuzzy_match is not None:
            self._log_fuzzy_match_reuse("SeatEngine", name, venue_id, city, state, fuzzy_match)
            return fuzzy_match

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE,
                (name, address, website, zip_code, city, state, venue_id, website),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for SeatEngine venue {venue_id}: {e}")
            raise

    def upsert_for_seatengine_v3_venue(self, venue: dict) -> Optional[Club]:
        """
        Upsert a clubs row for a SeatEngine v3 venue discovered via the national
        discovery job.  On conflict (name), preserves any existing seatengine_id
        and scraper values rather than overwriting them.

        Args:
            venue: dict with at minimum 'uuid' and 'name' keys from the v3 GraphQL API.
                   Optional keys: 'address', 'website', 'zipCode'/'zip_code', 'city', 'state'.

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        venue_uuid = (venue.get("uuid") or "").strip()
        name = (venue.get("name") or "").strip()
        if not venue_uuid or not name:
            return None

        address = (venue.get("address") or "").strip()
        website = (venue.get("website") or "").strip()
        zip_code = (venue.get("zipCode") or venue.get("zip_code") or venue.get("zip") or "").strip()
        # v3 venues are served from v-{uuid}.seatengine.net
        scraping_url = f"https://v-{venue_uuid}.seatengine.net"

        from laughtrack.utilities.domain.club.quality_filter import is_junk_venue  # noqa: PLC0415
        if is_junk_venue(name, website):
            return None

        # Prefer explicit city/state from the API; fall back to address parsing.
        city = (venue.get("city") or "").strip() or None
        state = (venue.get("state") or "").strip() or None
        if not city or not state:
            from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address  # noqa: PLC0415
            parsed_city, parsed_state = parse_city_state_from_address(address)
            city = city or parsed_city
            state = state or parsed_state

        fuzzy_match = self._find_fuzzy_match_in_location(name, city, state)
        if fuzzy_match is not None:
            self._log_fuzzy_match_reuse("SeatEngine v3", name, venue_uuid, city, state, fuzzy_match)
            return fuzzy_match

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE,
                (name, address, website, zip_code, city, state, venue_uuid, scraping_url),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for SeatEngine v3 venue {venue_uuid}: {e}")
            raise

    def upsert_for_ticketmaster_venue(self, venue: dict) -> Optional[Club]:
        """
        Upsert a clubs row for a Ticketmaster venue discovered via the national
        comedy genre scraper.  On conflict (name), preserves any existing
        ticketmaster_id, scraper, and timezone values.

        Args:
            venue: dict from TM Discovery API _embedded.venues[0]

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        venue_id = (venue.get("id") or "").strip()
        name = (venue.get("name") or "").strip()
        if not venue_id or not name:
            return None

        from laughtrack.utilities.domain.club.quality_filter import is_junk_venue  # noqa: PLC0415
        if is_junk_venue(name):
            return None

        address_obj = venue.get("address") or {}
        street = address_obj.get("line1", "")
        city = (venue.get("city") or {}).get("name", "") or None
        state = (venue.get("state") or {}).get("stateCode", "") or None
        address_parts = [p for p in [street, city, state] if p]
        address = ", ".join(address_parts)
        zip_code = (venue.get("postalCode") or "").strip()
        timezone = (venue.get("timezone") or "").strip() or None

        fuzzy_match = self._find_fuzzy_match_in_location(name, city, state)
        if fuzzy_match is not None:
            self._log_fuzzy_match_reuse("Ticketmaster", name, venue_id, city, state, fuzzy_match)
            return fuzzy_match

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE,
                (name, address, zip_code, city, state, timezone, venue_id),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for Ticketmaster venue {venue_id}: {e}")
            raise

    def upsert_for_tour_date_venue(self, venue: dict) -> Optional[Club]:
        """
        Upsert a clubs row for a venue discovered via the tour-date aggregator
        (Songkick or BandsInTown).  On conflict (name), preserves any existing
        scraper and timezone values rather than overwriting them.

        Args:
            venue: dict with at minimum 'name' key; optional 'address', 'zip_code', 'timezone'

        Returns:
            Club: the upserted (or existing) club, or None on invalid input
        """
        name = (venue.get("name") or "").strip()
        if not name:
            return None

        from laughtrack.utilities.domain.club.quality_filter import is_junk_venue  # noqa: PLC0415
        if is_junk_venue(name):
            return None

        address = (venue.get("address") or "").strip()
        zip_code = (venue.get("zip_code") or "").strip()
        timezone = (venue.get("timezone") or None)
        discovery_metadata = _build_tour_date_discovery_metadata(venue)

        from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address  # noqa: PLC0415
        city, state = parse_city_state_from_address(address)

        fuzzy_match = self._find_fuzzy_match_in_location(name, city, state)
        if fuzzy_match is not None:
            self._log_fuzzy_match_reuse("Tour date", name, name, city, state, fuzzy_match)
            return fuzzy_match

        try:
            results = self.execute_with_cursor(
                ClubQueries.UPSERT_CLUB_BY_TOUR_DATE_VENUE,
                (name, address, zip_code, city, state, timezone, discovery_metadata),
                return_results=True,
            )
            if not results:
                return None
            return Club.from_db_row(results[0])
        except Exception as e:
            Logger.error(f"Error upserting club for tour date venue '{name}': {e}")
            raise

    def enrich_timezones(self, scraper: str = "eventbrite") -> int:
        """
        Enrich timezone for clubs that were upserted without one.

        Queries clubs WHERE scraper = <scraper> AND timezone IS NULL, infers
        the timezone from the stored address (US state abbreviation), and
        updates only rows still NULL — so re-running is always safe.

        Args:
            scraper: The scraper type to filter clubs by (default: 'eventbrite').

        Returns:
            Number of clubs whose timezone was successfully updated.
        """
        from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_address  # noqa: PLC0415

        rows = self.execute_with_cursor(
            ClubQueries.GET_CLUBS_WITH_NULL_TIMEZONE,
            (scraper,),
            return_results=True,
        )
        if not rows:
            Logger.info(f"No clubs with scraper='{scraper}' and timezone=NULL found.")
            return 0

        updates: List[tuple] = []
        for row in rows:
            club = Club.from_db_row(row)
            tz = timezone_from_address(club.address)
            if tz:
                updates.append((club.id, tz))
            else:
                Logger.warning(
                    f"Could not resolve timezone for club {club.id} '{club.name}' "
                    f"(address: {club.address!r})"
                )

        if not updates:
            Logger.info("Timezone enrichment: no resolvable timezones found.")
            return 0

        results = self.execute_batch_operation(
            ClubQueries.BATCH_UPDATE_CLUB_TIMEZONES,
            updates,
            return_results=True,
        )
        updated = len(results) if results else 0
        null_guarded = len(updates) - updated
        unresolvable = len(rows) - len(updates)
        Logger.info(
            f"Timezone enrichment: {updated}/{len(updates)} updated, "
            f"{null_guarded} resolvable-but-missed (null-guard fired), "
            f"{unresolvable} skipped (no state match), "
            f"{len(rows)} total examined."
        )
        return updated

    def backfill_city_state(self) -> int:
        """
        Populate city and state for clubs where either column is NULL, by
        parsing the stored address field (format: "Street, City, State ZIP").

        Only updates rows still missing city or state — re-running is safe.

        Returns:
            Number of clubs whose city/state was successfully updated.
        """
        from laughtrack.utilities.domain.club.timezone_lookup import parse_city_state_from_address  # noqa: PLC0415

        rows = self.execute_with_cursor(
            ClubQueries.GET_CLUBS_WITH_NULL_CITY_STATE,
            return_results=True,
        )
        if not rows:
            Logger.info("City/state backfill: no clubs with missing city or state found.")
            return 0

        updates: List[tuple] = []
        for row in rows:
            club = Club.from_db_row(row)
            city, state = parse_city_state_from_address(club.address)
            if city or state:
                updates.append((club.id, city, state))
            else:
                Logger.warning(
                    f"Could not parse city/state for club {club.id} '{club.name}' "
                    f"(address: {club.address!r})"
                )

        if not updates:
            Logger.info("City/state backfill: no parseable addresses found.")
            return 0

        results = self.execute_batch_operation(
            ClubQueries.BATCH_UPDATE_CLUB_CITY_STATE,
            updates,
            return_results=True,
        )
        updated = len(results) if results else 0
        Logger.info(
            f"City/state backfill: {updated}/{len(updates)} updated, "
            f"{len(rows) - len(updates)} skipped (unparseable address), "
            f"{len(rows)} total examined."
        )
        return updated

    def refresh_club_total_shows(self) -> None:
        """Recompute total_shows for every club by counting Show rows per club_id.

        Called at the end of each scrape run so the column stays in sync with
        the current shows table.  Clubs with no shows are set to 0.
        """
        try:
            self.execute_with_cursor(ClubQueries.UPDATE_CLUB_TOTAL_SHOWS)
            Logger.info("refresh_club_total_shows: club total_shows updated")
        except Exception as e:
            Logger.error(f"Error refreshing club total_shows: {str(e)}")
            raise

    def get_active_festival_ids(self) -> Set[int]:
        """Return IDs of festival clubs that have shows in the next 90 days.

        Festivals without upcoming shows are considered off-season and can be
        skipped during bulk scrape runs.
        """
        try:
            results = self.execute_with_cursor(
                ClubQueries.GET_ACTIVE_FESTIVAL_IDS, return_results=True
            )
            ids = {row["id"] for row in results} if results else set()
            Logger.info(f"Found {len(ids)} active festival club(s) with upcoming shows")
            return ids
        except Exception as e:
            Logger.error(f"Error fetching active festival IDs: {e}")
            return set()

    def get_all_club_ids(self) -> List[int]:
        """
        Fetch all active, visible club IDs from the database.

        Returns:
            List[int]: IDs of every active, visible club (regardless of scraper).
        """
        results = self.execute_with_cursor(ClubQueries.GET_ALL_CLUB_IDS, return_results=True)
        if not results:
            raise ValueError("No active clubs found in database")

        Logger.info(f"Retrieved {len(results)} active club IDs from database")
        return [row["id"] for row in results]

    def update_club_popularity(self, club_ids: Optional[List[int]] = None) -> None:
        """
        Recompute and persist popularity for clubs.

        Aggregates show activity and lineup quality over a ±90-day window per
        club (see ``ClubQueries.BATCH_GET_CLUB_POPULARITY``).  Clubs with no
        shows in that window are absent from the result set and keep their
        current popularity value — the signal is "this club is active right
        now", not "this club has ever been active".

        Args:
            club_ids: Optional list of specific club IDs to update.  When
                ``None``, every active, visible club is considered.
        """
        try:
            # When club_ids is None/empty, get_all_club_ids raises on an empty
            # database, so target_ids is guaranteed non-empty past this line.
            target_ids = club_ids if club_ids else self.get_all_club_ids()

            results = self.execute_with_cursor(
                ClubQueries.BATCH_GET_CLUB_POPULARITY, (target_ids,), return_results=True
            )

            if not results:
                Logger.info(
                    f"update_club_popularity: no clubs with show activity in the ±90d window "
                    f"(examined {len(target_ids)} clubs)"
                )
                return

            result_club_ids = [int(row["club_id"]) for row in results]
            popularity_values = [float(row["popularity"]) for row in results]

            self.execute_with_cursor(
                ClubQueries.BATCH_UPDATE_CLUB_POPULARITY,
                (result_club_ids, popularity_values),
            )

            Logger.info(
                f"update_club_popularity: updated {len(results)}/{len(target_ids)} clubs "
                f"(clubs without recent/upcoming shows keep their prior value)"
            )

        except Exception as e:
            Logger.error(f"Error updating club popularity: {str(e)}")
            raise

    def get_clubs_for_scraper(self, scraper_type: str) -> List[Club]:
        """
        Fetch all clubs that use a specific scraper type.

        Args:
            scraper_type: The scraper type to filter clubs by

        Returns:
            List[Club]: List of clubs using the specified scraper type
        """
        if not scraper_type:
            raise ValueError("No scraper type provided")

        try:
            results = self.execute_with_cursor(ClubQueries.GET_CLUBS_BY_SCRAPER, (scraper_type,), return_results=True)
            if not results:
                raise ValueError(f"No clubs found for scraper type: {scraper_type}")

            Logger.info(f"Retrieved {len(results)} clubs for scraper type '{scraper_type}'")
            return [Club.from_db_row(row) for row in results]

        except Exception as e:
            Logger.error(f"Error fetching clubs for scraper '{scraper_type}': {str(e)}")
            raise
