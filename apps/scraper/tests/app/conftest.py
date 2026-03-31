"""
Shared test fixtures for app/ tests.

Pre-stubs gioe_libs (optional private dep not in requirements.txt) and
bypasses laughtrack.utilities.infrastructure.__init__ so that scrapers can be
imported without triggering the gioe_libs dependency chain.

Uses sys.modules.setdefault() throughout — safe if other conftest.py files or
test_rate_limiter.py register the same stubs first; no-op if already present.
"""

import sys
import asyncio
import time as _time_mod
from pathlib import Path
from types import ModuleType

# ---------------------------------------------------------------------------
# Stub gioe_libs — must be registered before any laughtrack import that
# transitively loads rate_limiter.py (e.g. via BaseScraper → RateLimiter).
# ---------------------------------------------------------------------------


class _FakeBaseRateLimiter:
    """Minimal async-compatible RPS slot-reservation stub."""

    def __init__(self) -> None:
        self._last_request: dict = {}
        self._rps: dict = {}
        self._lock = asyncio.Lock()

    def configure(self, domain: str, rps: float) -> None:
        self._rps[domain] = rps

    async def await_if_needed(self, domain: str) -> None:
        min_interval = 1.0 / self._rps.get(domain, 1.0)
        async with self._lock:
            now = _time_mod.time()
            last = self._last_request.get(domain, now - min_interval)
            next_slot = max(now, last + min_interval)
            self._last_request[domain] = next_slot

    def wait_if_needed(self, domain: str) -> None:
        pass

    def reset(self, domain: str) -> None:
        self._last_request.pop(domain, None)

    def get_stats(self) -> dict:
        now = _time_mod.time()
        return {
            d: {"last_request": t, "time_since_last": now - t}
            for d, t in self._last_request.items()
        }


_gioe_rl = ModuleType("gioe_libs.rate_limiter")
_gioe_rl.RateLimiter = _FakeBaseRateLimiter  # type: ignore[attr-defined]
# Load real StringUtils before registering gioe_libs stub (gioe_libs.string_utils is pure stdlib)
import importlib.util as _ilu
_su_spec = _ilu.find_spec("gioe_libs.string_utils")
if _su_spec:
    _su_mod = _ilu.module_from_spec(_su_spec)
    _su_spec.loader.exec_module(_su_mod)
    _RealStringUtils = _su_mod.StringUtils
else:
    from unittest.mock import MagicMock as _MagicMock
    _RealStringUtils = _MagicMock
_gioe_su = ModuleType("gioe_libs.string_utils")
_gioe_su.StringUtils = _RealStringUtils  # type: ignore[attr-defined]
_gioe_mod = ModuleType("gioe_libs")
sys.modules.setdefault("gioe_libs", _gioe_mod)
sys.modules.setdefault("gioe_libs.rate_limiter", _gioe_rl)
sys.modules.setdefault("gioe_libs.string_utils", _gioe_su)


# ---------------------------------------------------------------------------
# Pre-stub laughtrack.utilities.infrastructure so __init__.py doesn't run.
# Setting __path__ to the real source directory lets Python find submodules
# (rate_limiter, domain_config, error_handling, etc.) on disk.
# ---------------------------------------------------------------------------

# tests/app/ → parents[2] = apps/scraper/
_SCRAPER_SRC = Path(__file__).parents[2] / "src"
_infra_stub = ModuleType("laughtrack.utilities.infrastructure")
_infra_stub.__path__ = [str(_SCRAPER_SRC / "laughtrack/utilities/infrastructure")]
_infra_stub.__package__ = "laughtrack.utilities.infrastructure"
sys.modules.setdefault("laughtrack.utilities.infrastructure", _infra_stub)

# Populate the stub with commonly imported names so that
# `from laughtrack.utilities.infrastructure import RateLimiter` succeeds.
# gioe_libs is already stubbed above, so these imports won't fail.
if not hasattr(_infra_stub, "RateLimiter"):
    from laughtrack.utilities.infrastructure.rate_limiter import RateLimiter as _RL
    _infra_stub.RateLimiter = _RL  # type: ignore[attr-defined]
