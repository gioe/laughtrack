"""
Shared gioe_libs stub registration for all test directories.

Stubs gioe_libs.rate_limiter and gioe_libs.string_utils so tests can import
laughtrack code without requiring the optional gioe_libs dependency to be
installed. Also stubs laughtrack.utilities.infrastructure to bypass its
__init__.py.

Usage in a per-directory conftest.py:

    from pathlib import Path
    from gioe_stubs import register_stubs
    register_stubs(Path(__file__).parents[N] / "src")

Where N is the number of parent hops from the conftest file to apps/scraper/:
    tests/<dir>/conftest.py          → parents[2]
    tests/scrapers/<dir>/conftest.py → parents[3]
    tests/scrapers/implementations/venues/conftest.py → parents[4]

Uses sys.modules.setdefault() throughout — safe if stubs were already
registered by a parent conftest; no-op if already present.
"""

import sys
import asyncio
import time as _time_mod
from pathlib import Path
from types import ModuleType


class _FakeRateLimiter:
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


def _load_string_utils() -> object:
    """Return the real StringUtils if gioe_libs is installed, else MagicMock."""
    import importlib.util as _ilu

    try:
        spec = _ilu.find_spec("gioe_libs.string_utils")
    except (ModuleNotFoundError, ValueError):
        spec = None
    if spec:
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.StringUtils
    from unittest.mock import MagicMock
    return MagicMock


def register_stubs(scraper_src: Path) -> None:
    """
    Register gioe_libs submodule stubs and the laughtrack.utilities.infrastructure
    path stub into sys.modules.

    Args:
        scraper_src: Path to the scraper's src/ directory
                     (e.g. Path(__file__).parents[N] / "src").
    """
    # gioe_libs.rate_limiter stub
    _gioe_rl = ModuleType("gioe_libs.rate_limiter")
    _gioe_rl.RateLimiter = _FakeRateLimiter  # type: ignore[attr-defined]

    # gioe_libs.string_utils — real implementation if available, MagicMock otherwise
    _gioe_su = ModuleType("gioe_libs.string_utils")
    _gioe_su.StringUtils = _load_string_utils()  # type: ignore[attr-defined]

    # gioe_libs root module
    _gioe_mod = ModuleType("gioe_libs")

    sys.modules.setdefault("gioe_libs", _gioe_mod)
    sys.modules.setdefault("gioe_libs.rate_limiter", _gioe_rl)
    sys.modules.setdefault("gioe_libs.string_utils", _gioe_su)

    # laughtrack.utilities.infrastructure — stub to bypass __init__.py while
    # still allowing submodule imports by pointing __path__ at the real source.
    _infra_stub = sys.modules.get("laughtrack.utilities.infrastructure")
    if _infra_stub is None:
        _infra_stub = ModuleType("laughtrack.utilities.infrastructure")
        _infra_stub.__path__ = [str(scraper_src / "laughtrack/utilities/infrastructure")]
        _infra_stub.__package__ = "laughtrack.utilities.infrastructure"
        sys.modules["laughtrack.utilities.infrastructure"] = _infra_stub

    if not hasattr(_infra_stub, "RateLimiter"):
        from laughtrack.utilities.infrastructure.rate_limiter import RateLimiter as _RL
        _infra_stub.RateLimiter = _RL  # type: ignore[attr-defined]
