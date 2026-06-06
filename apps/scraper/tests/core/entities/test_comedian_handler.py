"""
Unit tests for ComedianHandler.

Covers:
- insert_comedians: DO NOTHING on conflict contract (stub names never overwrite existing data)
- _fetch_recency_scores: happy path, empty results, exception propagation
- update_comedian_popularity: recency map applied; absent comedians default to 0.0
"""

import sys
from unittest.mock import MagicMock

import pytest
from unittest.mock import patch
from _entities_test_helpers import _load_module


# ---------------------------------------------------------------------------
# Load source modules directly from file, bypassing package __init__.py
# chains that require a live DB environment.
# ---------------------------------------------------------------------------

# Load comedian model directly (bypasses comedian __init__.py which pulls in handler)
_comedian_model_mod = _load_module("src/laughtrack/core/entities/comedian/model.py",
                                   "laughtrack.core.entities.comedian.model_direct")
Comedian = _comedian_model_mod.Comedian

# Load ComedianQueries directly (no deps)
_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_direct")
ComedianQueries = _comedian_queries_mod.ComedianQueries

# Register model and queries under canonical import paths so handler.py relative imports resolve
sys.modules.setdefault("laughtrack.core.entities.comedian.model", _comedian_model_mod)
sys.modules.setdefault("sql.comedian_queries", _comedian_queries_mod)

# Load ComedianHandler
_comedian_handler_mod = _load_module(
    "src/laughtrack/core/entities/comedian/handler.py",
    "laughtrack.core.entities.comedian.handler_direct",
)
ComedianHandler = _comedian_handler_mod.ComedianHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid_for(name: str) -> str:
    """Replicate the deterministic UUID logic for test assertions."""
    import hashlib
    normalized = name.lower().strip()
    return str(hashlib.md5(normalized.encode()).hexdigest())


def _make_stub(name: str) -> Comedian:
    """Create a name-only comedian stub as produced by lineup extraction."""
    c = Comedian.__new__(Comedian)
    # Set defaults matching the dataclass definition
    c.name = name
    c.uuid = None
    c.sold_out_shows = 0
    c.total_shows = 0
    c.instagram_followers = None
    c.tiktok_followers = None
    c.youtube_followers = None
    c.instagram_account = None
    c.tiktok_account = None
    c.youtube_account = None
    c.website = None
    c.linktree = None
    c.parent_comedian_id = None
    c.recency_score = 0.0
    return c


def _make_full_comedian(name: str) -> Comedian:
    """Create a comedian with social/follower data."""
    c = _make_stub(name)
    c.instagram_followers = 50_000
    c.tiktok_followers = 120_000
    c.sold_out_shows = 3
    c.total_shows = 10
    return c


# ---------------------------------------------------------------------------
# SQL-level contract
# ---------------------------------------------------------------------------

class TestBatchAddComediansSql:
    def test_uses_do_nothing_on_conflict(self):
        """Regression guard: BATCH_ADD_COMEDIANS must use DO NOTHING, not DO UPDATE."""
        sql = ComedianQueries.BATCH_ADD_COMEDIANS.upper()
        assert "DO NOTHING" in sql, "Expected ON CONFLICT DO NOTHING in BATCH_ADD_COMEDIANS"
        assert "DO UPDATE" not in sql, "DO UPDATE would overwrite existing comedian data"

    def test_inserts_only_base_fields(self):
        """The INSERT column list must not include social/follower fields."""
        import re
        match = re.search(r"INSERT INTO comedians\s*\(([^)]+)\)", ComedianQueries.BATCH_ADD_COMEDIANS, re.I)
        assert match, "Could not find INSERT column list"
        cols = [c.strip().lower() for c in match.group(1).split(",")]
        for social_field in ("instagram_followers", "tiktok_followers", "youtube_followers",
                             "instagram_account", "tiktok_account", "youtube_account"):
            assert social_field not in cols, (
                f"Social field '{social_field}' must not be in INSERT to avoid overwriting existing data"
            )


