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
from unittest.mock import MagicMock, patch

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
_IGFetch = _comedian_handler_mod._IGFetch
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

    def test_update_query_stamps_refresh_timestamp(self):
        """UPDATE must also set youtube_followers_refreshed_at."""
        sql = ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS.lower()
        assert "youtube_followers_refreshed_at" in sql
        assert "now()" in sql

    def test_get_query_filters_null_accounts(self):
        """GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT must exclude NULLs and empty strings."""
        sql = ComedianQueries.GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT.lower()
        assert "is not null" in sql
        assert "youtube_account" in sql

    def test_get_query_filters_empty_string(self):
        sql = ComedianQueries.GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT
        assert "<> ''" in sql or "!= ''" in sql

    def test_get_query_filters_on_staleness_window(self):
        """The stale query must gate on the refresh timestamp via a bound param."""
        sql = ComedianQueries.GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT.lower()
        assert "youtube_followers_refreshed_at" in sql
        assert "make_interval(days => %s)" in ComedianQueries.GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT


class TestFollowerHistorySqlContract:
    @pytest.mark.parametrize(
        ("query", "platform"),
        [
            (ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS, "youtube"),
            (ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS, "instagram"),
            (ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS, "tiktok"),
        ],
    )
    def test_each_platform_update_inserts_a_provenanced_observation(
        self, query, platform
    ):
        sql = query.lower()
        assert "insert into comedian_follower_observations" in sql
        assert f"'{platform}'::\"socialplatform\"" in sql
        assert "follower_count" in sql
        assert "observed_at" in sql

    @pytest.mark.parametrize(
        "query",
        [
            ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS,
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS,
        ],
    )
    def test_daily_observation_key_makes_retries_idempotent(self, query):
        sql = " ".join(query.lower().split())
        assert "date_trunc('day', now(), 'utc')" in sql
        assert (
            "on conflict (comedian_id, platform, observed_at) do nothing" in sql
        )

    @pytest.mark.parametrize(
        "query",
        [
            ComedianQueries.UPDATE_COMEDIAN_YOUTUBE_FOLLOWERS,
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS,
        ],
    )
    def test_successful_unchanged_counts_are_not_filtered_out(self, query):
        sql = query.lower()
        assert "from updated" in sql
        assert "is distinct from" not in sql
        assert "follower_count <>" not in sql


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
        rows = handler._get_comedians_with_youtube_accounts(7)
        assert rows == [
            {"uuid": "uuid-1", "youtube_account": "@comedian1"},
            {"uuid": "uuid-2", "youtube_account": "https://youtube.com/channel/UCabc"},
        ]

    def test_none_result_returns_empty_list(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None
        rows = handler._get_comedians_with_youtube_accounts(7)
        assert rows == []

    def test_passes_correct_query(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = []
        handler._get_comedians_with_youtube_accounts(7)
        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.GET_STALE_COMEDIANS_WITH_YOUTUBE_ACCOUNT,
            params=(7,),
            return_results=True,
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

    def test_measured_zero_subscribers_is_not_treated_as_missing(self):
        channel_id = "UCabcdefghijklmnopqrstuv"
        handler = _make_handler()
        rows = [{"uuid": "uuid-zero", "youtube_account": channel_id}]
        fake_response = _yt_response([_yt_item(channel_id, 0)])

        with patch.object(ComedianHandler, "_youtube_request", return_value=fake_response):
            results = handler._fetch_youtube_subscriber_counts("key", rows)

        assert results == [("uuid-zero", 0)]

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

    def test_first_growth_and_later_unchanged_measurements_all_reach_persistence(self):
        handler = _make_handler()
        rows = [{"uuid": "uuid-A", "youtube_account": "@comedianA"}]
        handler._get_comedians_with_youtube_accounts = MagicMock(return_value=rows)
        handler._fetch_youtube_subscriber_counts = MagicMock(
            side_effect=[
                [("uuid-A", 100)],
                [("uuid-A", 150)],
                [("uuid-A", 150)],
            ]
        )

        assert [handler.refresh_youtube_followers("key") for _ in range(3)] == [1, 1, 1]
        persisted = [call.args[1] for call in handler.execute_batch_operation.call_args_list]
        assert persisted == [
            [("uuid-A", 100)],
            [("uuid-A", 150)],
            [("uuid-A", 150)],
        ]


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

    def test_targeted_query_selects_numeric_ids_without_staleness_filter(self):
        sql = ComedianQueries.GET_COMEDIANS_FOR_INSTAGRAM_REFRESH_BY_IDS.lower()
        assert "id = any(%s)" in sql
        assert "instagram_followers_refreshed_at" not in sql

    def test_update_query_is_a_partial_upsert(self):
        sql = ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS.lower()
        assert "update" in sql
        assert "where" in sql
        assert "uuid" in sql

    def test_get_query_filters_null_and_empty(self):
        sql = ComedianQueries.GET_STALE_COMEDIANS_WITH_INSTAGRAM_ACCOUNT.lower()
        assert "is not null" in sql
        assert "instagram_account" in sql
        sql_raw = ComedianQueries.GET_STALE_COMEDIANS_WITH_INSTAGRAM_ACCOUNT
        assert "<> ''" in sql_raw or "!= ''" in sql_raw

    def test_get_query_filters_on_staleness_window(self):
        """The stale query must gate on the refresh timestamp via a bound param."""
        sql = ComedianQueries.GET_STALE_COMEDIANS_WITH_INSTAGRAM_ACCOUNT.lower()
        assert "instagram_followers_refreshed_at" in sql
        assert "make_interval(days => %s)" in ComedianQueries.GET_STALE_COMEDIANS_WITH_INSTAGRAM_ACCOUNT

    def test_update_query_stamps_refresh_timestamp(self):
        """UPDATE must also set instagram_followers_refreshed_at."""
        sql = ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS.lower()
        assert "instagram_followers_refreshed_at" in sql
        assert "now()" in sql

    def test_clear_query_nulls_handle_count_and_timestamp(self):
        """CLEAR_COMEDIAN_INSTAGRAM_ACCOUNT must null all three Instagram fields."""
        sql = ComedianQueries.CLEAR_COMEDIAN_INSTAGRAM_ACCOUNT.lower()
        assert "instagram_account = null" in sql
        assert "instagram_followers = null" in sql
        assert "instagram_followers_refreshed_at = null" in sql
        # Scoped to the given uuids, never a blanket wipe.
        assert "where" in sql and "uuid" in sql


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
        rows = handler._get_comedians_with_instagram_accounts(7)
        assert rows == [
            {"uuid": "uuid-1", "instagram_account": "@comedian1"},
            {"uuid": "uuid-2", "instagram_account": "comedian2"},
        ]

    def test_none_result_returns_empty_list(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None
        rows = handler._get_comedians_with_instagram_accounts(7)
        assert rows == []

    def test_passes_correct_query(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = []
        handler._get_comedians_with_instagram_accounts(7)
        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.GET_STALE_COMEDIANS_WITH_INSTAGRAM_ACCOUNT,
            params=(7,),
            return_results=True,
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
        assert result == _IGFetch("ok", "uuid-1", 150_000)

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
        assert result == _IGFetch("ok", "uuid-3", 200)
        mock_req.assert_called_once_with("bareaccount")

    def test_api_error_returns_skip(self):
        handler = _make_handler()
        row = {"uuid": "uuid-4", "instagram_account": "@unavailable"}
        with patch.object(ComedianHandler, "_instagram_request", side_effect=RuntimeError("403 Forbidden")):
            result = handler._fetch_instagram_follower_count(row)
        assert result.status == "skip"
        assert result.uuid == "uuid-4"

    def test_malformed_response_returns_skip(self):
        handler = _make_handler()
        row = {"uuid": "uuid-5", "instagram_account": "@comedian5"}
        with patch.object(ComedianHandler, "_instagram_request", return_value={"data": {}}):
            result = handler._fetch_instagram_follower_count(row)
        assert result.status == "skip"

    def test_http_error_returns_skip(self):
        """A transient HTTPError (e.g. 429) is caught and returns a skip."""
        handler = _make_handler()
        row = {"uuid": "uuid-6", "instagram_account": "@ratelimited"}
        with patch.object(
            ComedianHandler,
            "_instagram_request",
            side_effect=_requests.exceptions.HTTPError("429 Too Many Requests"),
        ):
            result = handler._fetch_instagram_follower_count(row)
        assert result.status == "skip"

    def test_persistent_404_returns_dead(self):
        """A handle that 404s across the confirmation threshold is marked dead."""
        handler = _make_handler()
        row = {"uuid": "uuid-7", "instagram_account": "@gone"}
        gone = _comedian_handler_mod._InstagramAccountGone("gone")
        with patch.object(ComedianHandler, "_instagram_request", side_effect=gone):
            result = handler._fetch_instagram_follower_count(row)
        assert result == _IGFetch("dead", "uuid-7", None)

    def test_single_404_then_recovery_is_not_marked_dead(self):
        """One 404 followed by a success must NOT clear the handle (blip guard)."""
        handler = _make_handler()
        row = {"uuid": "uuid-8", "instagram_account": "@blip"}
        gone = _comedian_handler_mod._InstagramAccountGone("blip")
        with patch.object(
            ComedianHandler,
            "_instagram_request",
            side_effect=[gone, self._ig_response(500)],
        ):
            result = handler._fetch_instagram_follower_count(row)
        assert result == _IGFetch("ok", "uuid-8", 500)

    @pytest.mark.parametrize(
        ("label", "expected"),
        [
            ("27K", 27_000),
            ("3M", 3_000_000),
            ("20m", 20_000_000),
            ("1.2B", 1_200_000_000),
            ("123,456", 123_456),
        ],
    )
    def test_parses_formatted_html_follower_counts(self, label, expected):
        html = (
            f'<meta content="{label} Followers, 10 Following" name="description">'
        )
        assert (
            _comedian_handler_mod._parse_instagram_follower_count_from_html(html)
            == expected
        )

    def test_taylor_schema_error_uses_html_fallback(self):
        api_response = MagicMock(status_code=400)
        api_response.raise_for_status.side_effect = _requests.exceptions.HTTPError(
            "400 Client Error"
        )
        api_response.text = (
            '{"message":"Asset asset://laser.provider/'
            "ig_business_category_subvertical has been deleted. "
            'You cannot use this schema"}'
        )
        html_response = MagicMock(status_code=200)
        html_response.text = (
            '<meta property="og:description" '
            'content="3M Followers, 1,481 Following, 2,031 Posts">'
        )

        with (
            patch.object(
                _comedian_handler_mod.cffi_requests,
                "get",
                side_effect=[api_response, html_response],
            ),
            patch.object(_comedian_handler_mod, "Logger") as logger,
        ):
            data = ComedianHandler._instagram_request("taylortomlinson")

        assert data["data"]["user"]["edge_followed_by"]["count"] == 3_000_000
        assert "rounded HTML follower count 3000000" in logger.warn.call_args[0][0]

    def test_confirmed_404_does_not_use_html_fallback(self):
        api_response = MagicMock(status_code=404)

        with patch.object(
            _comedian_handler_mod.cffi_requests, "get", return_value=api_response
        ) as request:
            with pytest.raises(_comedian_handler_mod._InstagramAccountGone):
                ComedianHandler._instagram_request("gone")

        request.assert_called_once()

    def test_html_fallback_failure_returns_skip(self):
        api_response = MagicMock(status_code=400)
        api_response.raise_for_status.side_effect = _requests.exceptions.HTTPError(
            "400 Client Error"
        )
        html_response = MagicMock(status_code=200, text="<html></html>")
        handler = _make_handler()
        row = {"uuid": "uuid-9", "instagram_account": "@stillblocked"}

        with (
            patch.object(
                _comedian_handler_mod.cffi_requests,
                "get",
                side_effect=[api_response, html_response],
            ),
            patch.object(_comedian_handler_mod, "_INSTAGRAM_MAX_ATTEMPTS", 1),
        ):
            result = handler._fetch_instagram_follower_count(row)

        assert result == _IGFetch("skip", "uuid-9", None)


# ---------------------------------------------------------------------------
# refresh_instagram_followers — end-to-end
# ---------------------------------------------------------------------------

class TestRefreshInstagramFollowers:
    def test_targeted_refresh_bypasses_staleness_and_preserves_csv_order(self):
        handler = _make_handler()
        rows = [
            {"uuid": "uuid-2", "instagram_account": "@second"},
            {"uuid": "uuid-1", "instagram_account": "@first"},
        ]
        handler._get_comedians_with_instagram_accounts = MagicMock()
        handler._get_comedians_with_instagram_accounts_by_ids = MagicMock(
            return_value=rows
        )
        handler._fetch_instagram_follower_count = MagicMock(
            side_effect=[
                _IGFetch("ok", "uuid-2", 20),
                _IGFetch("ok", "uuid-1", 10),
            ]
        )

        result = handler.refresh_instagram_followers(comedian_ids=[2, 1])

        assert result == 2
        handler._get_comedians_with_instagram_accounts.assert_not_called()
        handler._get_comedians_with_instagram_accounts_by_ids.assert_called_once_with(
            [2, 1]
        )
        assert [
            fetch_call.args[0]["uuid"]
            for fetch_call in handler._fetch_instagram_follower_count.call_args_list
        ] == ["uuid-2", "uuid-1"]

    def test_targeted_lookup_reconstructs_deduplicated_input_order(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"id": 1, "uuid": "uuid-1", "instagram_account": "@first"},
            {"id": 2, "uuid": "uuid-2", "instagram_account": "@second"},
        ]

        rows = handler._get_comedians_with_instagram_accounts_by_ids([2, 1, 2])

        assert rows == [
            {"uuid": "uuid-2", "instagram_account": "@second"},
            {"uuid": "uuid-1", "instagram_account": "@first"},
        ]
        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.GET_COMEDIANS_FOR_INSTAGRAM_REFRESH_BY_IDS,
            params=([2, 1],),
            return_results=True,
        )

    def test_targeted_lookup_rejects_all_problems_before_fetching(self):
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"id": 1, "uuid": "uuid-1", "instagram_account": ""},
        ]
        handler._fetch_instagram_follower_count = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            handler.refresh_instagram_followers(comedian_ids=[1, 999])

        assert "unknown comedian IDs: [999]" in str(exc_info.value)
        assert "without Instagram accounts: [1]" in str(exc_info.value)
        handler._fetch_instagram_follower_count.assert_not_called()

    @pytest.mark.parametrize("kwargs", [{"limit": 1}, {"stale_days": 0}])
    def test_targeted_refresh_rejects_incompatible_options(self, kwargs):
        handler = _make_handler()
        handler._fetch_instagram_follower_count = MagicMock()

        with pytest.raises(ValueError):
            handler.refresh_instagram_followers(comedian_ids=[1], **kwargs)

        handler._fetch_instagram_follower_count.assert_not_called()

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
        handler._fetch_instagram_follower_count = MagicMock(return_value=_IGFetch("ok", "uuid-A", 75_000))

        result = handler.refresh_instagram_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            [("uuid-A", 75_000)],
        )

    def test_failed_accounts_are_skipped(self):
        """Accounts where fetch returns a skip are excluded from the DB update."""
        handler = _make_handler()
        rows = [
            {"uuid": "uuid-ok", "instagram_account": "@ok"},
            {"uuid": "uuid-fail", "instagram_account": "@fail"},
        ]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)

        def _side_effect(row):
            if row["uuid"] == "uuid-fail":
                return _IGFetch("skip", "uuid-fail", None)
            return _IGFetch("ok", "uuid-ok", 50_000)

        handler._fetch_instagram_follower_count = MagicMock(side_effect=_side_effect)

        result = handler.refresh_instagram_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            [("uuid-ok", 50_000)],
        )

    def test_persists_in_chunks(self, monkeypatch):
        """Results flush in chunks so a mid-run stop keeps partial progress."""
        handler = _make_handler()
        rows = [{"uuid": f"uuid-{i}", "instagram_account": f"@c{i}"} for i in range(5)]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(
            side_effect=[_IGFetch("ok", f"uuid-{i}", 100 + i) for i in range(5)]
        )
        monkeypatch.setattr(_comedian_handler_mod, "_INSTAGRAM_PERSIST_CHUNK", 2)

        result = handler.refresh_instagram_followers()

        assert result == 5
        # 5 updates at chunk size 2 → flushes of 2, 2, then a final 1 = 3 writes,
        # NOT a single terminal batch.
        update_calls = [
            c for c in handler.execute_batch_operation.call_args_list
            if c.args[0] == ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS
        ]
        assert [len(c.args[1]) for c in update_calls] == [2, 2, 1]

    def test_dead_handles_are_cleared(self):
        """A 'dead' (404) result clears the account via the CLEAR query."""
        handler = _make_handler()
        rows = [
            {"uuid": "uuid-ok", "instagram_account": "@ok"},
            {"uuid": "uuid-gone", "instagram_account": "@gone"},
        ]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)

        def _side_effect(row):
            if row["uuid"] == "uuid-gone":
                return _IGFetch("dead", "uuid-gone", None)
            return _IGFetch("ok", "uuid-ok", 50_000)

        handler._fetch_instagram_follower_count = MagicMock(side_effect=_side_effect)

        result = handler.refresh_instagram_followers()

        # Return value counts follower updates only, not clears.
        assert result == 1
        handler.execute_batch_operation.assert_any_call(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            [("uuid-ok", 50_000)],
        )
        handler.execute_batch_operation.assert_any_call(
            ComedianQueries.CLEAR_COMEDIAN_INSTAGRAM_ACCOUNT,
            [("uuid-gone",)],
        )

    def test_clears_dead_handles_even_with_zero_updates(self):
        """When every reachable handle is dead, still issue the CLEAR (no UPDATE)."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-gone", "instagram_account": "@gone"}]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(
            return_value=_IGFetch("dead", "uuid-gone", None)
        )

        result = handler.refresh_instagram_followers()

        assert result == 0
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.CLEAR_COMEDIAN_INSTAGRAM_ACCOUNT,
            [("uuid-gone",)],
        )

    def test_no_batch_call_when_all_fetches_fail(self):
        handler = _make_handler()
        rows = [{"uuid": "uuid-B", "instagram_account": "@comedianB"}]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(
            return_value=_IGFetch("skip", "uuid-B", None)
        )

        result = handler.refresh_instagram_followers()

        assert result == 0
        handler.execute_batch_operation.assert_not_called()

    def test_warns_when_accounts_exist_but_zero_updated(self):
        """Logs a warning when rows are present but all fetches skip (API blocked)."""
        handler = _make_handler()
        rows = [{"uuid": "uuid-C", "instagram_account": "@comedian_c"}]
        handler._get_comedians_with_instagram_accounts = MagicMock(return_value=rows)
        handler._fetch_instagram_follower_count = MagicMock(
            return_value=_IGFetch("skip", "uuid-C", None)
        )

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
