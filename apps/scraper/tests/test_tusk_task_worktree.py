import importlib.util
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / ".claude" / "bin" / "tusk-task-worktree.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tusk_task_worktree", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_scraper_venv_is_linked_from_primary_checkout(tmp_path, monkeypatch):
    module = _load_module()
    primary = tmp_path / "primary"
    source_venv = primary / "apps" / "scraper" / ".venv"
    source_venv.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    scraper_dir = workspace / "apps" / "scraper"
    scraper_dir.mkdir(parents=True)

    monkeypatch.setattr(
        module,
        "_run_git",
        lambda *_: SimpleNamespace(returncode=0, stdout=str(primary / ".git") + "\n"),
    )

    assert module._ensure_scraper_venv_available(str(workspace), str(workspace)) is None

    linked_venv = scraper_dir / ".venv"
    assert linked_venv.is_symlink()
    assert linked_venv.resolve() == source_venv


def test_scraper_venv_setup_leaves_existing_venv_alone(tmp_path, monkeypatch):
    module = _load_module()
    primary = tmp_path / "primary"
    (primary / "apps" / "scraper" / ".venv").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    existing_venv = workspace / "apps" / "scraper" / ".venv"
    existing_venv.mkdir(parents=True)

    monkeypatch.setattr(
        module,
        "_run_git",
        lambda *_: SimpleNamespace(returncode=0, stdout=str(primary / ".git") + "\n"),
    )

    assert module._ensure_scraper_venv_available(str(workspace), str(workspace)) is None

    assert existing_venv.is_dir()
    assert not existing_venv.is_symlink()
