"""
Unit tests for ClubHandler.upsert_for_eventbrite_venue.

Verifies three contracts:
1. Happy path — valid venue upserts and returns a Club with the correct eventbrite_id.
2. Conflict path — existing club by name returns existing row with preserved
   scraper/eventbrite_id (COALESCE semantics).
3. Invalid input — None venue, missing id, or missing name returns None without raising.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from _entities_test_helpers import _load_module, _stub


# Non-foundation stubs (foundation modules are registered by conftest.py)
from typing import TypeVar as _TypeVar
_T = _TypeVar("T")
_stub("laughtrack.foundation.models.types", T=_T, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True, T=_T)
_stub("laughtrack.adapters.db", create_connection=MagicMock())
_stub("laughtrack.adapters", as_package=True, create_connection=MagicMock())

# Load Club model directly (bypasses club __init__.py which may pull in handler)
_club_model_mod = _load_module(
    "src/laughtrack/core/entities/club/model.py",
    "laughtrack.core.entities.club.model_direct",
)
Club = _club_model_mod.Club

# Load ClubQueries directly
_club_queries_mod = _load_module("sql/club_queries.py", "sql.club_queries_direct")
ClubQueries = _club_queries_mod.ClubQueries

# Load BaseDatabaseHandler
_base_handler_mod = _load_module(
    "src/laughtrack/core/data/base_handler.py",
    "laughtrack.core.data.base_handler_direct",
)
BaseDatabaseHandler = _base_handler_mod.BaseDatabaseHandler

# Patch the club model module name so ClubHandler can import it
sys.modules["laughtrack.core.entities.club.model"] = _club_model_mod
sys.modules["laughtrack.core.data.base_handler"] = _base_handler_mod
sys.modules["sql.club_queries"] = _club_queries_mod

# Load timezone_lookup (used via lazy import in handler methods)
_tz_lookup_mod = _load_module(
    "src/laughtrack/utilities/domain/club/timezone_lookup.py",
    "laughtrack.utilities.domain.club.timezone_lookup",
)
parse_city_state_from_address = _tz_lookup_mod.parse_city_state_from_address
sys.modules["laughtrack.utilities.domain.club.timezone_lookup"] = _tz_lookup_mod

# Load ClubHandler
_club_handler_mod = _load_module(
    "src/laughtrack/core/entities/club/handler.py",
    "laughtrack.core.entities.club.handler_direct",
)
ClubHandler = _club_handler_mod.ClubHandler


# ---------------------------------------------------------------------------
# Default: treat every venue as non-junk so happy-path tests see a Club result.
# Junk-filter test classes override this with return_value=True inside each method.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_is_junk_venue():
    with patch("laughtrack.utilities.domain.club.quality_filter.is_junk_venue", return_value=False):
        yield


# ---------------------------------------------------------------------------
# Minimal venue/address stand-ins (no imports from Eventbrite models needed)
# ---------------------------------------------------------------------------

class _FakeAddress:
    def __init__(self, address_1=None, city=None, region=None, postal_code=None):
        self.address_1 = address_1
        self.city = city
        self.region = region
        self.postal_code = postal_code


class _FakeVenue:
    def __init__(self, id=None, name=None, address=None):
        self.id = id
        self.name = name
        self.address = address


def _scraping_sources_entry(*, platform, scraper_key="", source_url="",
                             platform_id=None, club_id=None, source_id=1):
    """Build one element of the scraping_sources list as produced by the
    json_agg LATERAL in ClubQueries — the shape Club.from_db_row consumes."""
    source = {
        "id": source_id,
        "club_id": club_id,
        "platform": platform,
        "scraper_key": scraper_key or "",
        "source_url": source_url or "",
        "priority": 0,
        "enabled": True,
        "metadata": {},
    }
    if platform == "seatengine":
        source["seatengine_id"] = int(platform_id) if platform_id is not None else None
    elif platform == "seatengine_v3":
        source["seatengine_v3_id"] = platform_id
    elif platform == "eventbrite":
        source["eventbrite_id"] = platform_id
    elif platform == "ticketmaster":
        source["ticketmaster_id"] = platform_id
    elif platform == "ovationtix":
        source["ovationtix_id"] = platform_id
    elif platform == "wix_events":
        source["wix_event_id"] = platform_id
    elif platform == "squadup":
        source["squadup_id"] = platform_id
    return source


def _row_with_source(defaults, *, platform, legacy):
    """Take a defaults dict for a club row plus the platform + legacy field
    overrides, and attach the scraping_sources list that Club.from_db_row
    will read."""
    defaults["scraping_sources"] = [
        _scraping_sources_entry(
            platform=platform,
            scraper_key=legacy.get("scraper", "") or "",
            source_url=legacy.get("scraping_url", "") or "",
            platform_id=legacy.get("platform_id"),
            club_id=defaults.get("id"),
        )
    ]
    return defaults


_LEGACY_KEYS = ("scraper", "scraping_url", "eventbrite_id",
                "ticketmaster_id", "seatengine_id",
                "ovationtix_client_id", "wix_comp_id", "squadup_user_id")


def _split_legacy(overrides, defaults_legacy):
    """Pop legacy fields out of overrides; merge with helper-level defaults."""
    legacy = dict(defaults_legacy)
    for key in _LEGACY_KEYS:
        if key in overrides:
            legacy[key] = overrides.pop(key)
    return legacy


def _make_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "",
        "popularity": 0,
        "zip_code": "10001",
        "city": "New York",
        "state": "NY",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "eventbrite",
        "scraping_url": "www.eventbrite.com",
        "eventbrite_id": "venue-abc",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="eventbrite", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "platform_id": legacy["eventbrite_id"],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChainScrapingDefaultQueries:
    def _normalized(self, sql: str) -> str:
        return " ".join(sql.split()).upper()

    def test_base_club_select_resolves_blank_source_key_from_chain_default(self):
        sql = self._normalized(ClubQueries.GET_ALL_CLUBS)

        assert "CHAIN_SCRAPING_DEFAULTS CSD" in sql
        assert "CSD.CHAIN_ID = C.CHAIN_ID" in sql
        assert "CSD.PLATFORM = SS.PLATFORM" in sql
        assert "CSD.PRIORITY = SS.PRIORITY" in sql
        assert "NULLIF(SS.SCRAPER_KEY, '') IS NULL" in sql
        assert "COALESCE(NULLIF(SS.SCRAPER_KEY, ''), CSD.SCRAPER_KEY, SS.SCRAPER_KEY)" in sql

    def test_base_club_select_keeps_per_club_source_fields(self):
        sql = self._normalized(ClubQueries.GET_ALL_CLUBS)

        assert "'SOURCE_URL', SS.SOURCE_URL" in sql
        assert "SS.CLUB_ID = C.ID" in sql
        assert "SS.ENABLED = TRUE" in sql
        assert "COALESCE(CSD.METADATA, '{}'::JSONB) || COALESCE(SS.METADATA, '{}'::JSONB)" in sql

    def test_get_clubs_by_scraper_filters_on_effective_primary_source_key(self):
        sql = self._normalized(ClubQueries.GET_CLUBS_BY_SCRAPER)

        assert "WHERE PRIMARY_SOURCE.SCRAPER_KEY = %S" in sql
        assert "COALESCE(NULLIF(SS.SCRAPER_KEY, ''), CSD.SCRAPER_KEY, SS.SCRAPER_KEY) AS SCRAPER_KEY" in sql

    def test_distinct_scraper_types_counts_effective_chain_default_keys(self):
        sql = self._normalized(ClubQueries.GET_DISTINCT_SCRAPER_TYPES)

        assert "COALESCE(NULLIF(SS.SCRAPER_KEY, ''), CSD.SCRAPER_KEY, SS.SCRAPER_KEY) AS SCRAPER_KEY" in sql
        assert "CHAIN_SCRAPING_DEFAULTS CSD" in sql
        assert "NULLIF(SS.SCRAPER_KEY, '') IS NULL" in sql


class TestClubAliasResolution:
    def test_eventbrite_alias_hit_returns_canonical_club_before_fuzzy_match(self):
        canonical = _make_club_row(
            id=86,
            name="Mesquite St. Comedy Club",
            city="Corpus Christi",
            state="TX",
            eventbrite_id="canonical",
            aliases=[
                {
                    "alias_name": "Mesquite Street",
                    "normalized_alias_name": "mesquite street",
                    "normalized_city": "corpus christi",
                    "normalized_state": "tx",
                }
            ],
        )
        venue = _FakeVenue(
            id="mesquite-street-source",
            name="Mesquite Street",
            address=_FakeAddress(city="Corpus Christi", region="TX"),
        )
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[canonical]) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 86
        assert result.name == "Mesquite St. Comedy Club"
        assert mock_exec.call_count == 1
        assert "club_aliases" in mock_exec.call_args.args[0]

    def test_alias_same_name_different_city_does_not_match(self):
        new_row = _make_club_row(
            id=211,
            name="Mesquite Street",
            city="Austin",
            state="TX",
            eventbrite_id="austin-source",
        )
        venue = _FakeVenue(
            id="austin-source",
            name="Mesquite Street",
            address=_FakeAddress(city="Austin", region="TX"),
        )
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", side_effect=[[], [new_row]]) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 211
        assert mock_exec.call_count == 2
        assert "club_aliases" in mock_exec.call_args_list[0].args[0]
        assert "WHERE LOWER(TRIM(c.city))" in mock_exec.call_args_list[0].args[0]
        assert "INSERT INTO clubs" in mock_exec.call_args_list[1].args[0]

    def test_tour_date_no_alias_falls_back_to_upsert(self):
        new_row = _make_club_row(
            id=300,
            name="Fresh Venue",
            city="Corpus Christi",
            state="TX",
        )
        venue = {
            "name": "Fresh Venue",
            "address": "123 Shoreline Blvd, Corpus Christi, TX",
            "zip_code": "78401",
            "timezone": "America/Chicago",
        }
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", side_effect=[[], [new_row]]) as mock_exec:
            result = handler.upsert_for_tour_date_venue(venue)

        assert result is not None
        assert result.id == 300
        assert mock_exec.call_count == 2
        assert "club_aliases" in mock_exec.call_args_list[0].args[0]
        assert "INSERT INTO clubs" in mock_exec.call_args_list[1].args[0]


class TestUpsertForEventbriteVenueHappyPath:
    """Criterion 668: valid venue inserts new club and returns Club with correct eventbrite_id."""

    def test_returns_club_with_matching_eventbrite_id(self):
        venue = _FakeVenue(
            id="venue-abc",
            name="Comedy Cellar",
            address=_FakeAddress(
                address_1="117 MacDougal St",
                city="New York",
                region="NY",
                postal_code="10012",
            ),
        )
        row = _make_club_row(name="Comedy Cellar", eventbrite_id="venue-abc", zip_code="10012")

        handler = ClubHandler()
        # side_effect: location lookup returns no candidate (fuzzy match path skipped),
        # then UPSERT returns the freshly-inserted row. See TASK-1926.
        with patch.object(handler, "execute_with_cursor", side_effect=[[], [row]]):
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert isinstance(result, Club)
        assert result.eventbrite_id == "venue-abc"
        assert result.name == "Comedy Cellar"

    def test_passes_correct_params_to_execute(self):
        """execute_with_cursor receives (name, address, eventbrite_id, zip_code)."""
        venue = _FakeVenue(
            id="venue-xyz",
            name="Gotham Comedy Club",
            address=_FakeAddress(
                address_1="208 W 23rd St",
                city="New York",
                region="NY",
                postal_code="10011",
            ),
        )
        row = _make_club_row(name="Gotham Comedy Club", eventbrite_id="venue-xyz", zip_code="10011")

        handler = ClubHandler()
        # side_effect: location lookup returns no candidate, then UPSERT runs. The
        # UPSERT call is the second/last; mock_exec.call_args targets it. (TASK-1926)
        with patch.object(handler, "execute_with_cursor", side_effect=[[], [row]]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        assert mock_exec.call_count == 2
        call_args = mock_exec.call_args  # last call = UPSERT
        params = call_args[0][1]  # second positional arg is the params tuple
        # New CTE shape: (name, address, zip_code, city, state, venue_id)
        assert params[0] == "Gotham Comedy Club"   # name
        assert params[2] == "10011"                # zip_code
        assert params[5] == "venue-xyz"            # venue_id (scraping_sources.eventbrite_id)

    def test_address_concatenated_from_parts(self):
        """Address is joined from address_1, city, region with ', '."""
        venue = _FakeVenue(
            id="v1",
            name="Laugh Factory",
            address=_FakeAddress(address_1="8001 Sunset Blvd", city="Los Angeles", region="CA"),
        )
        row = _make_club_row(name="Laugh Factory", eventbrite_id="v1",
                             address="8001 Sunset Blvd, Los Angeles, CA")

        handler = ClubHandler()
        # side_effect: location lookup returns no candidate, then UPSERT runs. (TASK-1926)
        with patch.object(handler, "execute_with_cursor", side_effect=[[], [row]]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]  # last call = UPSERT
        assert params[1] == "8001 Sunset Blvd, Los Angeles, CA"

    def test_zip_code_empty_when_no_address(self):
        """zip_code defaults to '' when venue.address is None."""
        venue = _FakeVenue(id="v2", name="Club No Address", address=None)
        row = _make_club_row(name="Club No Address", eventbrite_id="v2", zip_code="")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[2] == ""   # zip_code (new CTE shape)
        assert params[1] == ""   # address


class TestUpsertForEventbriteVenueConflict:
    """Criterion 669: conflict on name preserves existing scraper and eventbrite_id via COALESCE."""

    def test_existing_club_retains_original_scraper(self):
        """When a club already exists with scraper='broadway', it stays 'broadway', not 'eventbrite'."""
        venue = _FakeVenue(id="new-venue-id", name="Broadway Comedy Club")
        # DB returns the existing row — COALESCE kept the original scraper
        existing_row = _make_club_row(
            name="Broadway Comedy Club",
            scraper="broadway",
            eventbrite_id="original-eb-id",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.scraper == "broadway"

    def test_existing_club_retains_original_eventbrite_id(self):
        """When a club already has an eventbrite_id, it stays unchanged."""
        venue = _FakeVenue(id="different-id", name="Broadway Comedy Club")
        existing_row = _make_club_row(
            name="Broadway Comedy Club",
            eventbrite_id="original-eb-id",
            scraper="broadway",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result.eventbrite_id == "original-eb-id"

    def test_sql_uses_coalesce_for_scraper(self):
        """SQL contract: UPSERT_CLUB_BY_EVENTBRITE_VENUE must use COALESCE for scraper."""
        sql = ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPER" in sql

    def test_sql_uses_coalesce_for_eventbrite_id(self):
        """SQL contract: UPSERT_CLUB_BY_EVENTBRITE_VENUE must COALESCE the
        scraping_sources.eventbrite_id (the Eventbrite venue id) so existing
        rows are preserved on conflict."""
        sql = ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE.upper()
        assert "SCRAPING_SOURCES" in sql
        assert "EVENTBRITE_ID" in sql


class TestUpsertSqlAvoidsCteSnapshotBug:
    """Regression tests for TASK-1927: the final SELECT must project from the
    upserted_club CTE (which sees its own RETURNING rows) rather than JOINing
    against the clubs table snapshot. PostgreSQL data-modifying CTEs share a
    single statement-level snapshot, so a `JOIN clubs c ON uc.id = c.id`
    cannot see a freshly INSERTed row — first-time per-venue upserts in
    EventbriteScraper organizer-mode silently returned 0 rows on 2026-05-05,
    dropping 90 'Big Couch' shows for hidden club 2287."""

    def _normalized(self, sql: str) -> str:
        # Collapse whitespace so multi-line SQL formatting doesn't defeat
        # the substring match.
        return " ".join(sql.split()).upper()

    def test_eventbrite_upsert_selects_from_cte_not_clubs_table(self):
        sql = self._normalized(ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE)
        # The buggy shape was `JOIN UPSERTED_CLUB UC ON UC.ID = C.ID` against
        # the live clubs table; the fixed shape projects directly from the CTE.
        assert "JOIN UPSERTED_CLUB" not in sql
        assert "FROM UPSERTED_CLUB" in sql
        # CTE must RETURNING * so the final SELECT can read the inserted row.
        assert "RETURNING *" in sql

    def test_seatengine_upsert_selects_from_cte_not_clubs_table(self):
        sql = self._normalized(ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE)
        assert "JOIN UPSERTED_CLUB" not in sql
        assert "FROM UPSERTED_CLUB" in sql
        assert "RETURNING *" in sql

    def test_seatengine_v3_upsert_selects_from_cte_not_clubs_table(self):
        sql = self._normalized(ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE)
        assert "JOIN UPSERTED_CLUB" not in sql
        assert "FROM UPSERTED_CLUB" in sql
        assert "RETURNING *" in sql

    def test_ticketmaster_upsert_selects_from_cte_not_clubs_table(self):
        sql = self._normalized(ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE)
        assert "JOIN UPSERTED_CLUB" not in sql
        assert "FROM UPSERTED_CLUB" in sql
        assert "RETURNING *" in sql

    def test_tour_date_upsert_selects_from_cte_not_clubs_table(self):
        sql = self._normalized(ClubQueries.UPSERT_CLUB_BY_TOUR_DATE_VENUE)
        assert "JOIN UPSERTED_CLUB" not in sql
        assert "FROM UPSERTED_CLUB" in sql
        assert "RETURNING *" in sql


class TestSeatEngineUpsertRespectsDispositionMetadata:
    """Regression tests for TASK-1968: UPSERT_CLUB_BY_SEATENGINE_VENUE and
    UPSERT_CLUB_BY_SEATENGINE_V3_VENUE must not unconditionally re-enable a row
    whose metadata carries any ``task_<id>_disposition`` stamp. seatengine_national
    iterates v1 venue ids 1..N every night and upserts every still-listed venue,
    so the prior bare ``enabled = TRUE`` reverted dispositional disables within
    24h (concrete prior-art: ss=924 club 602 'Laugh And Enjoy' was disabled on
    2026-05-02 and back to enabled=true by 2026-05-03 07:42:54). The fix replaces
    the bare TRUE with a CASE that preserves ``scraping_sources.enabled`` when
    any matching disposition key exists on the existing row, while leaving the
    new-venue INSERT path emitting enabled=true."""

    def _normalized(self, sql: str) -> str:
        # Collapse whitespace so multi-line SQL formatting doesn't defeat
        # substring matches.
        return " ".join(sql.split()).upper()

    def _conflict_clause(self, sql: str) -> str:
        """Return only the scraping_sources ON CONFLICT … RETURNING segment.

        Both upserts have two ON CONFLICT clauses — the first on `clubs.name`
        for the upserted_club CTE, the second on `(club_id, platform, priority)`
        for the upserted_source CTE. Anchor on the (CLUB_ID, … so we only see
        the scraping_sources branch we are guarding.
        """
        normalized = self._normalized(sql)
        start = normalized.index("ON CONFLICT (CLUB_ID")
        end = normalized.index("RETURNING CLUB_ID", start)
        return normalized[start:end]

    def _seatengine_sqls(self):
        return [
            ("seatengine", ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE),
            ("seatengine_v3", ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE),
        ]

    def test_conflict_branch_preserves_existing_enabled_on_disposition_metadata(self):
        for label, raw in self._seatengine_sqls():
            conflict = self._conflict_clause(raw)
            # The conflict branch must inspect existing-row metadata for any
            # disposition key and short-circuit the re-enable when found.
            assert "JSONB_OBJECT_KEYS" in conflict, label
            assert "SCRAPING_SOURCES.METADATA" in conflict, label
            assert "TASK_%_DISPOSITION" in conflict, label
            # Preserves the existing enabled flag (not EXCLUDED.enabled, which
            # would defeat the carve-out by always re-enabling).
            assert "THEN SCRAPING_SOURCES.ENABLED" in conflict, label
            assert "ELSE TRUE" in conflict, label
            # Must NOT contain a bare unconditional re-enable in this branch.
            assert "ENABLED = TRUE" not in conflict, label

    def test_insert_branch_still_emits_enabled_true_for_new_venues(self):
        # The first-time-discovery path lives in the SELECT inside the
        # upserted_source CTE, BEFORE the (club_id, platform, priority) ON
        # CONFLICT clause. Slice that segment and confirm a bare TRUE is still
        # being inserted. (There is an earlier ON CONFLICT on clubs.name for
        # the upserted_club CTE; we want the one on the scraping_sources CTE.)
        for label, raw in self._seatengine_sqls():
            normalized = self._normalized(raw)
            select_start = normalized.index("INSERT INTO SCRAPING_SOURCES")
            conflict_start = normalized.index("ON CONFLICT (CLUB_ID", select_start)
            insert_segment = normalized[select_start:conflict_start]
            # Bare TRUE literal in the SELECT projection — confirms the
            # disposition guard didn't accidentally bleed into the insert path.
            assert ", TRUE," in insert_segment, label
            # And the conflict guard must not appear in the insert segment.
            assert "JSONB_OBJECT_KEYS" not in insert_segment, label


class TestEventbriteTicketmasterTourDateUpsertRespectsDispositionMetadata:
    """Regression tests for TASK-1978: UPSERT_CLUB_BY_EVENTBRITE_VENUE,
    UPSERT_CLUB_BY_TICKETMASTER_VENUE, and UPSERT_CLUB_BY_TOUR_DATE_VENUE must
    respect the same dispositional disable contract as the seatengine pair fixed
    in TASK-1968. Each query's caller drives a recurring nightly sweep that
    re-emits previously-disposed venues — eventbrite organizer-mode replays
    every distinct (name, city, state) per organizer feed, ticketmaster_national
    paginates the TM Discovery API for US Comedy events, and the two
    tour_date callers (TourDatesScraper + ComedianWebsiteScraper) iterate the
    full bandsintown_id / personal-website comedian set and re-discover
    venues per artist. The bare 'enabled = TRUE' that originally lived on each
    of these queries' (club_id, platform, priority) ON CONFLICT branch reverted
    any dispositional disable on a still-listed venue within 24h, exactly the
    pattern that TASK-1968 first observed on seatengine_national (ss=924 club
    602 'Laugh And Enjoy' was disabled on 2026-05-02 and back to enabled=true
    by 2026-05-03 07:42:54). The fix mirrors the seatengine carve-out: when the
    existing scraping_sources row carries any 'task_<id>_disposition' metadata
    key, the UPDATE branch preserves scraping_sources.enabled instead of
    re-setting it to TRUE; otherwise (no disposition stamp, including all
    first-time-discovery rows) the upsert continues to flip enabled to TRUE."""

    def _normalized(self, sql: str) -> str:
        # Collapse whitespace so multi-line SQL formatting doesn't defeat
        # substring matches.
        return " ".join(sql.split()).upper()

    def _conflict_clause(self, sql: str) -> str:
        """Return only the scraping_sources ON CONFLICT … RETURNING segment.

        Each upsert has two ON CONFLICT clauses — the first on `clubs.name`
        for the upserted_club CTE, the second on `(club_id, platform, priority)`
        for the upserted_source CTE. Anchor on the (CLUB_ID, … so we only see
        the scraping_sources branch we are guarding.
        """
        normalized = self._normalized(sql)
        start = normalized.index("ON CONFLICT (CLUB_ID")
        end = normalized.index("RETURNING CLUB_ID", start)
        return normalized[start:end]

    def _at_risk_sqls(self):
        return [
            ("eventbrite", ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE),
            ("ticketmaster", ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE),
            ("tour_date", ClubQueries.UPSERT_CLUB_BY_TOUR_DATE_VENUE),
        ]

    def test_conflict_branch_preserves_existing_enabled_on_disposition_metadata(self):
        for label, raw in self._at_risk_sqls():
            conflict = self._conflict_clause(raw)
            # The conflict branch must inspect existing-row metadata for any
            # disposition key and short-circuit the re-enable when found.
            assert "JSONB_OBJECT_KEYS" in conflict, label
            assert "SCRAPING_SOURCES.METADATA" in conflict, label
            assert "TASK_%_DISPOSITION" in conflict, label
            # Preserves the existing enabled flag (not EXCLUDED.enabled, which
            # would defeat the carve-out by always re-enabling).
            assert "THEN SCRAPING_SOURCES.ENABLED" in conflict, label
            assert "ELSE TRUE" in conflict, label
            # Must NOT contain a bare unconditional re-enable in this branch.
            assert "ENABLED = TRUE" not in conflict, label

    def test_insert_branch_still_emits_enabled_true_for_new_venues(self):
        # The first-time-discovery path lives in the SELECT inside the
        # upserted_source CTE, BEFORE the (club_id, platform, priority) ON
        # CONFLICT clause. Slice that segment and confirm a bare TRUE is still
        # being inserted. (There is an earlier ON CONFLICT on clubs.name for
        # the upserted_club CTE; we want the one on the scraping_sources CTE.)
        for label, raw in self._at_risk_sqls():
            normalized = self._normalized(raw)
            select_start = normalized.index("INSERT INTO SCRAPING_SOURCES")
            conflict_start = normalized.index("ON CONFLICT (CLUB_ID", select_start)
            insert_segment = normalized[select_start:conflict_start]
            # Bare TRUE literal in the SELECT projection — confirms the
            # disposition guard didn't accidentally bleed into the insert path.
            assert ", TRUE," in insert_segment, label
            # And the conflict guard must not appear in the insert segment.
            assert "JSONB_OBJECT_KEYS" not in insert_segment, label


class TestTourDateUpsertDiscoveryMetadata:
    def _normalized(self, sql: str) -> str:
        return " ".join(sql.split()).upper()

    def _conflict_clause(self, sql: str) -> str:
        normalized = self._normalized(sql)
        start = normalized.index("ON CONFLICT (CLUB_ID")
        end = normalized.index("RETURNING CLUB_ID", start)
        return normalized[start:end]

    def test_upsert_passes_discovery_metadata_as_json_param(self):
        row = _make_club_row(name="The Comedy Store")
        venue = {
            "name": "The Comedy Store",
            "address": "Los Angeles, CA",
            "zip_code": "90046",
            "timezone": "America/Los_Angeles",
            "discovery_metadata": {
                "source": "tour_dates",
                "comedian_refs": [{"uuid": "hg-uuid", "name": "Hannah Gadsby"}],
                "event_urls": ["https://www.bandsintown.com/e/99"],
                "platform_hints": ["bandsintown"],
            },
        }
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            result = handler.upsert_for_tour_date_venue(venue)

        assert result is not None
        params = mock_exec.call_args.args[1]
        metadata = json.loads(params[6])
        assert metadata["source"] == "tour_dates"
        assert metadata["comedian_refs"] == [{"uuid": "hg-uuid", "name": "Hannah Gadsby"}]
        assert metadata["event_urls"] == ["https://www.bandsintown.com/e/99"]
        assert metadata["platform_hints"] == ["bandsintown"]
        assert metadata["reference_count"] == 1
        assert isinstance(metadata["first_seen_at"], str)
        assert isinstance(metadata["last_seen_at"], str)

    def test_conflict_branch_merges_metadata_and_preserves_existing_first_seen(self):
        conflict = self._conflict_clause(ClubQueries.UPSERT_CLUB_BY_TOUR_DATE_VENUE)

        assert "METADATA =" in conflict
        assert "SCRAPING_SOURCES.METADATA" in conflict
        assert "EXCLUDED.METADATA" in conflict
        assert "FIRST_SEEN_AT" in conflict
        assert "LAST_SEEN_AT" in conflict
        assert "REFERENCE_COUNT" in conflict
        assert "SCRAPING_SOURCES.METADATA ->> 'FIRST_SEEN_AT'" in conflict


class TestUpsertForEventbriteVenueInvalidInput:
    """Criterion 670: None/missing venue fields returns None without raising."""

    def test_none_venue_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(None)
        assert result is None

    def test_venue_missing_id_returns_none(self):
        venue = _FakeVenue(id=None, name="Some Club")
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_venue_missing_name_returns_none(self):
        venue = _FakeVenue(id="v999", name=None)
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_venue_empty_id_returns_none(self):
        venue = _FakeVenue(id="", name="Some Club")
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_venue_empty_name_returns_none(self):
        venue = _FakeVenue(id="v999", name="")
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_no_db_call_on_invalid_input(self):
        """execute_with_cursor must NOT be called when input is invalid."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.upsert_for_eventbrite_venue(None)
            handler.upsert_for_eventbrite_venue(_FakeVenue(id=None, name="X"))
            handler.upsert_for_eventbrite_venue(_FakeVenue(id="v1", name=None))

        mock_exec.assert_not_called()

    def test_none_returned_when_db_returns_empty(self):
        """If execute_with_cursor returns [] (no row), the method returns None."""
        venue = _FakeVenue(id="v1", name="Valid Club")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]):
            result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None


