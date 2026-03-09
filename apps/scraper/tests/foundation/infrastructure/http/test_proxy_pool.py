"""Unit tests for ProxyPool."""

import os
import tempfile
from unittest.mock import patch

import pytest

from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool


PROXY_A = "http://proxy-a:8080"
PROXY_B = "http://proxy-b:8080"
PROXY_C = "http://proxy-c:8080"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestProxyPoolInit:
    def test_raises_on_empty_list(self):
        with pytest.raises(ValueError):
            ProxyPool(proxies=[])

    def test_active_proxies_match_input(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B])
        assert pool.active_proxies == [PROXY_A, PROXY_B]

    def test_rotation_default_is_per_request(self):
        pool = ProxyPool(proxies=[PROXY_A])
        assert pool.rotation == ProxyPool.PER_REQUEST


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------


class TestProxyPoolFromEnv:
    def test_returns_none_when_env_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SCRAPER_PROXY_LIST", None)
            result = ProxyPool.from_env()
        assert result is None

    def test_returns_none_when_env_empty(self):
        with patch.dict(os.environ, {"SCRAPER_PROXY_LIST": "  "}):
            result = ProxyPool.from_env()
        assert result is None

    def test_parses_comma_separated_proxies(self):
        with patch.dict(os.environ, {"SCRAPER_PROXY_LIST": f"{PROXY_A},{PROXY_B}"}):
            pool = ProxyPool.from_env()
        assert pool is not None
        assert pool.active_proxies == [PROXY_A, PROXY_B]

    def test_parses_comma_list_with_spaces(self):
        with patch.dict(os.environ, {"SCRAPER_PROXY_LIST": f" {PROXY_A} , {PROXY_B} "}):
            pool = ProxyPool.from_env()
        assert pool is not None
        assert pool.active_proxies == [PROXY_A, PROXY_B]

    def test_reads_from_file_path(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
            fh.write(f"{PROXY_A}\n{PROXY_B}\n\n")
            tmp_path = fh.name

        try:
            with patch.dict(os.environ, {"SCRAPER_PROXY_LIST": tmp_path}):
                pool = ProxyPool.from_env()
        finally:
            os.unlink(tmp_path)

        assert pool is not None
        assert pool.active_proxies == [PROXY_A, PROXY_B]

    def test_returns_none_when_file_has_no_valid_proxies(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
            fh.write("\n\n")
            tmp_path = fh.name

        try:
            with patch.dict(os.environ, {"SCRAPER_PROXY_LIST": tmp_path}):
                result = ProxyPool.from_env()
        finally:
            os.unlink(tmp_path)

        assert result is None

    def test_custom_env_var_name(self):
        with patch.dict(os.environ, {"MY_PROXIES": PROXY_A}):
            pool = ProxyPool.from_env(env_var="MY_PROXIES")
        assert pool is not None
        assert pool.active_proxies == [PROXY_A]


# ---------------------------------------------------------------------------
# Per-request rotation
# ---------------------------------------------------------------------------


class TestPerRequestRotation:
    def test_get_proxy_returns_first_proxy(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], rotation=ProxyPool.PER_REQUEST)
        assert pool.get_proxy() == PROXY_A

    def test_successive_calls_rotate(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], rotation=ProxyPool.PER_REQUEST)
        assert pool.get_proxy() == PROXY_A
        assert pool.get_proxy() == PROXY_B

    def test_rotation_wraps_around(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], rotation=ProxyPool.PER_REQUEST)
        pool.get_proxy()  # A
        pool.get_proxy()  # B
        assert pool.get_proxy() == PROXY_A  # wraps

    def test_single_proxy_always_returns_same(self):
        pool = ProxyPool(proxies=[PROXY_A], rotation=ProxyPool.PER_REQUEST)
        for _ in range(5):
            assert pool.get_proxy() == PROXY_A


# ---------------------------------------------------------------------------
# Per-session rotation
# ---------------------------------------------------------------------------


class TestPerSessionRotation:
    def test_get_proxy_same_without_rotate(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], rotation=ProxyPool.PER_SESSION)
        assert pool.get_proxy() == PROXY_A
        assert pool.get_proxy() == PROXY_A  # stays on A

    def test_rotate_advances_proxy(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], rotation=ProxyPool.PER_SESSION)
        assert pool.get_proxy() == PROXY_A
        pool.rotate()
        assert pool.get_proxy() == PROXY_B

    def test_rotate_wraps_around(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], rotation=ProxyPool.PER_SESSION)
        pool.rotate()  # → B
        pool.rotate()  # → A
        assert pool.get_proxy() == PROXY_A


# ---------------------------------------------------------------------------
# Failure tracking and retirement
# ---------------------------------------------------------------------------


class TestFailureTracking:
    def test_report_failure_increments_count(self):
        pool = ProxyPool(proxies=[PROXY_A], max_failures=3)
        pool.report_failure(PROXY_A)
        assert pool._failure_counts[PROXY_A] == 1

    def test_proxy_retired_after_max_failures(self):
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], max_failures=2)
        pool.report_failure(PROXY_A)
        pool.report_failure(PROXY_A)
        assert PROXY_A in pool._retired
        assert pool.active_proxies == [PROXY_B]

    def test_report_success_decrements_count(self):
        pool = ProxyPool(proxies=[PROXY_A], max_failures=3)
        pool.report_failure(PROXY_A)
        pool.report_failure(PROXY_A)
        pool.report_success(PROXY_A)
        assert pool._failure_counts[PROXY_A] == 1

    def test_report_success_does_not_go_below_zero(self):
        pool = ProxyPool(proxies=[PROXY_A], max_failures=3)
        pool.report_success(PROXY_A)
        pool.report_success(PROXY_A)
        assert pool._failure_counts[PROXY_A] == 0

    def test_get_proxy_returns_none_when_all_retired(self):
        pool = ProxyPool(proxies=[PROXY_A], max_failures=1)
        pool.report_failure(PROXY_A)
        assert pool.get_proxy() is None

    def test_scraper_keeps_running_with_remaining_proxy(self):
        """Retiring one proxy does not crash — remaining pool still serves requests."""
        pool = ProxyPool(proxies=[PROXY_A, PROXY_B], max_failures=1)
        pool.report_failure(PROXY_A)
        # PROXY_A retired; pool still returns PROXY_B
        assert pool.get_proxy() == PROXY_B

    def test_retired_proxy_not_re_retired(self):
        """Extra failures on an already-retired proxy don't raise."""
        pool = ProxyPool(proxies=[PROXY_A], max_failures=1)
        pool.report_failure(PROXY_A)
        pool.report_failure(PROXY_A)  # should not raise
        assert PROXY_A in pool._retired


# ---------------------------------------------------------------------------
# No-proxy passthrough (SCRAPER_PROXY_LIST unset)
# ---------------------------------------------------------------------------


class TestNoProxy:
    def test_from_env_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("SCRAPER_PROXY_LIST", raising=False)
        pool = ProxyPool.from_env()
        assert pool is None

    def test_none_pool_means_no_proxy_injected(self, monkeypatch):
        """Callers treat None pool as 'no proxy' — no ProxyPool created."""
        monkeypatch.delenv("SCRAPER_PROXY_LIST", raising=False)
        pool = ProxyPool.from_env()
        # Caller pattern: proxy_url = pool.get_proxy() if pool else None
        proxy_url = pool.get_proxy() if pool else None
        assert proxy_url is None