# ---------------------------------------------------------------------------
# Model-level contract
# ---------------------------------------------------------------------------

class TestComedianInsertTuple:
    def test_to_insert_tuple_excludes_social_fields(self):
        """to_insert_tuple() must only include (uuid, name, sold_out_shows, total_shows)."""
        comedian = _make_full_comedian("Amy Schumer")
        comedian.uuid = "test-uuid-123"
        t = comedian.to_insert_tuple()
        assert len(t) == 4
        assert t[0] == comedian.uuid
        assert t[1] == comedian.name
        assert t[2] == comedian.sold_out_shows
        assert t[3] == comedian.total_shows

    def test_stub_to_insert_tuple_has_zero_show_counts(self):
        """Stubs from lineup extraction have 0 show counts, so any additive update would be a no-op."""
        stub = _make_stub("Chris Rock")
        stub.uuid = "some-uuid"
        t = stub.to_insert_tuple()
        assert t[2] == 0, "sold_out_shows should be 0 for name-only stubs"
        assert t[3] == 0, "total_shows should be 0 for name-only stubs"

    def test_social_fields_not_in_insert_tuple(self):
        """Confirm social fields present on the model are excluded from to_insert_tuple."""
        comedian = _make_full_comedian("Dave Chappelle")
        comedian.uuid = "uuid-456"
        t = comedian.to_insert_tuple()
        # instagram_followers=50000 must NOT appear in the tuple
        assert comedian.instagram_followers not in t
        assert comedian.tiktok_followers not in t


# ---------------------------------------------------------------------------
# Helpers — ComedianHandler construction
# ---------------------------------------------------------------------------

def _make_handler() -> ComedianHandler:
    """Return a ComedianHandler with all DB methods replaced by MagicMocks."""
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock()
    handler.execute_batch_operation = MagicMock()
    return handler


# ---------------------------------------------------------------------------
# _fetch_recency_scores
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# BATCH_UPDATE_COMEDIAN_SHOW_COUNTS — SQL contract
# ---------------------------------------------------------------------------

class TestBatchUpdateComedianShowCountsSql:
    def test_query_updates_both_columns(self):
        """Query must SET both total_shows and sold_out_shows."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "total_shows" in sql
        assert "sold_out_shows" in sql

    def test_query_uses_any_param_not_show_id_filter(self):
        """Query must use ANY(%s) for comedian_id filtering, not a show_id whitelist."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS
        assert "ANY(%s)" in sql, "Expected ANY(%s) for comedian_id array parameter"
        assert "show_id = ANY" not in sql.lower(), (
            "Query must not filter by show_id — must aggregate across all shows"
        )

    def test_query_aggregates_from_lineup_items(self):
        """Query must join lineup_items to count per-comedian show totals."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "lineup_items" in sql

    def test_query_uses_bool_and_for_sold_out_detection(self):
        """BOOL_AND(sold_out) is the correct aggregate for all-tickets-sold-out."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "bool_and" in sql, "Expected BOOL_AND to determine show-level sold-out status"

    def test_query_bounds_tickets_aggregation_per_show(self):
        """Regression guard for TASK-2544: the tickets BOOL_AND must NOT be
        materialized over the whole tickets table.

        The prior shape was a top-level subquery `(SELECT show_id, BOOL_AND(sold_out)
        FROM tickets GROUP BY show_id)` that Postgres aggregated over the entire
        tickets table on every call, because the outer comedian_id filter
        cannot push into an aggregated subquery. As tickets scaled, that single
        statement crossed Neon's 30s statement_timeout mid-nightly.

        The fix uses LEFT JOIN LATERAL with a correlated `WHERE t.show_id = li.show_id`
        so BOOL_AND only runs for shows in the targeted comedians' lineups.
        Don't reintroduce the unbounded GROUP BY form.
        """
        import re
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        # LATERAL is the contract — the correlated subquery is what bounds the
        # tickets aggregation to relevant shows only.
        assert "lateral" in sql, "Expected LEFT JOIN LATERAL to bound tickets aggregation"
        # The correlated predicate is what makes the LATERAL bounded; a LATERAL
        # without it would still scan all tickets per row.
        assert "t.show_id = li.show_id" in sql, (
            "LATERAL subquery must correlate on show_id to use the tickets index"
        )
        # The exact prior offending shape: a non-correlated `FROM tickets GROUP BY show_id`.
        # Normalize whitespace first so reformatting the SQL string (dedent, line
        # rewrap) cannot silently turn this anti-pattern check into a no-op.
        normalized = re.sub(r"\s+", " ", sql)
        assert "from tickets group by show_id" not in normalized, (
            "Reintroduced unbounded tickets GROUP BY — would scan all tickets every call"
        )


