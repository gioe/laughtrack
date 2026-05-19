"""
Root conftest for the scraper test suite.

Pre-imports real foundation modules so that module-level sys.modules.setdefault()
stubs in subdirectory conftest files (e.g. tests/core/entities/conftest.py) become
no-ops. Without this, the stub MagicMocks persist across the entire pytest session
and break tests that depend on the real Logger (test_logger_error_count,
test_validator, pipeline smoke tests).
"""

import os
import tempfile

# Redirect log files to a temp directory so test runs don't pollute the real
# app.log used by production scraping. Must be set before Logger.configure()
# is triggered by the imports below.
os.environ.setdefault("LAUGHTRACK_LOG_DIR", os.path.join(tempfile.gettempdir(), "laughtrack_test_logs"))

# Disable the Playwright fallback by default for the whole test session: any
# test that drives ``HttpClient.fetch_html`` / ``fetch_json`` through a mocked
# 4xx / bot-signature response would otherwise trigger ``_get_js_browser`` to
# import playwright and launch a real headless Chromium, blowing past the
# 30-second pytest-timeout budget. Tests that need to exercise the fallback
# (e.g. ``test_client.py`` Playwright suites) explicitly opt back in with
# ``monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "1")`` or by patching
# ``_get_js_browser`` directly with a fake browser — both still work because
# this is a ``setdefault`` and per-test overrides take precedence.
os.environ.setdefault("PLAYWRIGHT_FALLBACK", "0")

# Import the real Logger module chain — this populates sys.modules with the real
# modules BEFORE any test subdirectory conftest can register MagicMock stubs via
# setdefault(). Since setdefault() only sets if absent, these real entries win.
import laughtrack.foundation.infrastructure.logger.logger  # noqa: F401
import laughtrack.foundation.infrastructure.logger  # noqa: F401
import laughtrack.foundation.infrastructure  # noqa: F401