class TestNormalizeVenueNameForMatch:
    """Direct unit tests for _normalize_venue_name_for_match (TASK-1926).

    The function is the core merge-or-not decision and has several non-trivial
    branches: leading 'the ' strip, longest-first suffix candidate ordering,
    empty-string protection, and non-alphanumeric collapsing. Pinning the
    contract here documents the false-positive/false-negative behavior in
    production directly rather than only via upsert integration tests.
    """

    @pytest.fixture
    def normalize(self):
        # Resolve the helper from the directly-loaded handler module — the
        # module-level import in this test file is via _load_module, so the
        # function isn't available under its package path.
        return _club_handler_mod._normalize_venue_name_for_match

    def test_the_prefix_strip_normalizes_to_same_core(self, normalize):
        """'The Comedy Cellar' and 'Comedy Cellar' both yield 'comedy cellar'."""
        assert normalize("The Comedy Cellar", "New York", "NY") == "comedy cellar"
        assert normalize("Comedy Cellar", "New York", "NY") == "comedy cellar"

    def test_longest_suffix_candidate_strips_first(self, normalize):
        """'big couch new orleans la' must strip the 'new orleans la' suffix
        before falling through to the shorter 'new orleans' candidate; both
        yield 'big couch'."""
        assert normalize("Big Couch New Orleans LA", "New Orleans", "LA") == "big couch"
        assert normalize("Big Couch New Orleans", "New Orleans", "LA") == "big couch"

    def test_name_equal_to_city_keeps_original_form(self, normalize):
        """A venue literally named after its city ('New Orleans' in (New
        Orleans, LA)) must not be reduced to an empty string — empty-string
        protection keeps the pre-strip form so the row stays distinguishable."""
        assert normalize("New Orleans", "New Orleans", "LA") == "new orleans"

    def test_mid_string_city_token_is_preserved(self, normalize):
        """'New Orleans Comedy Club' must NOT collapse to 'comedy club' — only
        a TRAILING city/state token strips. Mid-string occurrences stay
        because folding them would merge unrelated venues that legitimately
        carry a city in the middle of the name."""
        assert normalize("New Orleans Comedy Club", "New Orleans", "LA") == "new orleans comedy club"

    def test_apostrophe_handling_documents_limitation(self, normalize):
        """Apostrophes are non-alphanumeric and collapse to a space, so
        'Joe's Pub' yields 'joe s pub' — intentionally distinct from
        'Joes Pub' which yields 'joes pub'. This is a known limitation:
        venues that vary only by apostrophe across spellings get two rows.
        Documents the trade-off via assertion."""
        assert normalize("Joe's Pub", "New York", "NY") == "joe s pub"
        assert normalize("Joes Pub", "New York", "NY") == "joes pub"
        # Confirm they do NOT collapse to the same form.
        assert normalize("Joe's Pub", "New York", "NY") != normalize("Joes Pub", "New York", "NY")

    def test_lone_the_does_not_strip_to_empty(self, normalize):
        """A name that is just 'The' (after the leading-'the ' strip would
        leave '') only strips when followed by content; a lone 'The' keeps
        the 'the' (no trailing space to match the prefix pattern)."""
        # 'The' alone (no trailing space) does not match the 'the ' prefix.
        assert normalize("The", "New York", "NY") == "the"

    def test_punctuation_collapses_to_space(self, normalize):
        """Comma, parens, em-dash, and unicode whitespace all collapse to
        single spaces before suffix stripping."""
        assert normalize("Big Couch, New Orleans", "New Orleans", "LA") == "big couch"
        assert normalize("Big Couch (New Orleans)", "New Orleans", "LA") == "big couch"

    def test_empty_name_returns_empty_string(self, normalize):
        """Empty input returns empty string; caller (_find_fuzzy_match_in_location)
        treats empty as 'no candidate' and falls through to UPSERT."""
        assert normalize("", "New York", "NY") == ""
        assert normalize("   ", "New York", "NY") == ""

    def test_missing_location_only_strips_prefix_and_punctuation(self, normalize):
        """When city/state are empty, no suffix candidates are built — only
        the 'the ' prefix and punctuation collapse run. This matches the
        helper's caller, which skips the fuzzy-match path entirely when
        location is missing, so this is the safe pass-through behavior."""
        assert normalize("The Big Couch", "", "") == "big couch"
        assert normalize("Big Couch New Orleans", "", "") == "big couch new orleans"

    def test_club_name_normalize_expands_common_abbreviations(self, normalize):
        """Ft./St./Mt. spellings normalize to their expanded forms."""
        assert normalize("Ft. Lauderdale Improv", "Fort Lauderdale", "FL") == "fort lauderdale improv"
        assert normalize("Fort Lauderdale Improv", "Ft. Lauderdale", "FL") == "fort lauderdale improv"
        assert normalize("St. Marks Comedy Club", "New York", "NY") == "saint marks comedy club"
        assert normalize("Mt. Pleasant Comedy", "Mount Pleasant", "SC") == "mount pleasant comedy"

    def test_club_name_normalize_expands_ampersand_and_trailing_punctuation(self, normalize):
        """Ampersands fold to 'and' and trailing punctuation/whitespace is ignored."""
        assert normalize("Comedy & Magic Club.  ", "Hermosa Beach", "CA") == "comedy and magic club"
        assert normalize("Comedy and Magic Club", "Hermosa Beach", "CA") == "comedy and magic club"


