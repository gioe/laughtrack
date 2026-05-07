"""Unit tests for the capsolver-backed DataDome solver module."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from laughtrack.foundation.infrastructure.http.protection.datadome_solver import (
    CAPSOLVER_API_KEY_ENV,
    DATADOME_IFRAME_HOST,
    DataDomeSolver,
    DataDomeSolverError,
    SolvedCookie,
    build_default_solver,
    is_datadome_iframe_url,
    parse_set_cookie,
)


# ---------------------------------------------------------------------------
# is_datadome_iframe_url
# ---------------------------------------------------------------------------


class TestIsDataDomeIframeUrl:
    def test_matches_geo_captcha_delivery_host(self):
        assert is_datadome_iframe_url(
            "https://geo.captcha-delivery.com/captcha/?cid=ABC&hash=DEF"
        )

    def test_returns_false_for_unrelated_iframe(self):
        assert not is_datadome_iframe_url("https://example.com/iframe.html")

    def test_returns_false_for_none(self):
        assert not is_datadome_iframe_url(None)

    def test_returns_false_for_empty_string(self):
        assert not is_datadome_iframe_url("")

    def test_constant_is_canonical_host(self):
        # The host string is shared with PlaywrightBrowser's iframe selector;
        # a typo here would break detection silently.
        assert DATADOME_IFRAME_HOST == "geo.captcha-delivery.com"


# ---------------------------------------------------------------------------
# parse_set_cookie
# ---------------------------------------------------------------------------


class TestParseSetCookie:
    def test_basic_name_value_with_domain(self):
        cookie = parse_set_cookie("datadome=ABC123; Domain=.example.com; Path=/")
        assert cookie == {
            "name": "datadome",
            "value": "ABC123",
            "domain": ".example.com",
            "path": "/",
        }

    def test_full_attributes_parsed(self):
        cookie = parse_set_cookie(
            "datadome=v; Domain=.example.com; Path=/; Secure; HttpOnly; SameSite=Lax"
        )
        assert cookie["secure"] is True
        assert cookie["httpOnly"] is True
        assert cookie["sameSite"] == "Lax"

    def test_default_domain_used_when_set_cookie_omits_it(self):
        cookie = parse_set_cookie("datadome=v; Path=/", default_domain="example.com")
        assert cookie is not None
        assert cookie["domain"] == "example.com"

    def test_returns_none_without_domain(self):
        # No Domain attr in the Set-Cookie AND no default — Playwright
        # rejects domain-less cookies, so we filter them out up front.
        assert parse_set_cookie("datadome=v; Path=/") is None

    def test_returns_none_for_empty_string(self):
        assert parse_set_cookie("") is None

    def test_returns_none_when_missing_equals(self):
        assert parse_set_cookie("malformed; Domain=example.com") is None

    def test_samesite_normalized_to_capitalized(self):
        cookie = parse_set_cookie(
            "datadome=v; Domain=example.com; SameSite=lax"
        )
        assert cookie is not None
        assert cookie["sameSite"] == "Lax"

    def test_unknown_samesite_value_dropped(self):
        cookie = parse_set_cookie(
            "datadome=v; Domain=example.com; SameSite=Bogus"
        )
        assert cookie is not None
        assert "sameSite" not in cookie


# ---------------------------------------------------------------------------
# build_default_solver — env-var guardrail
# ---------------------------------------------------------------------------


class TestBuildDefaultSolver:
    def test_returns_none_when_env_var_unset(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(CAPSOLVER_API_KEY_ENV, None)
            assert build_default_solver() is None

    def test_returns_none_when_env_var_empty(self):
        with patch.dict(os.environ, {CAPSOLVER_API_KEY_ENV: ""}):
            assert build_default_solver() is None

    def test_returns_solver_when_env_var_set(self):
        with patch.dict(os.environ, {CAPSOLVER_API_KEY_ENV: "cap-test-key"}):
            solver = build_default_solver()
            assert isinstance(solver, DataDomeSolver)


# ---------------------------------------------------------------------------
# DataDomeSolver.solve
# ---------------------------------------------------------------------------


class _FakeSolver(DataDomeSolver):
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


class TestDataDomeSolverSolve:
    @pytest.mark.asyncio
    async def test_success_returns_solved_cookie(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {
                        "cookie": "datadome=ABC; Domain=.etix.com",
                        "userAgent": "Mozilla/5.0 …",
                    },
                },
            ]
        )
        result = await solver.solve(
            captcha_url="https://geo.captcha-delivery.com/c/?cid=X",
            website_url="https://www.etix.com/foo",
            user_agent="Mozilla/5.0 …",
        )
        assert isinstance(result, SolvedCookie)
        assert result.cookie.startswith("datadome=ABC")
        assert result.user_agent == "Mozilla/5.0 …"
        # createTask + getTaskResult both called
        assert len(solver.calls) == 2
        assert solver.calls[0][0].endswith("/createTask")
        assert solver.calls[1][0].endswith("/getTaskResult")

    @pytest.mark.asyncio
    async def test_create_task_error_raises(self):
        solver = _FakeSolver(
            responses=[
                {
                    "errorId": 1,
                    "errorCode": "ERROR_INVALID_TASK_DATA",
                    "errorDescription": "unsupported userAgent",
                }
            ]
        )
        with pytest.raises(DataDomeSolverError) as excinfo:
            await solver.solve(
                captcha_url="https://geo.captcha-delivery.com/c/",
                website_url="https://www.etix.com/foo",
                user_agent="bad-ua",
            )
        assert "unsupported userAgent" in str(excinfo.value)

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
        with pytest.raises(DataDomeSolverError):
            await solver.solve(
                captcha_url="x",
                website_url="x",
                user_agent="x",
            )

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        # All poll responses come back as 'processing' — the solver never
        # sees 'ready' and must abort within timeout_sec rather than loop.
        solver = _FakeSolver(
            responses=[{"errorId": 0, "taskId": "t-1"}]
            + [{"errorId": 0, "status": "processing"}] * 100
        )
        result = await solver.solve(
            captcha_url="x", website_url="x", user_agent="x"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_proxy_url_threaded_into_task_payload(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {
                        "cookie": "datadome=v; Domain=.example.com",
                        "userAgent": "ua",
                    },
                },
            ]
        )
        await solver.solve(
            captcha_url="x",
            website_url="x",
            user_agent="ua",
            proxy_url="http://user:pass@proxy:3128",
        )
        create_payload = solver.calls[0][1]
        assert create_payload["task"]["proxy"] == "http://user:pass@proxy:3128"
        assert create_payload["task"]["type"] == "DatadomeSliderTask"

    @pytest.mark.asyncio
    async def test_missing_task_id_returns_none(self):
        solver = _FakeSolver(responses=[{"errorId": 0}])
        result = await solver.solve(
            captcha_url="x", website_url="x", user_agent="x"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_solution_cookie_returns_none(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {"errorId": 0, "status": "ready", "solution": {}},
            ]
        )
        result = await solver.solve(
            captcha_url="x", website_url="x", user_agent="x"
        )
        assert result is None

    def test_empty_api_key_rejected_at_construction(self):
        with pytest.raises(ValueError):
            DataDomeSolver("")
