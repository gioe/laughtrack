"""
Unit tests for gioe_stubs._load_string_utils() exception-handling paths.

The function must return MagicMock when importlib.util.find_spec() raises
PermissionError, ModuleNotFoundError, or ValueError — not just when it
returns None (package not installed).
"""

import importlib.util
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_and_call() -> object:
    """Re-import gioe_stubs fresh and call _load_string_utils()."""
    # Remove cached module so the import runs from scratch each time.
    sys.modules.pop("gioe_stubs", None)
    import gioe_stubs  # noqa: PLC0415
    return gioe_stubs._load_string_utils()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoadStringUtils:
    def test_returns_magic_mock_on_permission_error(self):
        """find_spec() raising PermissionError → MagicMock returned."""
        with patch.object(importlib.util, "find_spec", side_effect=PermissionError("sandbox")):
            result = _reload_and_call()
        assert result is MagicMock

    def test_returns_magic_mock_on_module_not_found_error(self):
        """find_spec() raising ModuleNotFoundError → MagicMock returned."""
        with patch.object(importlib.util, "find_spec", side_effect=ModuleNotFoundError("gioe_libs")):
            result = _reload_and_call()
        assert result is MagicMock

    def test_returns_magic_mock_on_value_error(self):
        """find_spec() raising ValueError → MagicMock returned."""
        with patch.object(importlib.util, "find_spec", side_effect=ValueError("bad value")):
            result = _reload_and_call()
        assert result is MagicMock

    def test_returns_magic_mock_when_spec_is_none(self):
        """find_spec() returning None (package not installed) → MagicMock returned."""
        with patch.object(importlib.util, "find_spec", return_value=None):
            result = _reload_and_call()
        assert result is MagicMock
