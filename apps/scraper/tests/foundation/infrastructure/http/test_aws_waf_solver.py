"""Unit tests for the capsolver-backed AWS WAF solver module."""

import os
from unittest.mock import patch

import pytest

from laughtrack.foundation.infrastructure.http.protection.aws_waf_solver import (
    AWS_WAF_MARKERS,
    AwsWafSolver,
    AwsWafSolverError,
    SolvedAwsWafCookie,
    build_default_aws_waf_solver,
    is_aws_waf_interactive_challenge,
)
from laughtrack.foundation.infrastructure.http.protection.datadome_solver import (
    CAPSOLVER_API_KEY_ENV,
)


# ---------------------------------------------------------------------------
# AWS_WAF_MARKERS — canonical home for detection
# ---------------------------------------------------------------------------


class TestAwsWafMarkers:
    def test_includes_passive_challenge_globals(self):
        # PlaywrightBrowser._wait_for_waf_challenge polls the live DOM for
        # the absence of these globals, and aliases _AWS_WAF_MARKERS to
        # this tuple. A typo would silently break detection.
        assert "awsWafCookieDomainList" in AWS_WAF_MARKERS
        assert "gokuProps" in AWS_WAF_MARKERS

    def test_is_a_tuple_for_immutability(self):
        assert isinstance(AWS_WAF_MARKERS, tuple)


# ---------------------------------------------------------------------------
# is_aws_waf_interactive_challenge
# ---------------------------------------------------------------------------


class TestIsAwsWafInteractiveChallenge:
    def test_detects_aws_waf_cookie_domain_list(self):
        html = "<html><script>window.awsWafCookieDomainList=['etix.com'];</script></html>"
        assert is_aws_waf_interactive_challenge(html)

    def test_detects_goku_props(self):
        html = "<html><script>window.gokuProps={};</script></html>"
        assert is_aws_waf_interactive_challenge(html)

    def test_returns_false_for_post_challenge_html(self):
        # When the passive WAF wait succeeds the markers are gone — this
        # must NOT trigger the interactive solver (criterion 6573).
        assert not is_aws_waf_interactive_challenge(
            "<html>real venue content</html>"
        )

    def test_returns_false_for_empty_string(self):
        assert not is_aws_waf_interactive_challenge("")

    def test_returns_false_for_unrelated_html(self):
        assert not is_aws_waf_interactive_challenge(
            "<html><body>regular content</body></html>"
        )


# ---------------------------------------------------------------------------
# build_default_aws_waf_solver — env-var guardrail
# ---------------------------------------------------------------------------


