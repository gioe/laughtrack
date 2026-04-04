"""
Shared fixtures for tests/core/entities/.

Registers the 'sql' package stub in sys.modules so that test-file module-level
imports (e.g. handler.py loading via importlib) can resolve sql.* submodule
references without a real installed package.
"""

import sys
from pathlib import Path
from types import ModuleType

import pytest

# apps/scraper/ — three parents up from tests/core/entities/conftest.py
_SCRAPER_ROOT = Path(__file__).parents[3]


def _register_sql_package_stub() -> None:
    """Register 'sql' as a package stub.

    Idempotent — if a 'sql' entry already exists in sys.modules with a
    __path__, it is left untouched.
    """
    sql_pkg = sys.modules.get("sql")
    if sql_pkg is None or not hasattr(sql_pkg, "__path__"):
        sql_pkg = ModuleType("sql")
        sql_pkg.__path__ = [str(_SCRAPER_ROOT / "sql")]
        sql_pkg.__package__ = "sql"
        sys.modules["sql"] = sql_pkg


# Called at collection time: conftest.py is imported before test files, so
# the stub is in place before any module-level _load_module() calls run.
_register_sql_package_stub()


@pytest.fixture(scope="session", autouse=True)
def sql_package_stub() -> None:
    """Session-scoped stub ensuring 'sql' is importable as a package.

    The module-level call above handles collection-time needs; this fixture
    covers any runtime imports that occur after collection is complete.
    """
    _register_sql_package_stub()