class TestUpsertForEventbriteVenueFuzzyMatch:
    """Criterion 6331 (TASK-1926): organizer-feed venues whose names differ only by
    a trailing city suffix ('Big Couch' / 'Big Couch New Orleans') in the same
    (city, state) collapse to one clubs row instead of inserting a duplicate.

    Reproduces the TASK-1919 incident: club 654's Big Couch organizer feed emitted
    25 distinct venue.id values across two name spellings, and ON CONFLICT (name)
    in UPSERT_CLUB_BY_EVENTBRITE_VENUE produced two rows for one physical venue.
    """

    def test_trailing_city_suffix_returns_existing_club_no_upsert(self):
        """A new venue named 'Big Couch New Orleans' must reuse the existing
        'Big Couch' clubs row in (New Orleans, LA) — no second INSERT, no
        second clubs row."""
        existing = _make_club_row(
            id=42,
            name="Big Couch",
            city="New Orleans",
            state="LA",
            eventbrite_id="venue-original",
        )
        venue = _FakeVenue(
            id="venue-new-spelling",
            name="Big Couch New Orleans",
            address=_FakeAddress(
                address_1="123 Frenchmen St",
                city="New Orleans",
                region="LA",
            ),
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            # Only the GET_CLUBS_BY_LOCATION query should fire — UPSERT must not.
            mock_exec.return_value = [existing]
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 42
        assert result.name == "Big Couch"
        assert mock_exec.call_count == 1
        called_sql = mock_exec.call_args_list[0][0][0]
        assert "GET_CLUBS_BY_LOCATION" in called_sql or "WHERE LOWER(TRIM(c.city))" in called_sql

    def test_no_match_falls_through_to_upsert(self):
        """When no existing clubs row in (city, state) normalizes to the same
        core form, the method falls through to UPSERT_CLUB_BY_EVENTBRITE_VENUE."""
        venue = _FakeVenue(
            id="v-fresh",
            name="Brand New Venue",
            address=_FakeAddress(city="Austin", region="TX"),
        )
        new_row = _make_club_row(
            id=200,
            name="Brand New Venue",
            city="Austin",
            state="TX",
            eventbrite_id="v-fresh",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", side_effect=[[], [new_row]]) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 200
        # Two calls: location lookup (no match), then UPSERT.
        assert mock_exec.call_count == 2

    def test_club_dedupe_abbreviations_ft_then_fort_reuses_same_row(self):
        """Scraping Ft. X then Fort X in the same city/state lands on one club row."""
        first_venue = _FakeVenue(
            id="venue-ft",
            name="Ft. Lauderdale Improv",
            address=_FakeAddress(city="Fort Lauderdale", region="FL"),
        )
        second_venue = _FakeVenue(
            id="venue-fort",
            name="Fort Lauderdale Improv",
            address=_FakeAddress(city="Fort Lauderdale", region="FL"),
        )
        existing = _make_club_row(
            id=53,
            name="Ft. Lauderdale Improv",
            city="Fort Lauderdale",
            state="FL",
            eventbrite_id="venue-ft",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", side_effect=[[], [existing], [existing]]) as mock_exec:
            first_result = handler.upsert_for_eventbrite_venue(first_venue)
            second_result = handler.upsert_for_eventbrite_venue(second_venue)

        assert first_result is not None
        assert second_result is not None
        assert first_result.id == second_result.id == 53
        assert mock_exec.call_count == 3

    def test_exact_name_conflict_wins_over_existing_abbreviation_variant(self):
        """An exact name row should use SQL conflict handling, not an older fuzzy variant."""
        variant = _make_club_row(
            id=53,
            name="Ft. Lauderdale Improv",
            city="Fort Lauderdale",
            state="FL",
            eventbrite_id="venue-ft",
        )
        exact = _make_club_row(
            id=460,
            name="Fort Lauderdale Improv",
            city="Fort Lauderdale",
            state="FL",
            eventbrite_id="venue-fort",
        )
        venue = _FakeVenue(
            id="venue-fort-new",
            name="Fort Lauderdale Improv",
            address=_FakeAddress(city="Fort Lauderdale", region="FL"),
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", side_effect=[[variant, exact], [exact]]) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 460
        assert mock_exec.call_count == 2

    def test_missing_city_skips_fuzzy_match_entirely(self):
        """When venue.address has no city, the (city, state) gate fails and
        the fuzzy-match pre-check is skipped — only the UPSERT runs.

        This is the structural guarantee that prevents brand-name false
        positives: without (city, state), there's no safe gate, so the
        normal name-keyed UPSERT path takes over."""
        venue = _FakeVenue(
            id="v-no-city",
            name="Some Venue",
            address=_FakeAddress(city=None, region="CA"),
        )
        new_row = _make_club_row(id=300, name="Some Venue", eventbrite_id="v-no-city")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[new_row]) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert mock_exec.call_count == 1
        # The single call must be the UPSERT, not the location lookup.
        called_sql = mock_exec.call_args_list[0][0][0]
        assert "INSERT INTO clubs" in called_sql

    def test_fuzzy_lookup_db_error_falls_through_to_upsert(self):
        """If the GET_CLUBS_BY_LOCATION query raises, the helper logs and returns
        None — the caller falls through to UPSERT so a transient lookup failure
        never blocks ingestion."""
        venue = _FakeVenue(
            id="v-tx",
            name="Existing Venue",
            address=_FakeAddress(city="Austin", region="TX"),
        )
        new_row = _make_club_row(id=400, name="Existing Venue", city="Austin", state="TX")

        handler = ClubHandler()
        with patch.object(
            handler,
            "execute_with_cursor",
            side_effect=[Exception("connection reset"), [new_row]],
        ) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 400
        assert mock_exec.call_count == 2


class TestUpsertForEventbriteVenueBrandNameSafety:
    """Criterion 6332 (TASK-1926): same-brand venues across distinct (city, state)
    must NOT collapse — a 'Laugh Factory' in San Diego is a real, distinct venue
    from 'Laugh Factory' in Hollywood.

    The (city, state) gate is the primary defense; the SQL query restricts the
    candidate set to one location, so cross-city matches are impossible by
    construction. These tests assert the gate works as designed.
    """

    def test_laugh_factory_san_diego_not_merged_with_hollywood(self):
        """A 'Laugh Factory' in (San Diego, CA) does NOT merge with the
        existing 'Laugh Factory' in (Hollywood, CA). The location query
        returns rows scoped to (San Diego, CA) only, so the Hollywood row
        is never even considered as a candidate."""
        venue = _FakeVenue(
            id="lf-sd",
            name="Laugh Factory",
            address=_FakeAddress(city="San Diego", region="CA"),
        )
        new_row = _make_club_row(
            id=170,
            name="Laugh Factory",
            city="San Diego",
            state="CA",
            eventbrite_id="lf-sd",
        )

        handler = ClubHandler()
        # First call (location lookup in San Diego CA) → empty (Hollywood row is
        # excluded by the WHERE clause). Second call (UPSERT) → inserts the SD row.
        with patch.object(
            handler,
            "execute_with_cursor",
            side_effect=[[], [new_row]],
        ) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 170
        assert result.name == "Laugh Factory"
        assert mock_exec.call_count == 2

        # The location query was scoped to (San Diego, CA), not (Hollywood, CA).
        location_call_params = mock_exec.call_args_list[0][0][1]
        assert location_call_params == ("San Diego", "CA")

    def test_same_city_distinct_brand_does_not_merge(self):
        """Two genuinely distinct brands sharing a city ('Comedy Cellar' vs
        'Comedy Cellar Village' in NY, NY) keep distinct rows. After
        normalization their core forms differ ('comedy cellar' vs
        'comedy cellar village') so exact-equality match fails and the
        new venue falls through to UPSERT."""
        existing_cellar = _make_club_row(
            id=10,
            name="Comedy Cellar",
            city="New York",
            state="NY",
        )
        venue = _FakeVenue(
            id="v-village",
            name="Comedy Cellar Village",
            address=_FakeAddress(city="New York", region="NY"),
        )
        village_row = _make_club_row(
            id=11,
            name="Comedy Cellar Village",
            city="New York",
            state="NY",
            eventbrite_id="v-village",
        )

        handler = ClubHandler()
        # Location lookup returns the Cellar row, but normalization produces
        # different cores — no merge. UPSERT then inserts Village as id=11.
        with patch.object(
            handler,
            "execute_with_cursor",
            side_effect=[[existing_cellar], [village_row]],
        ) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.id == 11
        assert result.name == "Comedy Cellar Village"
        assert mock_exec.call_count == 2


# ---------------------------------------------------------------------------
# Tests for upsert_for_seatengine_venue
# ---------------------------------------------------------------------------

def _make_seatengine_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume for SeatEngine clubs."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "https://testclub.com",
        "popularity": 0,
        "zip_code": "10001",
        "city": "New York",
        "state": "NY",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "seatengine",
        "scraping_url": "www.seatengine.com",
        "seatengine_id": "458",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="seatengine", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "platform_id": legacy["seatengine_id"],
    })


class TestUpsertForSeatEngineVenueHappyPath:
    """Valid venue dict inserts new club and returns Club with correct seatengine_id."""

    def test_returns_club_with_matching_seatengine_id(self):
        venue = {"id": 458, "name": "McGuire's Comedy Club", "address": "123 Main St", "zip": "10001", "website": ""}
        row = _make_seatengine_club_row(name="McGuire's Comedy Club", seatengine_id="458")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]):
            result = handler.upsert_for_seatengine_venue(venue)

        assert result is not None
        assert isinstance(result, Club)
        assert result.seatengine_id == "458"
        assert result.name == "McGuire's Comedy Club"

    def test_passes_correct_params_to_execute(self):
        """execute_with_cursor receives (name, address, website, scraping_url, venue_id, zip_code)."""
        venue = {"id": 457, "name": "Brokerage Comedy Club", "address": "200 Elm St", "zip": "11795", "website": "https://brokerage.com"}
        row = _make_seatengine_club_row(name="Brokerage Comedy Club", seatengine_id="457")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        mock_exec.assert_called_once()
        params = mock_exec.call_args[0][1]
        # New CTE shape:
        # (name, address, website, zip_code, city, state, venue_id, website-as-source_url)
        assert params[0] == "Brokerage Comedy Club"   # name
        assert params[1] == "200 Elm St"              # address
        assert params[2] == "https://brokerage.com"   # website
        assert params[3] == "11795"                   # zip_code
        assert params[6] == "457"                     # venue_id (seatengine_id, stringified)
        assert params[7] == "https://brokerage.com"   # source_url (mirrors website)

    def test_venue_id_stringified(self):
        """Numeric id in the dict is converted to string for the DB param."""
        venue = {"id": 325, "name": "Stress Factory", "address": "", "zip": "", "website": ""}
        row = _make_seatengine_club_row(name="Stress Factory", seatengine_id="325")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[6] == "325"

    def test_postal_code_fallback(self):
        """zip_code is read from 'postal_code' key when 'zip' is absent."""
        venue = {"id": 456, "name": "Governors Comedy Club", "address": "", "postal_code": "11520", "website": ""}
        row = _make_seatengine_club_row(name="Governors Comedy Club", seatengine_id="456", zip_code="11520")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] == "11520"  # zip_code (new CTE shape)


