"""
Unit tests for the social follower refresh pipeline on ComedianHandler.

Covers:
- _get_comedians_with_youtube_accounts: happy path, empty result
- _fetch_youtube_subscriber_counts: channel-ID path, handle path, mixed,
  hiddenSubscriberCount (missing), API error isolation per handle
- refresh_youtube_followers: end-to-end integration with mocked helpers,
  empty-accounts short-circuit, batch persistence call
- SQL contract: UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS only sets youtube_followers
- SQL contract: GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT filters NULL / empty string
"""

import sys
from unittest.mock import MagicMock, patch, call

import pytest
import requests as _requests
from _entities_test_helpers import _load_module


# ---------------------------------------------------------------------------
# Module loading (shared helpers and stubs are set up in conftest.py)
# ---------------------------------------------------------------------------

# Comedian model
_comedian_model_mod = _load_module(
    "src/laughtrack/core/entities/comedian/model.py",
    "laughtrack.core.entities.comedian.model_direct",
)
Comedian = _comedian_model_mod.Comedian

# ComedianQueries
_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_direct")
ComedianQueries = _comedian_queries_mod.ComedianQueries

# Register under canonical paths
sys.modules.setdefault("laughtrack.core.entities.comedian.model", _comedian_model_mod)
sys.modules.setdefault("sql.comedian_queries", _comedian_queries_mod)

# Load ComedianHandler (contains the new social refresh methods)
_comedian_handler_mod = _load_module(
    "src/laughtrack/core/entities/comedian/handler.py",
    "laughtrack.core.entities.comedian.handler_social_test",
)
ComedianHandler = _comedian_handler_mod.ComedianHandler
# Disable per-request sleep delay so tests run at full speed
_comedian_handler_mod._SOCIAL_REQUEST_DELAY_S = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_handler() -> ComedianHandler:
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock()
    handler.execute_batch_operation = MagicMock()
    return handler


def _yt_response(items: list) -> dict:
    """Minimal YouTube Data API v3 channels response envelope."""
    return {"kind": "youtube#channelListResponse", "items": items}


def _yt_item(channel_id: str, subscriber_count: int) -> dict:
    return {
        "kind": "youtube#channel",
        "id": channel_id,
        "statistics": {"subscriberCount": str(subscriber_count)},
    }


# ---------------------------------------------------------------------------
# SQL contract tests
# ---------------------------------------------------------------------------

class TestYouTubeFollowersSqlContract:
    def test_update_query_only_sets_youtube_followers(self):
        """UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS must SET only youtube_followers."""
        sql = ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS.lower()
        # Must update youtube_followers
        assert "youtube_followers" in sql
        # Must NOT touch instagram or tiktok columns
        assert "instagram_followers" not in sql
        assert "tiktok_followers" not in sql

    def test_update_query_is_a_partial_upsert(self):
        """Query must update via VALUES join on uuid, not a full replace."""
        sql = ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS.lower()
        assert "update" in sql
        assert "where" in sql
        assert "uuid" in sql

    def test_get_query_filters_null_accounts(self):
        """GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT must exclude NULLs and empty strings."""
        sql = ComedianQueries.GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT.lower()
        assert "is not null" in sql
        assert "youtube_account" in sql

    def test_get_query_filters_empty_string(self):
        sql = ComedianQueries.GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT
        assert "<> ''" in sql or "!= ''" in sql


# ---------------------------------------------------------------------------
# _get_comedians_with_youtube_accounts
# ---------------------------------------------------------------------------

