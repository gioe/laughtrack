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

# ---------------------------------------------------------------------------
# Frozen-clock fixture-rot sweep (TASK-3593, convention 309).
#
# When FAKE_NOW is set, the whole pytest session runs under a time-machine
# frozen clock so fixture dates that rot with the wall clock (past-drop
# filters, wall-clock year inference, DST-window assumptions) fail *now*
# instead of on some future nightly. Inert when FAKE_NOW is unset — normal
# runs never import time_machine. Accepted forms:
#
#   FAKE_NOW="2027-03-15T12:00:00+00:00"   absolute ISO datetime
#   FAKE_NOW="+240d"                        relative offset in days from now
#
# Run via `make test-frozen` locally or the scraper-frozen-clock GHA job.
# ---------------------------------------------------------------------------

_time_traveller = None


def _resolve_fake_now(raw: str):
    from datetime import datetime, timedelta, timezone

    if raw.startswith("+") and raw.endswith("d"):
        return datetime.now(timezone.utc) + timedelta(days=int(raw[1:-1]))
    return raw  # time_machine parses ISO strings itself


def pytest_configure(config):
    global _time_traveller
    raw = os.environ.get("FAKE_NOW")
    if not raw:
        return
    import time_machine

    _time_traveller = time_machine.travel(_resolve_fake_now(raw), tick=True)
    _time_traveller.start()
    from datetime import datetime, timezone

    print(f"\nFAKE_NOW={raw} — session clock frozen at {datetime.now(timezone.utc).isoformat()} (fixture-rot sweep)")


def pytest_unconfigure(config):
    global _time_traveller
    if _time_traveller is not None:
        _time_traveller.stop()
        _time_traveller = None