class TestUpsertForSeatEngineVenueConflict:
    """Conflict on name preserves existing scraper and seatengine_id via COALESCE."""

    def test_existing_club_retains_original_scraper(self):
        """When a club already exists with scraper='broadway', it stays 'broadway'."""
        venue = {"id": 999, "name": "Broadway Comedy Club", "address": "", "zip": "", "website": ""}
        existing_row = _make_seatengine_club_row(
            name="Broadway Comedy Club",
            scraper="broadway",
            seatengine_id="457",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_venue(venue)

        assert result is not None
        assert result.scraper == "broadway"

    def test_existing_club_retains_original_seatengine_id(self):
        """When a club already has a seatengine_id, it stays unchanged."""
        venue = {"id": 999, "name": "Broadway Comedy Club", "address": "", "zip": "", "website": ""}
        existing_row = _make_seatengine_club_row(
            name="Broadway Comedy Club",
            seatengine_id="457",
            scraper="broadway",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_venue(venue)

        assert result.seatengine_id == "457"

    def test_sql_uses_coalesce_for_seatengine_id(self):
        """SQL contract: UPSERT_CLUB_BY_SEATENGINE_VENUE must COALESCE the
        scraping_sources.seatengine_id (the SeatEngine venue id)."""
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPING_SOURCES" in sql
        assert "SEATENGINE_ID" in sql

    def test_sql_uses_coalesce_for_scraper(self):
        """SQL contract: UPSERT_CLUB_BY_SEATENGINE_VENUE must use COALESCE for scraper."""
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPER" in sql


class TestUpsertForSeatEngineVenueInvalidInput:
    """Missing/empty id or name returns None without raising."""

    def test_missing_id_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"name": "Some Club"})
        assert result is None

    def test_empty_id_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"id": "", "name": "Some Club"})
        assert result is None

    def test_missing_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"id": 123})
        assert result is None

    def test_empty_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"id": 123, "name": ""})
        assert result is None

    def test_no_db_call_on_invalid_input(self):
        """execute_with_cursor must NOT be called when input is invalid."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.upsert_for_seatengine_venue({"name": "No Id"})
            handler.upsert_for_seatengine_venue({"id": "", "name": "Empty Id"})
            handler.upsert_for_seatengine_venue({"id": 123, "name": None})

        mock_exec.assert_not_called()

    def test_none_returned_when_db_returns_empty(self):
        """If execute_with_cursor returns [], the method returns None."""
        venue = {"id": 458, "name": "Valid Club"}
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]):
            result = handler.upsert_for_seatengine_venue(venue)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: city/state extraction in Eventbrite upsert
# ---------------------------------------------------------------------------

class TestEventbriteVenueCityStateExtraction:
    """City and state are passed to execute_with_cursor from venue.address fields."""

    def test_city_and_state_extracted_from_address(self):
        venue = _FakeVenue(
            id="v1",
            name="Comedy Cellar",
            address=_FakeAddress(
                address_1="117 MacDougal St",
                city="New York",
                region="NY",
                postal_code="10012",
            ),
        )
        row = _make_club_row(name="Comedy Cellar", city="New York", state="NY")
        handler = ClubHandler()
        # side_effect: location lookup returns no candidate (skips TASK-1926
        # fuzzy match), then UPSERT runs and is the call we assert against.
        with patch.object(handler, "execute_with_cursor", side_effect=[[], [row]]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]  # last call = UPSERT
        # New CTE shape: (name, address, zip_code, city, state, venue_id)
        assert params[3] == "New York"  # city
        assert params[4] == "NY"        # state

    def test_city_state_none_when_no_address(self):
        venue = _FakeVenue(id="v2", name="Club No Address", address=None)
        row = _make_club_row(name="Club No Address", city=None, state=None)
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] is None  # city
        assert params[4] is None  # state


# ---------------------------------------------------------------------------
# Tests: city/state extraction in SeatEngine upsert
# ---------------------------------------------------------------------------

class TestSeatEngineVenueCityStateExtraction:
    """City and state are parsed from the address string for SeatEngine venues."""

    def test_city_and_state_parsed_from_address(self):
        venue = {"id": 100, "name": "Stress Factory", "address": "90 New St, Newark, NJ", "zip": "07102", "website": ""}
        row = _make_seatengine_club_row(name="Stress Factory", city="Newark", state="NJ")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, website, zip_code, city, state, venue_id, source_url)
        assert params[4] == "Newark"  # city
        assert params[5] == "NJ"      # state

    def test_city_state_none_when_address_unparseable(self):
        """No city/state when address has only one segment."""
        venue = {"id": 101, "name": "Mystery Club", "address": "NoCommasHere", "zip": "", "website": ""}
        row = _make_seatengine_club_row(name="Mystery Club", city=None, state=None)
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[4] is None  # city
        assert params[5] is None  # state


# ---------------------------------------------------------------------------
# Tests: city/state extraction in Ticketmaster upsert
# ---------------------------------------------------------------------------

def _make_ticketmaster_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume for Ticketmaster clubs."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "",
        "popularity": 0,
        "zip_code": "10001",
        "city": "New York",
        "state": "NY",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "live_nation",
        "scraping_url": "www.ticketmaster.com",
        "ticketmaster_id": "tm-001",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="ticketmaster", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "platform_id": legacy["ticketmaster_id"],
    })


class TestTicketmasterVenueCityStateExtraction:
    """City and state are read from structured API fields for Ticketmaster venues."""

    def test_city_and_state_extracted_from_structured_fields(self):
        venue = {
            "id": "tm-001",
            "name": "Radio City Music Hall",
            "address": {"line1": "1260 Avenue of the Americas"},
            "city": {"name": "New York"},
            "state": {"stateCode": "NY"},
            "postalCode": "10020",
            "timezone": "America/New_York",
        }
        row = _make_ticketmaster_club_row(name="Radio City Music Hall", city="New York", state="NY")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_ticketmaster_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, zip_code, city, state, timezone, venue_id)
        assert params[3] == "New York"  # city
        assert params[4] == "NY"        # state

    def test_city_state_none_when_absent_from_venue(self):
        """City and state default to None when not present in venue dict."""
        venue = {"id": "tm-002", "name": "Unknown Hall", "postalCode": ""}
        row = _make_ticketmaster_club_row(name="Unknown Hall", city=None, state=None)
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_ticketmaster_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] is None  # city
        assert params[4] is None  # state


# ---------------------------------------------------------------------------
# Tests: ClubHandler.backfill_city_state
# ---------------------------------------------------------------------------

def _make_backfill_club_row(**overrides):
    """Row for a club with city/state NULL."""
    defaults = {
        "id": 10,
        "name": "Test Club",
        "address": "117 MacDougal St, New York, NY",
        "website": "",
        "popularity": 0,
        "zip_code": "10012",
        "city": None,
        "state": None,
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "eventbrite",
        "scraping_url": "www.test.com",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="eventbrite", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "platform_id": None,
    })


class TestBackfillCityState:
    """ClubHandler.backfill_city_state populates city/state from address."""

    def test_updates_club_with_parseable_address(self):
        """A club whose address yields city/state is batch-updated."""
        row = _make_backfill_club_row(id=10, address="117 MacDougal St, New York, NY")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation", return_value=[{"id": 10}]) as mock_batch:
            result = handler.backfill_city_state()

        assert result == 1
        mock_batch.assert_called_once()
        updates = mock_batch.call_args[0][1]
        assert len(updates) == 1
        assert updates[0] == (10, "New York", "NY")

    def test_skips_club_with_unparseable_address(self):
        """A club with a single-segment address (no commas) is skipped."""
        row = _make_backfill_club_row(id=11, address="NoCommasHere")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation") as mock_batch:
            result = handler.backfill_city_state()

        assert result == 0
        mock_batch.assert_not_called()

    def test_returns_zero_when_no_clubs_need_update(self):
        """If no clubs have NULL city/state, returns 0 without calling batch op."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]), \
             patch.object(handler, "execute_batch_operation") as mock_batch:
            result = handler.backfill_city_state()

        assert result == 0
        mock_batch.assert_not_called()

    def test_multiple_clubs_batched_in_single_update(self):
        """All resolvable clubs are sent in one batch."""
        rows = [
            _make_backfill_club_row(id=1, address="208 W 23rd St, New York, NY"),
            _make_backfill_club_row(id=2, address="8001 Sunset Blvd, Los Angeles, CA"),
        ]
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=rows), \
             patch.object(handler, "execute_batch_operation", return_value=[{"id": 1}, {"id": 2}]) as mock_batch:
            result = handler.backfill_city_state()

        assert result == 2
        mock_batch.assert_called_once()
        updates = mock_batch.call_args[0][1]
        assert len(updates) == 2
        assert updates[0] == (1, "New York", "NY")
        assert updates[1] == (2, "Los Angeles", "CA")