class TestUpdateComedianTourIdsSql:
    def test_query_only_fills_missing_platform_ids(self):
        """Tour ID discovery must not overwrite previously verified platform IDs."""
        sql = ComedianQueries.UPDATE_COMEDIAN_TOUR_IDS.lower()

        assert "case" in sql
        assert "nullif(btrim(coalesce(c.bandsintown_id, '')), '') is null" in sql
        assert "nullif(btrim(coalesce(c.songkick_id, '')), '') is null" in sql
        assert "coalesce(v.bandsintown_id, c.bandsintown_id)" not in sql
        assert "coalesce(v.songkick_id, c.songkick_id)" not in sql


# ---------------------------------------------------------------------------
# _refresh_comedian_show_counts
# ---------------------------------------------------------------------------

class TestRefreshComedianShowCounts:
    def test_single_chunk_passes_uuids_to_execute_with_cursor(self):
        """A list smaller than the chunk size produces exactly one statement."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None

        handler._refresh_comedian_show_counts(["uuid-1", "uuid-2"])

        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS,
            (["uuid-1", "uuid-2"],),
        )

    def test_empty_input_does_not_query(self):
        """No UUIDs → no statement issued (avoids ANY(empty array) overhead)."""
        handler = _make_handler()
        handler._refresh_comedian_show_counts([])
        handler.execute_with_cursor.assert_not_called()

    def test_large_input_is_chunked(self):
        """Regression guard for TASK-2544: _refresh_comedian_show_counts must
        chunk its UUID list so a single nightly batch can never issue one giant
        statement that crosses Neon's 30s statement_timeout. The LATERAL
        rewrite is the primary defense; this caller-side chunk is the
        secondary defense.
        """
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None

        chunk_size = ComedianHandler._SHOW_COUNTS_REFRESH_CHUNK_SIZE
        # Build an input larger than the chunk size so chunking must fire.
        uuids = [f"uuid-{i}" for i in range(chunk_size * 2 + 5)]

        handler._refresh_comedian_show_counts(uuids)

        # Expect ceil(len(uuids) / chunk_size) calls, each with a chunk of <= chunk_size.
        expected_calls = (len(uuids) + chunk_size - 1) // chunk_size
        assert handler.execute_with_cursor.call_count == expected_calls
        for call in handler.execute_with_cursor.call_args_list:
            args, _ = call
            query, params = args
            assert query == ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS
            (chunk,) = params
            assert len(chunk) <= chunk_size

        # And every UUID must appear in exactly one chunk — chunking can't drop or duplicate.
        seen = [
            uuid
            for call in handler.execute_with_cursor.call_args_list
            for uuid in call.args[1][0]
        ]
        assert seen == uuids

    def test_chunk_size_is_bounded(self):
        """The chunk-size constant is meaningful: bound it so future edits
        can't silently set it back to thousands and reintroduce the timeout.
        """
        assert 0 < ComedianHandler._SHOW_COUNTS_REFRESH_CHUNK_SIZE <= 500

    def test_exception_from_execute_with_cursor_propagates(self):
        """A DB error in execute_with_cursor bubbles up from _refresh_comedian_show_counts."""
        handler = _make_handler()
        handler.execute_with_cursor.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError, match="DB error"):
            handler._refresh_comedian_show_counts(["uuid-1"])


# ---------------------------------------------------------------------------
# update_comedian_popularity — show count refresh integration
# ---------------------------------------------------------------------------

class TestUpdateComedianPopularityRefreshShowCounts:
    def _make_comedian(self, uuid: str) -> Comedian:
        c = _make_stub(f"Comedian-{uuid}")
        c.uuid = uuid
        return c

    def _setup_handler(self, uuids, comedians, recency_map):
        handler = _make_handler()
        handler._get_comedian_uuids = MagicMock(return_value=uuids)
        handler._fetch_comedian_details = MagicMock(return_value=comedians)
        handler._fetch_recency_scores = MagicMock(return_value=recency_map)
        handler._refresh_comedian_show_counts = MagicMock()
        handler.execute_batch_operation = MagicMock(return_value=[{"id": "ok"}])
        return handler

    def test_refresh_show_counts_called_before_fetch_details(self):
        """_refresh_comedian_show_counts must be called before _fetch_comedian_details."""
        uuids = ["uuid-A"]
        comedians = [self._make_comedian("uuid-A")]
        handler = self._setup_handler(uuids, comedians, {})

        call_order = []
        handler._refresh_comedian_show_counts.side_effect = lambda *a, **kw: call_order.append("refresh")
        handler._fetch_comedian_details.side_effect = lambda *a, **kw: (call_order.append("fetch"), comedians)[1]

        handler.update_comedian_popularity()

        assert call_order == ["refresh", "fetch"], (
            "show counts must be refreshed before comedian details are fetched"
        )

    def test_refresh_show_counts_receives_target_uuids(self):
        """_refresh_comedian_show_counts is called with the resolved target UUIDs."""
        uuids = ["uuid-1", "uuid-2"]
        comedians = [self._make_comedian(u) for u in uuids]
        handler = self._setup_handler(uuids, comedians, {})

        handler.update_comedian_popularity()

        handler._refresh_comedian_show_counts.assert_called_once_with(uuids)

    def test_exception_from_refresh_show_counts_propagates(self):
        """A DB error in _refresh_comedian_show_counts bubbles up from update_comedian_popularity."""
        uuids = ["uuid-1"]
        comedians = [self._make_comedian("uuid-1")]
        handler = self._setup_handler(uuids, comedians, {})
        handler._refresh_comedian_show_counts.side_effect = RuntimeError("show count DB error")

        with pytest.raises(RuntimeError, match="show count DB error"):
            handler.update_comedian_popularity()


class TestFetchRecencyScores:
    def test_happy_path_returns_dict_of_float_scores(self):
        """execute_with_cursor returning rows → dict maps comedian_id to float recency_score."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"comedian_id": "uuid-1", "recency_score": 0.85},
            {"comedian_id": "uuid-2", "recency_score": 0.40},
        ]

        result = handler._fetch_recency_scores(["uuid-1", "uuid-2"])

        assert result == {"uuid-1": 0.85, "uuid-2": 0.40}
        assert all(isinstance(v, float) for v in result.values())

    def test_none_result_returns_empty_dict(self):
        """When execute_with_cursor returns None, result is an empty dict (no KeyError)."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None

        result = handler._fetch_recency_scores(["uuid-1"])

        assert result == {}

    def test_exception_propagates_from_execute_with_cursor(self):
        """A DB error raised by execute_with_cursor bubbles up unchanged."""
        handler = _make_handler()
        handler.execute_with_cursor.side_effect = RuntimeError("DB connection lost")

        with pytest.raises(RuntimeError, match="DB connection lost"):
            handler._fetch_recency_scores(["uuid-1"])


# ---------------------------------------------------------------------------
# update_comedian_popularity — recency map integration
# ---------------------------------------------------------------------------

class TestUpdateComedianPopularity:
    def _make_comedian(self, uuid: str) -> Comedian:
        c = _make_stub(f"Comedian-{uuid}")
        c.uuid = uuid
        return c

    def _setup_handler(self, uuids, comedians, recency_map):
        """Return a handler with all helpers stubbed out."""
        handler = _make_handler()
        handler._get_comedian_uuids = MagicMock(return_value=uuids)
        handler._fetch_comedian_details = MagicMock(return_value=comedians)
        handler._fetch_recency_scores = MagicMock(return_value=recency_map)
        # execute_batch_operation must return truthy to pass the "no comedians updated" guard
        handler.execute_batch_operation = MagicMock(return_value=[{"id": "ok"}])
        return handler

    def test_recency_score_applied_to_comedian_from_map(self):
        """Comedians present in the recency map get recency_score set correctly."""
        uuids = ["uuid-A", "uuid-B"]
        comedians = [self._make_comedian("uuid-A"), self._make_comedian("uuid-B")]
        handler = self._setup_handler(uuids, comedians, {"uuid-A": 0.9, "uuid-B": 0.3})

        handler.update_comedian_popularity()

        assert comedians[0].recency_score == 0.9
        assert comedians[1].recency_score == 0.3

    def test_comedian_absent_from_recency_map_defaults_to_zero(self):
        """Comedians not in the recency map keep recency_score=0.0."""
        uuids = ["uuid-X", "uuid-Y"]
        comedians = [self._make_comedian("uuid-X"), self._make_comedian("uuid-Y")]
        # Only uuid-X has an entry; uuid-Y is absent
        handler = self._setup_handler(uuids, comedians, {"uuid-X": 0.7})

        handler.update_comedian_popularity()

        assert comedians[0].recency_score == 0.7
        assert comedians[1].recency_score == 0.0

    def test_exception_from_fetch_recency_scores_propagates(self):
        """A DB error in _fetch_recency_scores bubbles up from update_comedian_popularity."""
        uuids = ["uuid-1"]
        comedians = [self._make_comedian("uuid-1")]
        handler = self._setup_handler(uuids, comedians, {})
        handler._fetch_recency_scores.side_effect = RuntimeError("recency DB error")

        with pytest.raises(RuntimeError, match="recency DB error"):
            handler.update_comedian_popularity()


# ---------------------------------------------------------------------------
# _get_comedian_uuids — UUID-not-found scenarios
# ---------------------------------------------------------------------------

class TestGetComedianUuids:
    """Tests for _get_comedian_uuids, covering duplicate deduplication and missing UUID filtering."""

    def _make_handler_with_db(self, db_uuids: list) -> ComedianHandler:
        """Return a handler whose execute_with_cursor simulates GET_TARGET_COMEDIAN_IDS."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [{"uuid": u} for u in db_uuids]
        return handler

    def test_duplicate_input_uuids_no_false_positive_warning(self):
        """Duplicate UUIDs in the input list must NOT trigger a missing-UUID warning.

        collect_comedian_uuids() returns duplicates when the same comedian appears in
        multiple shows. Before the fix, len(found) != len(input) because the DB returns
        each UUID once while the input list contained repeats.
        """
        # uuid-A appears 3 times (same comedian in 3 shows), uuid-B once
        comedian_ids = ["uuid-A", "uuid-A", "uuid-A", "uuid-B"]
        # DB contains both — no UUIDs are genuinely missing
        handler = self._make_handler_with_db(["uuid-A", "uuid-B"])

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._get_comedian_uuids(comedian_ids)

        # Both unique UUIDs returned; no warning emitted
        assert set(result) == {"uuid-A", "uuid-B"}
        mock_logger.warn.assert_not_called()

    def test_genuine_missing_uuid_is_silently_filtered(self):
        """When a UUID genuinely doesn't exist in the DB, return only the DB-backed UUIDs."""
        comedian_ids = ["uuid-exists", "uuid-missing"]
        handler = self._make_handler_with_db(["uuid-exists"])  # uuid-missing not in DB

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._get_comedian_uuids(comedian_ids)

        # Only the found UUID is returned
        assert result == ["uuid-exists"]
        mock_logger.warn.assert_not_called()

    def test_duplicate_with_genuine_missing_filters_missing_without_warning(self):
        """Duplicate input + 1 missing UUID should return existing UUIDs without warning noise."""
        # uuid-A duplicated, uuid-ghost is genuinely absent from DB
        comedian_ids = ["uuid-A", "uuid-A", "uuid-ghost"]
        handler = self._make_handler_with_db(["uuid-A"])  # uuid-ghost not in DB

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._get_comedian_uuids(comedian_ids)

        assert result == ["uuid-A"]
        mock_logger.warn.assert_not_called()

    def test_no_comedian_ids_returns_all_from_db(self):
        """Passing None (no IDs) delegates to get_all_comedian_uuids path."""
        handler = _make_handler()
        handler.get_all_comedian_uuids = MagicMock(return_value=["uuid-X", "uuid-Y"])

        result = handler._get_comedian_uuids(None)

        assert result == ["uuid-X", "uuid-Y"]
        handler.execute_with_cursor.assert_not_called()

    def test_all_missing_uuids_still_raise_without_warning(self):
        """When all UUIDs are absent, preserve the hard failure but do not emit warning noise."""
        comedian_ids = ["uuid-absent"]
        handler = self._make_handler_with_db([])  # no UUIDs in DB

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            with pytest.raises(ValueError, match="No matching comedians found"):
                handler._get_comedian_uuids(comedian_ids)

        # When ALL UUIDs are missing, ValueError is raised (not a warning)
        mock_logger.warn.assert_not_called()


