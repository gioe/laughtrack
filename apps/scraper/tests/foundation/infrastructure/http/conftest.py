"""Per-test reset hooks for HTTP-layer tests.

The HttpClient module keeps a per-process cache of hostnames whose Playwright
fallback confirmed a bot-block (``_recent_bot_blocked_hosts``). Tests that
exercise the fallback path add the host to that cache as a side effect, so
without an explicit reset the next test that hits the same host (almost
always "example.com") short-circuits Playwright and gets a different code
path than it expected. Auto-reset prevents that test-ordering coupling.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_http_client_bot_block_cache():
    import laughtrack.foundation.infrastructure.http.client as client_module
    client_module._reset_bot_block_shortcircuit()
    yield
    client_module._reset_bot_block_shortcircuit()