# ---------------------------------------------------------------------------
# Tests: ClubHandler.refresh_club_total_shows
# ---------------------------------------------------------------------------

class TestRefreshClubTotalShows:
    """ClubHandler.refresh_club_total_shows executes the UPDATE_CLUB_TOTAL_SHOWS query."""

    def test_calls_execute_with_cursor_with_correct_query(self):
        """execute_with_cursor is called with UPDATE_CLUB_TOTAL_SHOWS and no extra params."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.refresh_club_total_shows()

        mock_exec.assert_called_once_with(ClubQueries.UPDATE_CLUB_TOTAL_SHOWS)

    def test_sql_updates_total_shows_column(self):
        """SQL contract: UPDATE_CLUB_TOTAL_SHOWS must reference total_shows and shows table."""
        sql = ClubQueries.UPDATE_CLUB_TOTAL_SHOWS.upper()
        assert "TOTAL_SHOWS" in sql
        assert "FROM SHOWS" in sql

    def test_reraises_on_db_error(self):
        """DB exceptions propagate out of refresh_club_total_shows."""
        import pytest
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", side_effect=RuntimeError("db error")):
            with pytest.raises(RuntimeError, match="db error"):
                handler.refresh_club_total_shows()


# ---------------------------------------------------------------------------
# Tests for upsert_for_seatengine_v3_venue
# ---------------------------------------------------------------------------

_V3_UUID = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"


def _make_seatengine_v3_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume for SeatEngine v3 clubs."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, Cambridge, MA",
        "website": "https://testclub.com",
        "popularity": 0,
        "zip_code": "02139",
        "city": "Cambridge",
        "state": "MA",
        "phone_number": "",
        "timezone": None,
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "seatengine_v3",
        "scraping_url": f"https://v-{_V3_UUID}.seatengine.net",
        "seatengine_id": _V3_UUID,
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="seatengine_v3", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "platform_id": legacy["seatengine_id"],
    })


class TestUpsertForSeatEngineV3VenueHappyPath:
    """Valid venue dict inserts new club and returns Club with correct UUID."""

    def test_returns_club_with_matching_seatengine_id(self):
        venue = {"uuid": _V3_UUID, "name": "The Comedy Studio", "address": "1236 Mass Ave, Cambridge, MA", "website": "https://thecomedystudio.com", "zipCode": "02139"}
        row = _make_seatengine_v3_club_row(name="The Comedy Studio")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]):
            result = handler.upsert_for_seatengine_v3_venue(venue)

        assert result is not None
        assert isinstance(result, Club)
        assert result.seatengine_id == _V3_UUID
        assert result.name == "The Comedy Studio"

    def test_scraping_url_constructed_from_uuid(self):
        """source_url param must be https://v-{uuid}.seatengine.net."""
        venue = {"uuid": _V3_UUID, "name": "The Comedy Studio", "address": ""}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, website, zip_code, city, state, venue_uuid, source_url)
        assert params[7] == f"https://v-{_V3_UUID}.seatengine.net"

    def test_venue_uuid_stored_as_seatengine_id(self):
        """UUID is passed as the scraping_sources.seatengine_v3_id column value."""
        venue = {"uuid": _V3_UUID, "name": "The Comedy Studio", "address": ""}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[6] == _V3_UUID

    def test_zip_code_from_zipCode_key(self):
        """zipCode (camelCase) is the primary zip_code source."""
        venue = {"uuid": _V3_UUID, "name": "Club", "address": "", "zipCode": "02139"}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] == "02139"  # zip_code (new CTE shape)

    def test_zip_code_fallback_to_zip_key(self):
        """Falls back to 'zip' key when 'zipCode' is absent."""
        venue = {"uuid": _V3_UUID, "name": "Club", "address": "", "zip": "02139"}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] == "02139"  # zip_code (new CTE shape)

    def test_explicit_city_state_from_api_take_priority(self):
        """city/state from the venue dict are used before address parsing."""
        venue = {
            "uuid": _V3_UUID,
            "name": "Club",
            "address": "1 Broadway, New York, NY",
            "city": "Cambridge",
            "state": "MA",
        }

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[4] == "Cambridge"  # city (new CTE shape)
        assert params[5] == "MA"         # state


