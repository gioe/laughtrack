"""Unit tests for the capsolver-backed Cloudflare challenge solver module."""

import os
from unittest.mock import patch

import pytest

from laughtrack.foundation.infrastructure.http.protection.cloudflare_solver import (
    CF_CLEARANCE_COOKIE_NAME,
    CLOUDFLARE_CHALLENGE_MARKERS,
    CloudflareSolver,
    CloudflareSolverError,
    SolvedCloudflareClearance,
    build_default_cloudflare_solver,
    is_cloudflare_interactive_challenge,
)
from laughtrack.foundation.infrastructure.http.protection.datadome_solver import (
    CAPSOLVER_API_KEY_ENV,
)


# ---------------------------------------------------------------------------
# CLOUDFLARE_CHALLENGE_MARKERS — canonical home for detection
# ---------------------------------------------------------------------------


class TestCloudflareMarkers:
    def test_includes_just_a_moment(self):
        # PlaywrightBrowser aliases _CLOUDFLARE_CHALLENGE_MARKERS to this tuple;
        # a typo here would silently break challenge detection.
        assert "just a moment" in CLOUDFLARE_CHALLENGE_MARKERS
        assert "_cf_chl_opt" in CLOUDFLARE_CHALLENGE_MARKERS

    def test_is_a_tuple_for_immutability(self):
        assert isinstance(CLOUDFLARE_CHALLENGE_MARKERS, tuple)


# ---------------------------------------------------------------------------
# is_cloudflare_interactive_challenge
# ---------------------------------------------------------------------------


class TestIsCloudflareInteractiveChallenge:
    def test_detects_just_a_moment_case_insensitive(self):
        html = "<html><head><title>Just a Moment...</title></head></html>"
        assert is_cloudflare_interactive_challenge(html)

    def test_detects_cf_chl_opt(self):
        html = "<html><script>window._cf_chl_opt={};</script></html>"
        assert is_cloudflare_interactive_challenge(html)

    def test_no_markers_returns_false(self):
        assert not is_cloudflare_interactive_challenge("<html><body>real show</body></html>")

    def test_empty_html_returns_false(self):
        assert not is_cloudflare_interactive_challenge("")


# ---------------------------------------------------------------------------
# CloudflareSolver.solve
# ---------------------------------------------------------------------------


class _FakeSolver(CloudflareSolver):
    """Subclass that swaps _post_json for a scripted async mock."""

    def __init__(self, api_key="cap-test", responses=None, **kwargs):
        super().__init__(api_key, poll_interval_sec=0.0, timeout_sec=2.0, **kwargs)
        self.responses = list(responses or [])
        self.calls = []

    async def _post_json(self, url, payload):
        self.calls.append((url, payload))
        if not self.responses:
            return {}
        return self.responses.pop(0)