# ---------------------------------------------------------------------------
# _filter_false_positive_comedians
# ---------------------------------------------------------------------------

class TestFilterFalsePositiveComedians:
    """Tests for ComedianHandler._filter_false_positive_comedians.

    Verifies that placeholder names, open-mic substrings, structural keywords,
    decoration patterns, pipe characters, and length extremes are all rejected
    with a WARN log, while real comedian names pass through.
    """

    def test_real_name_passes_through(self):
        handler = _make_handler()
        comedians = [_make_stub("Dave Chappelle")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert len(result) == 1
        assert result[0].name == "Dave Chappelle"
        mock_logger.warn.assert_not_called()

    def test_placeholder_name_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("TBA")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()
        assert "TBA" in mock_logger.warn.call_args[0][0]

    def test_open_mic_substring_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("KRACKPOTS Open Mic Night")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()

    def test_structural_keyword_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("Comedy Showcase")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()

    def test_decoration_pattern_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("***Special Event***")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()

    def test_pipe_in_name_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("Comedy | Standup")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()

    def test_name_gt_60_chars_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("A" * 61)]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()

    def test_short_name_rejected(self):
        handler = _make_handler()
        comedians = [_make_stub("Al")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert result == []
        mock_logger.warn.assert_called_once()

    def test_mixed_list_filters_only_false_positives(self):
        handler = _make_handler()
        comedians = [
            _make_stub("Dave Chappelle"),
            _make_stub("TBA"),
            _make_stub("Amy Schumer"),
            _make_stub("Comedy Showcase"),
        ]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians(comedians)
        assert [c.name for c in result] == ["Dave Chappelle", "Amy Schumer"]
        assert mock_logger.warn.call_count == 2

    def test_warn_log_includes_detection_reason(self):
        """Logged WARN message must include the detection reason for diagnosability."""
        handler = _make_handler()
        comedians = [_make_stub("Comedy Showcase")]
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            handler._filter_false_positive_comedians(comedians)
        warn_msg = mock_logger.warn.call_args[0][0]
        # Should contain the name and the reason
        assert "Comedy Showcase" in warn_msg
        assert "structural_keyword" in warn_msg

    def test_empty_input_returns_empty(self):
        handler = _make_handler()
        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            result = handler._filter_false_positive_comedians([])
        assert result == []
        mock_logger.warn.assert_not_called()


# ---------------------------------------------------------------------------
# _filter_denied_comedians
# ---------------------------------------------------------------------------

class TestFilterDeniedComedians:
    def test_internal_nbsp_matches_space_normalized_deny_list_name(self):
        handler = _make_handler()
        blocked = _make_stub("🔥👀\u00a0TEASE ME TUESDAYS…👀🔥")
        allowed = _make_stub("Dave Chappelle")
        # Both stages query with the same normalized names; the deny-list
        # stage returns the suppressed name. The visible-comedian stage
        # returns empty (the row was never ingested as a comedian).
        handler.execute_with_cursor.side_effect = [
            [],
            [{"name": "🔥👀 TEASE ME TUESDAYS…👀🔥"}],
        ]

        with patch.object(_comedian_handler_mod, "Logger"):
            result = handler._filter_denied_comedians([blocked, allowed])

        assert result == [allowed]
        # Second (deny-list) call carries the same normalized name set the
        # original test asserted against — the contract did not change.
        deny_call = handler.execute_with_cursor.call_args_list[1][0]
        assert deny_call[0] == ComedianQueries.GET_DENIED_NAMES
        assert deny_call[1] == (["🔥👀 tease me tuesdays…👀🔥", "dave chappelle"],)

    def test_insert_comedians_skips_hidden(self):
        """Names matching a comedians row with visible=false are filtered at
        stage 1 (GET_HIDDEN_COMEDIAN_NAMES), before the deny-list stage is
        consulted. Validates the two-stage check per
        docs/comedian-visible-consolidation.md Decision 1.
        """
        handler = _make_handler()
        hidden = _make_stub("HiddenComedian")
        allowed = _make_stub("AllowedComedian")
        # Stage 1 returns the hidden name; stage 2 returns nothing. Both
        # stages always run so the deny-list check is not short-circuited.
        handler.execute_with_cursor.side_effect = [
            [{"name": "HiddenComedian"}],
            [],
        ]

        with patch.object(_comedian_handler_mod, "Logger"):
            result = handler._filter_denied_comedians([hidden, allowed])

        assert result == [allowed]
        assert handler.execute_with_cursor.call_count == 2
        hidden_call = handler.execute_with_cursor.call_args_list[0][0]
        assert hidden_call[0] == ComedianQueries.GET_HIDDEN_COMEDIAN_NAMES
        assert hidden_call[1] == (["hiddencomedian", "allowedcomedian"],)
        deny_call = handler.execute_with_cursor.call_args_list[1][0]
        assert deny_call[0] == ComedianQueries.GET_DENIED_NAMES

    def test_hidden_query_failure_falls_through_to_deny_list(self):
        """Stage 1 failure (e.g. visible column not yet deployed) must not
        prevent stage 2 from running. Regression guard for the rollout
        window when the scraper ships before the Prisma migration.
        """
        handler = _make_handler()
        denied = _make_stub("DeniedName")
        allowed = _make_stub("AllowedName")
        handler.execute_with_cursor.side_effect = [
            RuntimeError("column \"visible\" does not exist"),
            [{"name": "DeniedName"}],
        ]

        with patch.object(_comedian_handler_mod, "Logger"):
            result = handler._filter_denied_comedians([denied, allowed])

        assert result == [allowed]
        assert handler.execute_with_cursor.call_count == 2