class TestUpsertForSeatEngineV3VenueConflict:
    """Conflict on name preserves existing values via COALESCE."""

    def test_existing_club_retains_original_scraper(self):
        venue = {"uuid": _V3_UUID, "name": "Broadway Comedy Club", "address": ""}
        existing_row = _make_seatengine_v3_club_row(name="Broadway Comedy Club", scraper="broadway")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_v3_venue(venue)

        assert result is not None
        assert result.scraper == "broadway"

    def test_existing_club_retains_original_seatengine_id(self):
        venue = {"uuid": _V3_UUID, "name": "Broadway Comedy Club", "address": ""}
        existing_row = _make_seatengine_v3_club_row(seatengine_id="original-uuid")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_v3_venue(venue)

        assert result.seatengine_id == "original-uuid"

    def test_sql_uses_coalesce_for_seatengine_id(self):
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPING_SOURCES" in sql
        assert "SEATENGINE_V3_ID" in sql

    def test_sql_uses_coalesce_for_scraper(self):
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPER_KEY" in sql

    def test_sql_uses_coalesce_for_scraping_url(self):
        """source_url (the v-{uuid}.seatengine.net URL) must be preserved for
        existing clubs via COALESCE."""
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE.upper()
        assert "SOURCE_URL" in sql


class TestUpsertForSeatEngineV3VenueInvalidInput:
    """Missing/empty uuid or name returns None without raising."""

    def test_missing_uuid_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"name": "Some Club"})
        assert result is None

    def test_empty_uuid_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"uuid": "", "name": "Some Club"})
        assert result is None

    def test_missing_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"uuid": _V3_UUID})
        assert result is None

    def test_empty_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"uuid": _V3_UUID, "name": ""})
        assert result is None

    def test_no_db_call_on_invalid_input(self):
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.upsert_for_seatengine_v3_venue({"name": "No UUID"})
            handler.upsert_for_seatengine_v3_venue({"uuid": "", "name": "Empty UUID"})
            handler.upsert_for_seatengine_v3_venue({"uuid": _V3_UUID, "name": None})
        mock_exec.assert_not_called()

    def test_none_returned_when_db_returns_empty(self):
        venue = {"uuid": _V3_UUID, "name": "Valid Club"}
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]):
            result = handler.upsert_for_seatengine_v3_venue(venue)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: is_junk_venue filter across upsert paths (TASK-885)