class TestCloudflareSolverSolve:
    @pytest.mark.asyncio
    async def test_proxy_solve_returns_cf_clearance_cookie_from_cookies_dict(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-cf-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {
                        "cookies": {"cf_clearance": "ABC123"},
                        "token": "tok",
                        "userAgent": "Mozilla/5.0 cf",
                    },
                },
            ]
        )
        result = await solver.solve(
            website_url="https://tickettailor.com/foo",
            user_agent="Mozilla/5.0 cf",
            proxy_url="http://user:pass@proxy:3128",
        )
        assert isinstance(result, SolvedCloudflareClearance)
        # Bare value normalized to a cf_clearance Set-Cookie.
        assert result.cookie.startswith("cf_clearance=ABC123")
        assert "Secure" in result.cookie and "HttpOnly" in result.cookie
        assert result.token == "tok"
        assert result.user_agent == "Mozilla/5.0 cf"
        assert len(solver.calls) == 2
        assert solver.calls[0][0].endswith("/createTask")
        assert solver.calls[1][0].endswith("/getTaskResult")

    @pytest.mark.asyncio
    async def test_proxy_solve_uses_anticloudflare_task_type(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookies": {"cf_clearance": "v"}},
                },
            ]
        )
        await solver.solve(
            website_url="https://x.com/",
            user_agent="ua",
            proxy_url="http://user:pass@proxy:3128",
            website_key="0xSITEKEY",
            action="managed",
        )
        task = solver.calls[0][1]["task"]
        assert task["type"] == "AntiCloudflareTask"
        assert task["proxy"] == "http://user:pass@proxy:3128"
        assert task["websiteKey"] == "0xSITEKEY"
        assert task["metadata"]["action"] == "managed"

    @pytest.mark.asyncio
    async def test_accepts_full_set_cookie_under_cookie_field(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {
                        "cookie": "cf_clearance=XYZ; Domain=.x.com; Path=/; Secure",
                    },
                },
            ]
        )
        result = await solver.solve(
            website_url="https://x.com/", user_agent="ua", proxy_url="http://p:1"
        )
        # Already a full Set-Cookie — passed through without re-wrapping.
        assert result.cookie == "cf_clearance=XYZ; Domain=.x.com; Path=/; Secure"

    @pytest.mark.asyncio
    async def test_proxyless_with_sitekey_uses_turnstile_task_and_returns_token(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"token": "TURNSTILE_TOKEN", "userAgent": "ua"},
                },
            ]
        )
        result = await solver.solve(
            website_url="https://x.com/", user_agent="ua", website_key="0xKEY"
        )
        task = solver.calls[0][1]["task"]
        assert task["type"] == "AntiTurnstileTaskProxyless"
        assert task["websiteKey"] == "0xKEY"
        assert result.token == "TURNSTILE_TOKEN"
        assert result.cookie is None

    @pytest.mark.asyncio
    async def test_no_proxy_no_sitekey_skips_solve_without_api_call(self):
        # cf_clearance is IP-bound (needs a proxy) and the proxyless token flow
        # needs a sitekey — with neither, there is nothing to submit.
        solver = _FakeSolver(responses=[{"errorId": 0, "taskId": "t-1"}])
        result = await solver.solve(website_url="https://x.com/", user_agent="ua")
        assert result is None
        assert solver.calls == []

    @pytest.mark.asyncio
    async def test_create_task_error_raises(self):
        solver = _FakeSolver(
            responses=[
                {
                    "errorId": 1,
                    "errorCode": "ERROR_INVALID_TASK_DATA",
                    "errorDescription": "bad proxy",
                }
            ]
        )
        with pytest.raises(CloudflareSolverError) as excinfo:
            await solver.solve(
                website_url="https://x.com/", user_agent="ua", proxy_url="http://p:1"
            )
        assert "bad proxy" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_task_result_error_raises(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 1,
                    "errorCode": "ERROR_TASKID_INVALID",
                    "errorDescription": "task expired",
                },
            ]
        )
        with pytest.raises(CloudflareSolverError):
            await solver.solve(
                website_url="https://x.com/", user_agent="ua", proxy_url="http://p:1"
            )

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        # Always "processing" — the 2s timeout (poll 0s) trips and returns None.
        solver = _FakeSolver(
            responses=[{"errorId": 0, "taskId": "t-1"}],
        )
        # Make getTaskResult perpetually processing.
        solver.responses.append({"errorId": 0, "status": "processing"})

        async def _always_processing(url, payload):
            solver.calls.append((url, payload))
            if url.endswith("/createTask"):
                return {"errorId": 0, "taskId": "t-1"}
            return {"errorId": 0, "status": "processing"}

        solver._post_json = _always_processing  # type: ignore[assignment]
        result = await solver.solve(
            website_url="https://x.com/", user_agent="ua", proxy_url="http://p:1"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_ready_with_no_cookie_or_token_returns_none(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {"errorId": 0, "status": "ready", "solution": {}},
            ]
        )
        result = await solver.solve(
            website_url="https://x.com/", user_agent="ua", proxy_url="http://p:1"
        )
        assert result is None


# ---------------------------------------------------------------------------
# build_default_cloudflare_solver — env guardrail
# ---------------------------------------------------------------------------


class TestBuildDefaultCloudflareSolver:
    def test_returns_none_when_env_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            assert build_default_cloudflare_solver() is None

    def test_returns_solver_when_env_set(self):
        with patch.dict(os.environ, {CAPSOLVER_API_KEY_ENV: "cap-live"}, clear=True):
            solver = build_default_cloudflare_solver()
            assert isinstance(solver, CloudflareSolver)


class TestConstants:
    def test_cf_clearance_cookie_name(self):
        assert CF_CLEARANCE_COOKIE_NAME == "cf_clearance"
