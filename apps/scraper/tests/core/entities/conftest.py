"""
Shared fixtures and helpers for tests/core/entities/.

Registers the 'sql' package stub, psycopg2 stub, all foundation/utilities
stubs, and _BaseDatabaseHandlerStub in sys.modules so that test-file module-level
imports (e.g. handler.py loading via importlib) can resolve dependencies without
a live DB environment.
"""

import importlib.util
import sys
from abc import ABC as _ABC, abstractmethod as _abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Generic as _Generic, TypeVar as _TypeVar
from unittest.mock import MagicMock

import pytest

# apps/scraper/ — three parents up from tests/core/entities/conftest.py
_SCRAPER_ROOT = Path(__file__).parents[3]


# ---------------------------------------------------------------------------
# Shared helpers (importable by test files in this directory via
# `from conftest import _load_module, _stub, ...`)
# ---------------------------------------------------------------------------

def _load_module(rel_path: str, module_name: str):
    """Import a single .py file as a module without triggering __init__.py chains."""
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


def _ensure_psycopg2_stubbed():
    if "psycopg2" not in sys.modules:
        psycopg2 = ModuleType("psycopg2")
        extras = ModuleType("psycopg2.extras")
        extras.DictRow = dict  # type: ignore[attr-defined]
        extras.execute_values = MagicMock()
        extensions = ModuleType("psycopg2.extensions")
        extensions.connection = object  # type: ignore[attr-defined]
        psycopg2.extras = extras  # type: ignore[attr-defined]
        psycopg2.extensions = extensions  # type: ignore[attr-defined]
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = extras
        sys.modules["psycopg2.extensions"] = extensions


def _stub(name: str, as_package: bool = False, **attrs):
    m = ModuleType(name)
    if as_package:
        pkg_path = str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))
        m.__path__ = [pkg_path]
        m.__package__ = name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


# ---------------------------------------------------------------------------
# sql package stub (extracted in TASK-921)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# psycopg2 stub — registered before any module-level _load_module() calls
# ---------------------------------------------------------------------------

_ensure_psycopg2_stubbed()

# ---------------------------------------------------------------------------
# Foundation / utilities stubs
# ---------------------------------------------------------------------------

_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", as_package=True, DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", as_package=True, Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure", as_package=True, Logger=MagicMock())
_stub("laughtrack.foundation.utilities.popularity.scorer", PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.popularity", as_package=True, PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.string", StringUtils=MagicMock())
_stub("laughtrack.foundation.utilities", as_package=True, StringUtils=MagicMock())
_stub("laughtrack.foundation", as_package=True, DatabaseEntity=object)
_stub("laughtrack.utilities.domain.comedian.utils", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.comedian", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.utilities", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.foundation.infrastructure.database", as_package=True, BatchTemplateGenerator=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.template", BatchTemplateGenerator=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())

# ---------------------------------------------------------------------------
# _BaseDatabaseHandlerStub — minimal stand-in for BaseDatabaseHandler
# ---------------------------------------------------------------------------

_T_stub = _TypeVar("_T_stub")


class _BaseDatabaseHandlerStub(_Generic[_T_stub], _ABC):
    """Minimal stand-in for BaseDatabaseHandler used only during module loading."""

    def __init__(self) -> None:
        pass

    @_abstractmethod
    def get_entity_name(self) -> str: ...

    @_abstractmethod
    def get_entity_class(self): ...

    def execute_with_cursor(self, operation, params=None, return_results=False):
        raise NotImplementedError  # always patched in tests

    def execute_batch_operation(self, query, items, template=None, return_results=False, log_summary=True):
        raise NotImplementedError  # always patched in tests

    def _get_cursor_factory(self):
        return dict


_stub("laughtrack.core.data.base_handler", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.data", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.entities", as_package=True, Comedian=None)
_stub("laughtrack.core.entities.comedian", as_package=True, Comedian=None)

# ---------------------------------------------------------------------------
# Load false_positive_detector once — required by handler.py's relative import
# ---------------------------------------------------------------------------

_load_module(
    "src/laughtrack/core/entities/comedian/false_positive_detector.py",
    "laughtrack.core.entities.comedian.false_positive_detector",
)

# ---------------------------------------------------------------------------
# sql package stub — called at collection time so it's in place before test
# files run their module-level _load_module() calls
# ---------------------------------------------------------------------------

_register_sql_package_stub()


@pytest.fixture(scope="session", autouse=True)
def sql_package_stub() -> None:
    """Session-scoped stub ensuring 'sql' is importable as a package.

    The module-level call above handles collection-time needs; this fixture
    covers any runtime imports that occur after collection is complete.
    """
    _register_sql_package_stub()


# ---------------------------------------------------------------------------
# Register helpers under a unique sys.modules key so test files in this
# directory can do `from _entities_test_helpers import _load_module` without
# relying on sys.path ordering (which can pick up other conftest.py files
# when the full test suite is collected from the repo root).
# ---------------------------------------------------------------------------

_helpers_mod = ModuleType("_entities_test_helpers")
_helpers_mod._load_module = _load_module  # type: ignore[attr-defined]
_helpers_mod._stub = _stub  # type: ignore[attr-defined]
_helpers_mod._ensure_psycopg2_stubbed = _ensure_psycopg2_stubbed  # type: ignore[attr-defined]
_helpers_mod._BaseDatabaseHandlerStub = _BaseDatabaseHandlerStub  # type: ignore[attr-defined]
sys.modules.setdefault("_entities_test_helpers", _helpers_mod)
