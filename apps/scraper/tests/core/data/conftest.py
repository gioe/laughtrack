"""
Shared fixtures and helpers for tests/core/data/.

Registers the psycopg2 and data-layer stubs needed to import base_handler.py
directly without requiring a live DB environment.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

# apps/scraper/ -> three parents up from tests/core/data/conftest.py
_SCRAPER_ROOT = Path(__file__).parents[3]


def _ensure_psycopg2_stubbed():
    if "psycopg2" not in sys.modules:
        psycopg2 = ModuleType("psycopg2")
        extras = ModuleType("psycopg2.extras")
        extras.DictRow = dict
        extras.execute_values = MagicMock()
        extensions = ModuleType("psycopg2.extensions")
        extensions.connection = object
        psycopg2.extras = extras
        psycopg2.extensions = extensions
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = extras
        sys.modules["psycopg2.extensions"] = extensions


def _stub(name, as_package=False, **attrs):
    m = ModuleType(name)
    if as_package:
        pkg_path = str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))
        m.__path__ = [pkg_path]
        m.__package__ = name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


def _load_module(rel_path, module_name):
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(module_name, mod)
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


_ensure_psycopg2_stubbed()

_mock_logger = MagicMock()
_mock_db_op_logger = MagicMock()

_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=_mock_logger)
_stub("laughtrack.foundation.infrastructure.logger", as_package=True, Logger=_mock_logger)
_stub("laughtrack.foundation.infrastructure", as_package=True)
_stub("laughtrack.foundation.infrastructure.database", as_package=True)
_stub(
    "laughtrack.foundation.infrastructure.database.operation",
    DatabaseOperationLogger=_mock_db_op_logger,
)
_stub("laughtrack.foundation.models.types", T=None, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True)
_stub("laughtrack.foundation", as_package=True)

# Stub adapters.db so base_handler.py's import resolves. Include all names
# re-exported by the real module so downstream collectors do not get ImportError
# if this stub is already in sys.modules.
_stub(
    "laughtrack.adapters.db",
    create_connection=MagicMock(),
    create_connection_with_transaction=MagicMock(),
    get_connection=MagicMock(),
    get_transaction=MagicMock(),
    db=MagicMock(),
)
_stub("laughtrack.adapters", as_package=True)
_stub("laughtrack", as_package=True)

_base_handler_mod = _load_module(
    "src/laughtrack/core/data/base_handler.py",
    "laughtrack.core.data.base_handler_test_isolated",
)
_base_handler_mod.Logger = _mock_logger
_base_handler_mod.DatabaseOperationLogger = _mock_db_op_logger
BaseDatabaseHandler = _base_handler_mod.BaseDatabaseHandler

_operation_mod = _load_module(
    "src/laughtrack/foundation/infrastructure/database/operation.py",
    "laughtrack.foundation.infrastructure.database.operation_test_isolated",
)
_operation_mod.Logger = _mock_logger
DatabaseOperationLogger = _operation_mod.DatabaseOperationLogger

_helpers_mod = ModuleType("_core_data_test_helpers")
_helpers_mod.BaseDatabaseHandler = BaseDatabaseHandler  # type: ignore[attr-defined]
_helpers_mod.DatabaseOperationLogger = DatabaseOperationLogger  # type: ignore[attr-defined]
_helpers_mod._base_handler_mod = _base_handler_mod  # type: ignore[attr-defined]
_helpers_mod._mock_db_op_logger = _mock_db_op_logger  # type: ignore[attr-defined]
_helpers_mod._mock_logger = _mock_logger  # type: ignore[attr-defined]
sys.modules.setdefault("_core_data_test_helpers", _helpers_mod)