class TestBuildDefaultAwsWafSolver:
    def test_returns_none_when_env_var_unset(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(CAPSOLVER_API_KEY_ENV, None)
            assert build_default_aws_waf_solver() is None

    def test_returns_none_when_env_var_empty(self):
        with patch.dict(os.environ, {CAPSOLVER_API_KEY_ENV: ""}):
            assert build_default_aws_waf_solver() is None

    def test_returns_solver_when_env_var_set(self):
        with patch.dict(os.environ, {CAPSOLVER_API_KEY_ENV: "cap-test-key"}):
            solver = build_default_aws_waf_solver()
            assert isinstance(solver, AwsWafSolver)

    def test_shares_capsolver_api_key_with_datadome(self):
        # Operator-facing surface: one secret, both protection systems.
        # If this ever splits we need separate env vars in .env.example.
        from laughtrack.foundation.infrastructure.http.protection.datadome_solver import (
            CAPSOLVER_API_KEY_ENV as DD_KEY,
        )

        assert CAPSOLVER_API_KEY_ENV == DD_KEY


# ---------------------------------------------------------------------------
# AwsWafSolver.solve
# ---------------------------------------------------------------------------


class _FakeSolver(AwsWafSolver):
    """Subclass that swaps _post_json for a scripted async mock."""

    def __init__(self, api_key="cap-test", responses=None, **kwargs):
        super().__init__(
            api_key, poll_interval_sec=0.0, timeout_sec=2.0, **kwargs
        )
        self.responses = list(responses or [])
        self.calls = []

    async def _post_json(self, url, payload):
        self.calls.append((url, payload))
        if not self.responses:
            return {}
        return self.responses.pop(0)


class TestAwsWafSolverSolve:
    @pytest.mark.asyncio
    async def test_success_returns_solved_cookie(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-aws-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {
                        "cookie": "aws-waf-token=ABC; Domain=.etix.com; Path=/",
                        "userAgent": "Mozilla/5.0 …",
                    },
                },
            ]
        )
        result = await solver.solve(
            website_url="https://www.etix.com/foo",
            user_agent="Mozilla/5.0 …",
        )
        assert isinstance(result, SolvedAwsWafCookie)
        assert result.cookie.startswith("aws-waf-token=ABC")
        assert result.user_agent == "Mozilla/5.0 …"
        # createTask + getTaskResult both called
        assert len(solver.calls) == 2
        assert solver.calls[0][0].endswith("/createTask")
        assert solver.calls[1][0].endswith("/getTaskResult")

    @pytest.mark.asyncio
    async def test_proxyless_task_type_when_no_proxy(self):
        # Default path uses AntiAwsWafTaskProxyless — capsolver's worker
        # fetches the challenge JS itself.
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookie": "aws-waf-token=v; Domain=.x.com"},
                },
            ]
        )
        await solver.solve(website_url="https://x.com/", user_agent="ua")
        create_payload = solver.calls[0][1]
        assert create_payload["task"]["type"] == "AntiAwsWafTaskProxyless"
        assert "proxy" not in create_payload["task"]

    @pytest.mark.asyncio
    async def test_proxied_task_type_when_proxy_provided(self):
        # AWS WAF binds the issued token to the solving IP, so a proxied
        # solve must use AntiAwsWafTask (not the proxyless variant).
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookie": "aws-waf-token=v; Domain=.x.com"},
                },
            ]
        )
        await solver.solve(
            website_url="https://x.com/",
            user_agent="ua",
            proxy_url="http://user:pass@proxy:3128",
        )
        create_payload = solver.calls[0][1]
        assert create_payload["task"]["type"] == "AntiAwsWafTask"
        assert create_payload["task"]["proxy"] == "http://user:pass@proxy:3128"

    @pytest.mark.asyncio
    async def test_create_task_error_raises(self):
        solver = _FakeSolver(
            responses=[
                {
                    "errorId": 1,
                    "errorCode": "ERROR_INVALID_TASK_DATA",
                    "errorDescription": "missing websiteURL",
                }
            ]
        )
        with pytest.raises(AwsWafSolverError) as excinfo:
            await solver.solve(
                website_url="https://www.etix.com/foo",
                user_agent="ua",
            )
        assert "missing websiteURL" in str(excinfo.value)

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
        with pytest.raises(AwsWafSolverError):
            await solver.solve(website_url="x", user_agent="x")

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        # All polls come back as 'processing' — solver must abort within
        # timeout_sec rather than spin.
        solver = _FakeSolver(
            responses=[{"errorId": 0, "taskId": "t-1"}]
            + [{"errorId": 0, "status": "processing"}] * 100
        )
        result = await solver.solve(website_url="x", user_agent="x")
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_task_id_returns_none(self):
        solver = _FakeSolver(responses=[{"errorId": 0}])
        result = await solver.solve(website_url="x", user_agent="x")
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_solution_cookie_returns_none(self):
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {"errorId": 0, "status": "ready", "solution": {}},
            ]
        )
        result = await solver.solve(website_url="x", user_agent="x")
        assert result is None

    @pytest.mark.asyncio
    async def test_bare_token_response_normalized_to_set_cookie_shape(self):
        # Live capsolver behaviour observed 2026-05-07: AntiAwsWafTaskProxyless
        # returns the raw token value (no ``aws-waf-token=`` prefix, no
        # Domain attribute). The solver must normalize so the downstream
        # parse_set_cookie call always sees a valid name=value form.
        raw_token = (
            "61cbd1a4-7d5d-49ea-8cf9-cbda57074e51:FAoAsc5i4nkKAAAA:"
            "signature_blob_here"
        )
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookie": raw_token},
                },
            ]
        )
        result = await solver.solve(website_url="https://x.com/", user_agent="ua")
        assert result is not None
        assert result.cookie.startswith(f"aws-waf-token={raw_token}")
        # Per the live capture on www.etix.com, AWS WAF expects the
        # cookie to carry Path/Secure/SameSite — without those
        # attributes the cookie is silently rejected on reload.
        assert "Path=/" in result.cookie
        assert "Secure" in result.cookie
        assert "SameSite=Lax" in result.cookie

    @pytest.mark.asyncio
    async def test_bare_token_with_base64_padding_is_still_normalized(self):
        # Regression for live debug 2026-05-07: capsolver's signature
        # tail is base64-encoded and frequently contains ``=`` padding
        # bytes. A naive ``"=" not in cookie`` check tripped on the
        # padding and skipped the prefix, leaving parse_set_cookie to
        # treat the entire token as a cookie *name* with empty value.
        # Detection must use the canonical name prefix instead.
        raw_token_with_padding = (
            "61cbd1a4-7d5d-49ea-8cf9-cbda57074e51:FAoAvV9l2pEBAAAA:"
            "zff177O6LL23R4TGgPOpzo/T1ceCImciGotE/uJncJF=="
        )
        assert "=" in raw_token_with_padding  # the trap

        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookie": raw_token_with_padding},
                },
            ]
        )
        result = await solver.solve(website_url="https://x.com/", user_agent="ua")
        assert result is not None
        # Must be prefixed despite the embedded ``=``.
        assert result.cookie.startswith(f"aws-waf-token={raw_token_with_padding}")
        # Sanity: parse_set_cookie now reads the right name/value.
        from laughtrack.foundation.infrastructure.http.protection.datadome_solver import (
            parse_set_cookie,
        )

        parsed = parse_set_cookie(result.cookie, default_domain="x.com")
        assert parsed is not None
        assert parsed["name"] == "aws-waf-token"
        assert parsed["value"] == raw_token_with_padding

    @pytest.mark.asyncio
    async def test_full_set_cookie_response_passed_through_unchanged(self):
        # When capsolver returns a full Set-Cookie string the solver
        # must NOT prepend its own name — that would produce a malformed
        # ``aws-waf-token=aws-waf-token=v`` value.
        full = "aws-waf-token=ABC; Domain=.x.com; Path=/"
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookie": full},
                },
            ]
        )
        result = await solver.solve(website_url="https://x.com/", user_agent="ua")
        assert result is not None
        assert result.cookie == full

    @pytest.mark.asyncio
    async def test_user_agent_threaded_into_task_payload(self):
        # DataDome bound the issued cookie to the UA used during solve;
        # AWS WAF doesn't have the same documented constraint, but the
        # solver passes UA through unchanged so the browser context and
        # capsolver send the same value if the operator chooses to.
        solver = _FakeSolver(
            responses=[
                {"errorId": 0, "taskId": "t-1"},
                {
                    "errorId": 0,
                    "status": "ready",
                    "solution": {"cookie": "aws-waf-token=v; Domain=.x.com"},
                },
            ]
        )
        await solver.solve(
            website_url="https://x.com/", user_agent="custom-ua-string"
        )
        create_payload = solver.calls[0][1]
        assert create_payload["task"]["userAgent"] == "custom-ua-string"

    def test_empty_api_key_rejected_at_construction(self):
        with pytest.raises(ValueError):
            AwsWafSolver("")