class TestGetComediansWithYouTubeAccounts:
    def test_returns_list_of_dicts_with_uuid_and_account(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-1", "youtube_account": "@comedian1"},
            {"uuid": "uuid-2", "youtube_account": "https://youtube.com/channel/UCabc"},
        ]
        rows = handler._get_comedians_with_youtube_accounts()
        assert rows == [
            {"uuid": "uuid-1", "youtube_account": "@comedian1"},
            {"uuid": "uuid-2", "youtube_account": "https://youtube.com/channel/UCabc"},
        ]

    def test_none_result_returns_empty_list(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None
        rows = handler._get_comedians_with_youtube_accounts()
        assert rows == []

    def test_passes_correct_query(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = []
        handler._get_comedians_with_youtube_accounts()
        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.GET_COMEDIANS_WITH_YOUTUBE_ACCOUNT, return_results=True
        )


# ---------------------------------------------------------------------------
# _fetch_youtube_subscriber_counts
# ---------------------------------------------------------------------------

class TestFetchYouTubeSubscriberCounts:
    def test_channel_id_extracted_from_bare_id(self):
        """A bare UCxxx string is recognised as a channel ID."""
        handler = _make_handler()
        # YouTube channel IDs are exactly 24 chars: UC + 22 base64url chars
        rows = [{"uuid": "uuid-1", "youtube_account": "UCabcdefghijklmnopqrstuv"}]
        fake_response = _yt_response([_yt_item("UCabcdefghijklmnopqrstuv", 500_000)])

        with patch.object(ComedianHandler, "_youtube_request", return_value=fake_response):
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert results == [("uuid-1", 500_000)]

    def test_channel_id_extracted_from_full_url(self):
        """Channel ID embedded in a youtube.com/channel/ URL is extracted correctly."""
        handler = _make_handler()
        channel_id = "UCabcdefghijklmnopqrstuv"
        rows = [{"uuid": "uuid-2", "youtube_account": f"https://www.youtube.com/channel/{channel_id}"}]
        fake_response = _yt_response([_yt_item(channel_id, 1_000_000)])

        with patch.object(ComedianHandler, "_youtube_request", return_value=fake_response):
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert results == [("uuid-2", 1_000_000)]

    def test_handle_extracted_from_at_url(self):
        """@handle in a youtube.com URL resolves via forHandle request."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-3", "youtube_account": "https://www.youtube.com/@mycomedian"}]
        fake_response = _yt_response([{"id": "UCxxx", "statistics": {"subscriberCount": "250000"}}])

        with patch.object(ComedianHandler, "_youtube_request", return_value=fake_response) as mock_req:
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert results == [("uuid-3", 250_000)]
        mock_req.assert_called_once_with("key", handle="mycomedian")

    def test_bare_at_handle_resolves_correctly(self):
        """A bare @handle string (no URL) is passed as forHandle."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-4", "youtube_account": "@comedianhandle"}]
        fake_response = _yt_response([{"id": "UCyyy", "statistics": {"subscriberCount": "80000"}}])

        with patch.object(ComedianHandler, "_youtube_request", return_value=fake_response) as mock_req:
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert results == [("uuid-4", 80_000)]
        mock_req.assert_called_once_with("key", handle="comedianhandle")

    def test_missing_subscriber_count_skipped(self):
        """Items without subscriberCount in statistics are not included."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-5", "youtube_account": "UCabcdefghijklmnopqrstuv"}]
        # hiddenSubscriberCount: statistics dict has no subscriberCount
        fake_response = _yt_response([{"id": "UCabcdefghijklmnopqrstuv", "statistics": {}}])

        with patch.object(ComedianHandler, "_youtube_request", return_value=fake_response):
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert results == []

    def test_api_error_for_handle_is_isolated(self):
        """A failed request for one handle does not prevent results from others."""
        handler = _make_handler()
        good_response = _yt_response([{"id": "UCgood", "statistics": {"subscriberCount": "100"}}])

        def _side_effect(api_key, ids=None, handle=None):
            if handle == "badhandle":
                raise RuntimeError("404 Not Found")
            return good_response

        rows = [
            {"uuid": "uuid-bad", "youtube_account": "@badhandle"},
            {"uuid": "uuid-good", "youtube_account": "@goodhandle"},
        ]
        with patch.object(ComedianHandler, "_youtube_request", side_effect=_side_effect):
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        # Only the good handle returned a result
        assert ("uuid-good", 100) in results
        assert all(uuid != "uuid-bad" for uuid, _ in results)

    def test_mixed_channel_ids_and_handles(self):
        """Channel IDs are batched; handles are requested individually."""
        handler = _make_handler()
        channel_id = "UCabcdefghijklmnopqrstuv"
        rows = [
            {"uuid": "uuid-id", "youtube_account": channel_id},
            {"uuid": "uuid-handle", "youtube_account": "@myhandle"},
        ]
        id_response = _yt_response([_yt_item(channel_id, 999)])
        handle_response = _yt_response([{"id": "UCzzz", "statistics": {"subscriberCount": "111"}}])

        call_responses = [id_response, handle_response]

        with patch.object(ComedianHandler, "_youtube_request", side_effect=call_responses):
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert ("uuid-id", 999) in results
        assert ("uuid-handle", 111) in results


# ---------------------------------------------------------------------------
# refresh_youtube_followers — end-to-end
# ---------------------------------------------------------------------------

class TestRefreshYouTubeFollowers:
    def test_empty_accounts_returns_zero_without_api_call(self):
        """When no comedians have YouTube accounts, return 0 and skip API."""
        handler = _make_handler()
        handler._get_comedians_with_youtube_accounts = MagicMock(return_value=[])
        handler._fetch_youtube_subscriber_counts = MagicMock()

        result = handler.refresh_youtube_followers("key")

        assert result == 0
        handler._fetch_youtube_subscriber_counts.assert_not_called()
        handler.execute_batch_operation.assert_not_called()

    def test_updates_are_persisted_via_execute_batch_operation(self):
        """Happy path: fetched counts are written to DB."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-A", "youtube_account": "@comedianA"}]
        handler._get_comedians_with_youtube_accounts = MagicMock(return_value=rows)
        handler._fetch_youtube_subscriber_counts = MagicMock(return_value=[("uuid-A", 42_000)])

        result = handler.refresh_youtube_followers("key")

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS,
            [("uuid-A", 42_000)],
        )

    def test_no_batch_call_when_fetch_returns_empty(self):
        """If the API returns no usable data, skip the DB update."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-B", "youtube_account": "@comedianB"}]
        handler._get_comedians_with_youtube_accounts = MagicMock(return_value=rows)
        handler._fetch_youtube_subscriber_counts = MagicMock(return_value=[])

        result = handler.refresh_youtube_followers("key")

        assert result == 0
        handler.execute_batch_operation.assert_not_called()

    def test_batching_respects_batch_size(self):
        """Rows are split into batches of the specified size."""
        handler = _make_handler()
        rows = [{"uuid": f"uuid-{i}", "youtube_account": f"@comedian{i}"} for i in range(5)]
        handler._get_comedians_with_youtube_accounts = MagicMock(return_value=rows)
        handler._fetch_youtube_subscriber_counts = MagicMock(return_value=[])

        handler.refresh_youtube_followers("key", batch_size=2)

        # 5 rows with batch_size=2 → 3 calls: [0:2], [2:4], [4:5]
        assert handler._fetch_youtube_subscriber_counts.call_count == 3


# ---------------------------------------------------------------------------
# SQL contract tests — Instagram
# ---------------------------------------------------------------------------

class TestInstagramFollowersSqlContract:
    def test_update_query_only_sets_instagram_followers(self):
        """UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS must SET only instagram_followers."""
        sql = ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS.lower()
        assert "instagram_followers" in sql
        assert "youtube_followers" not in sql
        assert "tiktok_followers" not in sql

    def test_update_query_is_a_partial_upsert(self):
        sql = ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS.lower()
        assert "update" in sql
        assert "where" in sql
        assert "uuid" in sql

    def test_get_query_filters_null_and_empty(self):
        sql = ComedianQueries.GET_COMEDIANS_WITH_INSTAGRAM_ACCOUNT.lower()
        assert "is not null" in sql
        assert "instagram_account" in sql
        sql_raw = ComedianQueries.GET_COMEDIANS_WITH_INSTAGRAM_ACCOUNT
        assert "<> ''" in sql_raw or "!= ''" in sql_raw


# ---------------------------------------------------------------------------
# SQL contract tests — TikTok
# ---------------------------------------------------------------------------

class TestTikTokFollowersSqlContract:
    def test_update_query_only_sets_tiktok_followers(self):
        """UPDATE_COMEDIAN_TIKTOK_FOLLOWERS must SET only tiktok_followers."""
        sql = ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS.lower()
        assert "tiktok_followers" in sql
        assert "youtube_followers" not in sql
        assert "instagram_followers" not in sql

    def test_update_query_is_a_partial_upsert(self):
        sql = ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS.lower()
        assert "update" in sql
        assert "where" in sql
        assert "uuid" in sql

    def test_get_query_filters_null_and_empty(self):
        sql = ComedianQueries.GET_COMEDIANS_WITH_TIKTOK_ACCOUNT.lower()
        assert "is not null" in sql
        assert "tiktok_account" in sql
        sql_raw = ComedianQueries.GET_COMEDIANS_WITH_TIKTOK_ACCOUNT
        assert "<> ''" in sql_raw or "!= ''" in sql_raw


# ---------------------------------------------------------------------------
# _get_comedians_with_instagram_accounts
# ---------------------------------------------------------------------------

class TestGetComediansWithInstagramAccounts:
    def test_returns_list_of_dicts_with_uuid_and_account(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-1", "instagram_account": "@comedian1"},
            {"uuid": "uuid-2", "instagram_account": "comedian2"},
        ]
        rows = handler._get_comedians_with_instagram_accounts()
        assert rows == [
            {"uuid": "uuid-1", "instagram_account": "@comedian1"},
            {"uuid": "uuid-2", "instagram_account": "comedian2"},
        ]

    def test_none_result_returns_empty_list(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None
        rows = handler._get_comedians_with_instagram_accounts()
        assert rows == []

    def test_passes_correct_query(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = []
        handler._get_comedians_with_instagram_accounts()
        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.GET_COMEDIANS_WITH_INSTAGRAM_ACCOUNT, return_results=True
        )


# ---------------------------------------------------------------------------
# _fetch_instagram_follower_count
# ---------------------------------------------------------------------------

class TestFetchInstagramFollowerCount:
    def _ig_response(self, follower_count: int) -> dict:
        return {"data": {"user": {"edge_followed_by": {"count": follower_count}}}}

    def test_happy_path_returns_uuid_and_count(self):
        handler = _make_handler()
        row = {"uuid": "uuid-1", "instagram_account": "@mycomedian"}
        with patch.object(ComedianHandler, "_instagram_request", return_value=self._ig_response(150_000)):
            result = handler._fetch_instagram_follower_count(row)
        assert result == ("uuid-1", 150_000)

    def test_strips_at_prefix_before_request(self):
        handler = _make_handler()
        row = {"uuid": "uuid-2", "instagram_account": "@somecomedian"}
        with patch.object(ComedianHandler, "_instagram_request", return_value=self._ig_response(100)) as mock_req:
            handler._fetch_instagram_follower_count(row)
        mock_req.assert_called_once_with("somecomedian")

    def test_account_without_at_prefix_works(self):
        handler = _make_handler()
        row = {"uuid": "uuid-3", "instagram_account": "bareaccount"}
        with patch.object(ComedianHandler, "_instagram_request", return_value=self._ig_response(200)) as mock_req:
            result = handler._fetch_instagram_follower_count(row)
        assert result == ("uuid-3", 200)
        mock_req.assert_called_once_with("bareaccount")

    def test_api_error_returns_none(self):
        handler = _make_handler()
        row = {"uuid": "uuid-4", "instagram_account": "@unavailable"}
        with patch.object(ComedianHandler, "_instagram_request", side_effect=RuntimeError("403 Forbidden")):
            result = handler._fetch_instagram_follower_count(row)
        assert result is None

    def test_malformed_response_returns_none(self):
        handler = _make_handler()
        row = {"uuid": "uuid-5", "instagram_account": "@comedian5"}
        with patch.object(ComedianHandler, "_instagram_request", return_value={"data": {}}):
            result = handler._fetch_instagram_follower_count(row)
        assert result is None

    def test_http_error_returns_none(self):
        """requests.exceptions.HTTPError (e.g. 429) is caught and returns None."""
        handler = _make_handler()
        row = {"uuid": "uuid-6", "instagram_account": "@ratelimited"}
        with patch.object(
            ComedianHandler,
            "_instagram_request",
            side_effect=_requests.exceptions.HTTPError("429 Too Many Requests"),
        ):
            result = handler._fetch_instagram_follower_count(row)
        assert result is None


# ---------------------------------------------------------------------------
# refresh_instagram_followers — end-to-end
# ---------------------------------------------------------------------------

class TestRefreshInstagramFollowers:
    def test_empty_accounts_returns_zero_without_api_call(self):
        handler = _make_handler()
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=[])
        handler._fetch_instagram_follower_count = MagicMock()

        result = handler.refresh_instagram_followers()

        assert result == 0
        handler._fetch_instagram_follower_count.assert_not_called()
        handler.execute_batch_operation.assert_not_called()

    def test_updates_are_persisted_via_execute_batch_operation(self):
        handler = _make_handler()
        rows = [{"uuid": "uuid-A", "instagram_account": "@comedianA"}]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(return_value=("uuid-A", 75_000))

        result = handler.refresh_instagram_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            [("uuid-A", 75_000)],
        )

    def test_failed_accounts_are_skipped(self):
        """Accounts where fetch returns None are excluded from the DB update."""
        handler = _make_handler()
        rows = [
            {"uuid": "uuid-ok", "instagram_account": "@ok"},
            {"uuid": "uuid-fail", "instagram_account": "@fail"},
        ]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)

        def _side_effect(row):
            if row["uuid"] == "uuid-fail":
                return None
            return ("uuid-ok", 50_000)

        handler._fetch_instagram_follower_count = MagicMock(side_effect=_side_effect)

        result = handler.refresh_instagram_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            [("uuid-ok", 50_000)],
        )

    def test_no_batch_call_when_all_fetches_fail(self):
        handler = _make_handler()
        rows = [{"uuid": "uuid-B", "instagram_account": "@comedianB"}]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(return_value=None)

        result = handler.refresh_instagram_followers()

        assert result == 0
        handler.execute_batch_operation.assert_not_called()

    def test_warns_when_accounts_exist_but_zero_updated(self):
        """Logs a warning when rows are present but all fetches fail (API blocked)."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-C", "instagram_account": "@comedian_c"}]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(return_value=None)

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            handler.refresh_instagram_followers()
        mock_logger.warn.assert_called_once()
        assert "0 updated" in mock_logger.warn.call_args[0][0]


