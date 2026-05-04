"""Tests for the scraper_proxy_registry module.

The HttpClient routing tests in ``test_client_proxy.py`` stub
``proxy_enabled_keys()`` directly so the routing layer can be exercised in
isolation. This file covers the registry's own DB plumbing — specifically the
degraded-DB path that promises to return an empty frozenset and emit a WARN
rather than crash the nightly run when Postgres is unavailable.
"""

from unittest.mock import patch

import pytest

from laughtrack.foundation.infrastructure.http import scraper_proxy_registry


@pytest.fixture(autouse=True)
def _reset_registry_cache():
    scraper_proxy_registry.reset_cache()
    yield
    scraper_proxy_registry.reset_cache()


class TestLoadFromDbDegrades:
    def test_db_error_returns_empty_frozenset(self):
        """A failed DB query must not propagate — return empty so the run continues."""
        with patch(
            "laughtrack.infrastructure.database.connection.create_connection",
            side_effect=Exception("simulated DB outage"),
        ):
            with patch(
                "laughtrack.foundation.infrastructure.http.scraper_proxy_registry.Logger.warn"
            ):
                result = scraper_proxy_registry.proxy_enabled_keys()

        assert result == frozenset()

    def test_db_error_logs_warn_with_registry_prefix(self):
        """On-call greps for the '[ScraperProxyRegistry]' marker — pin the prefix."""
        with patch(
            "laughtrack.infrastructure.database.connection.create_connection",
            side_effect=RuntimeError("boom"),
        ):
            with patch(
                "laughtrack.foundation.infrastructure.http.scraper_proxy_registry.Logger.warn"
            ) as mock_warn:
                scraper_proxy_registry.proxy_enabled_keys()

        assert mock_warn.called
        msg = mock_warn.call_args[0][0]
        assert "[ScraperProxyRegistry]" in msg
        assert "boom" in msg

    def test_cache_holds_after_failure_so_we_dont_retry_per_fetch(self):
        """One DB failure is one WARN — subsequent calls must not re-attempt the query.

        The registry is consulted on every fetch decision; if the failure path
        re-tried the DB each time, a Neon outage would amplify into thousands
        of failed queries plus a WARN flood.
        """
        with patch(
            "laughtrack.infrastructure.database.connection.create_connection",
            side_effect=Exception("boom"),
        ) as mock_create:
            with patch(
                "laughtrack.foundation.infrastructure.http.scraper_proxy_registry.Logger.warn"
            ):
                scraper_proxy_registry.proxy_enabled_keys()
                scraper_proxy_registry.proxy_enabled_keys()
                scraper_proxy_registry.proxy_enabled_keys()

        assert mock_create.call_count == 1
