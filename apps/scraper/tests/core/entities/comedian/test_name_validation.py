"""Tests for comedian false-positive name validation."""

import sys
from unittest.mock import MagicMock

import pytest

from _entities_test_helpers import _load_module


_comedian_model_mod = _load_module(
    "src/laughtrack/core/entities/comedian/model.py",
    "laughtrack.core.entities.comedian.model_direct",
)
Comedian = _comedian_model_mod.Comedian

_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_direct")

sys.modules.setdefault("laughtrack.core.entities.comedian.model", _comedian_model_mod)
sys.modules.setdefault("sql.comedian_queries", _comedian_queries_mod)

_false_positive_mod = _load_module(
    "src/laughtrack/core/entities/comedian/false_positive_detector.py",
    "laughtrack.core.entities.comedian.false_positive_detector",
)
detect_false_positive = _false_positive_mod.detect_false_positive

_comedian_handler_mod = _load_module(
    "src/laughtrack/core/entities/comedian/handler.py",
    "laughtrack.core.entities.comedian.handler_direct",
)
ComedianHandler = _comedian_handler_mod.ComedianHandler


def _make_comedian(name: str) -> Comedian:
    comedian = Comedian.__new__(Comedian)
    comedian.name = name
    comedian.uuid = f"uuid-{name.lower().replace(' ', '-')}"
    comedian.sold_out_shows = 0
    comedian.total_shows = 0
    return comedian


@pytest.mark.parametrize(
    "name",
    [
        "Music",
        "More",
        "Best of",
        "The",
        "Show",
        "Live",
        "Drag",
        "Sketch",
        "ComedySportz",
        "Laughs",
        "Alex",
        "Blue",
        "Down",
        "LOVE",
        "Columbus",
        "JESSICA",
        "Paranormal",
    ],
)
def test_validator_rejects_generic_comedian_name_fragments(name: str):
    assert detect_false_positive(name) is not None


def test_comedian_write_boundary_does_not_insert_generic_fragment():
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock()
    handler.execute_batch_operation = MagicMock()

    result = handler.insert_comedians([_make_comedian("Music")])

    assert result == []
    handler.execute_batch_operation.assert_not_called()


def test_comedian_write_boundary_still_inserts_valid_name():
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock(return_value=[])
    handler.execute_batch_operation = MagicMock(return_value=[{"uuid": "uuid-real-comic"}])

    result = handler.insert_comedians([_make_comedian("Real Comic")])

    assert result == [{"uuid": "uuid-real-comic"}]
    handler.execute_batch_operation.assert_called_once()