# ---------------------------------------------------------------------------

_JUNK_FILTER = "laughtrack.utilities.domain.club.quality_filter.is_junk_venue"


class TestUpsertForEventbriteVenueJunkFilter:
    """is_junk_venue returning True causes upsert_for_eventbrite_venue to return None."""

    def test_junk_name_returns_none(self):
        venue = _FakeVenue(id="v-junk", name="Demo Comedy Club")
        handler = ClubHandler()
        with patch(_JUNK_FILTER, return_value=True) as mock_filter, \
             patch.object(handler, "execute_with_cursor") as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is None
        mock_filter.assert_called_once_with("Demo Comedy Club")
        mock_exec.assert_not_called()


class TestUpsertForTicketmasterVenueJunkFilter:
    """is_junk_venue returning True causes upsert_for_ticketmaster_venue to return None."""

    def test_junk_name_returns_none(self):
        venue = {"id": "tm-junk", "name": "Demo Comedy Club"}
        handler = ClubHandler()
        with patch(_JUNK_FILTER, return_value=True) as mock_filter, \
             patch.object(handler, "execute_with_cursor") as mock_exec:
            result = handler.upsert_for_ticketmaster_venue(venue)

        assert result is None
        mock_filter.assert_called_once_with("Demo Comedy Club")
        mock_exec.assert_not_called()


class TestUpsertForTourDateVenueJunkFilter:
    """is_junk_venue returning True causes upsert_for_tour_date_venue to return None."""

    def test_junk_name_returns_none(self):
        venue = {"name": "Demo Comedy Club"}
        handler = ClubHandler()
        with patch(_JUNK_FILTER, return_value=True) as mock_filter, \
             patch.object(handler, "execute_with_cursor") as mock_exec:
            result = handler.upsert_for_tour_date_venue(venue)

        assert result is None
        mock_filter.assert_called_once_with("Demo Comedy Club")
        mock_exec.assert_not_called()