# ---------------------------------------------------------------------------
# _get_comedians_with_tiktok_accounts
# ---------------------------------------------------------------------------

class TestGetComediansWithTikTokAccounts:
    def test_returns_list_of_dicts_with_uuid_and_account(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-1", "tiktok_account": "@comedian1"},
        ]
        rows = handler._get_comedians_with_tiktok_accounts()
        assert rows == [{"uuid": "uuid-1", "tiktok_account": "@comedian1"}]

    def test_none_result_returns_empty_list(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None
        rows = handler._get_comedians_with_tiktok_accounts()
        assert rows == []

    def test_passes_correct_query(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = []
        handler._get_comedians_with_tiktok_accounts()
        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.GET_COMEDIANS_WITH_TIKTOK_ACCOUNT, return_results=True
        )


# ---------------------------------------------------------------------------
# _fetch_tiktok_follower_count
# ---------------------------------------------------------------------------

class TestFetchTikTokFollowerCount:
    def _tt_response(self, follower_count: int) -> dict:
        return {"userInfo": {"stats": {"followerCount": follower_count}}}

    def test_happy_path_returns_uuid_and_count(self):
        handler = _make_handler()
        row = {"uuid": "uuid-1", "tiktok_account": "@mycomedian"}
        with patch.object(ComedianHandler, "_tiktok_request", return_value=self._tt_response(200_000)):
            result = handler._fetch_tiktok_follower_count(row)
        assert result == ("uuid-1", 200_000)

    def test_strips_at_prefix_before_request(self):
        handler = _make_handler()
        row = {"uuid": "uuid-2", "tiktok_account": "@ttcomedian"}
        with patch.object(ComedianHandler, "_tiktok_request", return_value=self._tt_response(100)) as mock_req:
            handler._fetch_tiktok_follower_count(row)
        mock_req.assert_called_once_with("ttcomedian")

    def test_account_without_at_prefix_works(self):
        handler = _make_handler()
        row = {"uuid": "uuid-3", "tiktok_account": "bareaccount"}
        with patch.object(ComedianHandler, "_tiktok_request", return_value=self._tt_response(300)) as mock_req:
            result = handler._fetch_tiktok_follower_count(row)
        assert result == ("uuid-3", 300)
        mock_req.assert_called_once_with("bareaccount")

    def test_api_error_returns_none(self):
        handler = _make_handler()
        row = {"uuid": "uuid-4", "tiktok_account": "@unavailable"}
        with patch.object(ComedianHandler, "_tiktok_request", side_effect=RuntimeError("429 Rate Limited")):
            result = handler._fetch_tiktok_follower_count(row)
        assert result is None

    def test_malformed_response_returns_none(self):
        handler = _make_handler()
        row = {"uuid": "uuid-5", "tiktok_account": "@comedian5"}
        with patch.object(ComedianHandler, "_tiktok_request", return_value={"userInfo": {}}):
            result = handler._fetch_tiktok_follower_count(row)
        assert result is None

    def test_http_error_returns_none(self):
        """requests.exceptions.HTTPError (e.g. 429) is caught and returns None."""
        handler = _make_handler()
        row = {"uuid": "uuid-6", "tiktok_account": "@ratelimited"}
        with patch.object(
            ComedianHandler,
            "_tiktok_request",
            side_effect=_requests.exceptions.HTTPError("429 Too Many Requests"),
        ):
            result = handler._fetch_tiktok_follower_count(row)
        assert result is None


# ---------------------------------------------------------------------------
# refresh_tiktok_followers — end-to-end
# ---------------------------------------------------------------------------

class TestRefreshTikTokFollowers:
    def test_empty_accounts_returns_zero_without_api_call(self):
        handler = _make_handler()
        handler._get_comedians_with_tiktok_accounts = MagicMock(return_value=[])
        handler._fetch_tiktok_follower_count = MagicMock()

        result = handler.refresh_tiktok_followers()

        assert result == 0
        handler._fetch_tiktok_follower_count.assert_not_called()
        handler.execute_batch_operation.assert_not_called()

    def test_updates_are_persisted_via_execute_batch_operation(self):
        handler = _make_handler()
        rows = [{"uuid": "uuid-A", "tiktok_account": "@comedianA"}]
        handler._get_comedians_with_tiktok_accounts = MagicMock(return_value=rows)
        handler._fetch_tiktok_follower_count = MagicMock(return_value=("uuid-A", 120_000))

        result = handler.refresh_tiktok_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS,
            [("uuid-A", 120_000)],
        )

    def test_failed_accounts_are_skipped(self):
        """Accounts where fetch returns None are excluded from the DB update."""
        handler = _make_handler()
        rows = [
            {"uuid": "uuid-ok", "tiktok_account": "@ok"},
            {"uuid": "uuid-fail", "tiktok_account": "@fail"},
        ]
        handler._get_comedians_with_tiktok_accounts = MagicMock(return_value=rows)

        def _side_effect(row):
            if row["uuid"] == "uuid-fail":
                return None
            return ("uuid-ok", 90_000)

        handler._fetch_tiktok_follower_count = MagicMock(side_effect=_side_effect)

        result = handler.refresh_tiktok_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS,
            [("uuid-ok", 90_000)],
        )

    def test_no_batch_call_when_all_fetches_fail(self):
        handler = _make_handler()
        rows = [{"uuid": "uuid-B", "tiktok_account": "@comedianB"}]
        handler._get_comedians_with_tiktok_accounts = MagicMock(return_value=rows)
        handler._fetch_tiktok_follower_count = MagicMock(return_value=None)

        result = handler.refresh_tiktok_followers()

        assert result == 0
        handler.execute_batch_operation.assert_not_called()

    def test_warns_when_accounts_exist_but_zero_updated(self):
        """Logs a warning when rows are present but all fetches fail (API blocked)."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-C", "tiktok_account": "@comedian_c"}]
        handler._get_comedians_with_tiktok_accounts = MagicMock(return_value=rows)
        handler._fetch_tiktok_follower_count = MagicMock(return_value=None)

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            handler.refresh_tiktok_followers()
        mock_logger.warn.assert_called_once()
        assert "0 updated" in mock_logger.warn.call_args[0][0]
