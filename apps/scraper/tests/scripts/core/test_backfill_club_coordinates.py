"""Operational coordinate CLI uses the shared scheduler and defaults to preview."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

SCRAPER_ROOT = Path(__file__).resolve().parents[3]
if str(SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPER_ROOT))

from scripts.core import backfill_club_coordinates as cli  # noqa: E402


def test_help_imports_real_shared_api_without_database_or_provider_access():
    env = dict(os.environ, PYTHONPATH=f"{SCRAPER_ROOT / 'src'}:{SCRAPER_ROOT}")
    result = subprocess.run(
        [sys.executable, str(SCRAPER_ROOT / "scripts/core/backfill_club_coordinates.py"), "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "--apply" in result.stdout
    assert "default: 30" in result.stdout


def test_default_preview_never_calls_mutating_enrichment(monkeypatch, capsys):
    preview = Mock(return_value=[SimpleNamespace(id=7, name="The Club", address="1 Main St", zip_code="10001")])
    apply = Mock(side_effect=AssertionError("dry-run must not invoke provider or persistence"))
    monkeypatch.setattr(cli.coordinates, "preview_missing_clubs", preview)
    monkeypatch.setattr(cli.coordinates, "geocode_missing_clubs", apply)

    assert cli.main([]) == 0
    preview.assert_called_once_with(limit=30)
    apply.assert_not_called()
    assert "club 7" in capsys.readouterr().out


def test_apply_delegates_limit_to_shared_enrichment(monkeypatch, capsys):
    apply = Mock(return_value=SimpleNamespace(attempted=5, resolved=3, unresolved=2, failed=0, retried=1, skipped=0))
    preview = Mock(side_effect=AssertionError("apply must use shared enrichment directly"))
    monkeypatch.setattr(cli.coordinates, "preview_missing_clubs", preview)
    monkeypatch.setattr(cli.coordinates, "geocode_missing_clubs", apply)

    assert cli.main(["--apply", "--limit", "5"]) == 0
    apply.assert_called_once_with(limit=5)
    preview.assert_not_called()
    assert "attempted=5 resolved=3 unresolved=2" in capsys.readouterr().out


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_invalid_limit_rejected_before_database_access(monkeypatch, limit):
    preview = Mock(side_effect=AssertionError("invalid argument must not access database"))
    monkeypatch.setattr(cli.coordinates, "preview_missing_clubs", preview)
    with pytest.raises(SystemExit) as exc:
        cli.main(["--limit", limit])
    assert exc.value.code == 2
    preview.assert_not_called()
