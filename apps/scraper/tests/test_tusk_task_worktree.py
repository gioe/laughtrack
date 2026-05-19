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


def test_web_worktree_resources_are_linked_from_primary_checkout(tmp_path, monkeypatch):
    module = _load_module()
    primary = tmp_path / "primary"
    source_node_modules = primary / "apps" / "web" / "node_modules"
    source_node_modules.mkdir(parents=True)
    source_web_env = primary / "apps" / "web" / ".env.local"
    source_web_env.write_text("NEXTAUTH_SECRET=test\n")
    source_scraper_env = primary / "apps" / "scraper" / ".env"
    source_scraper_env.parent.mkdir(parents=True)
    source_scraper_env.write_text("DATABASE_HOST=example.test\n")

    workspace = tmp_path / "workspace"
    web_dir = workspace / "apps" / "web"
    scraper_dir = workspace / "apps" / "scraper"
    web_dir.mkdir(parents=True)
    scraper_dir.mkdir(parents=True)

    monkeypatch.setattr(
        module,
        "_run_git",
        lambda *_: SimpleNamespace(returncode=0, stdout=str(primary / ".git") + "\n"),
    )

    assert module._ensure_workspace_resources_available(
        str(workspace), str(workspace)
    ) == []

    linked_node_modules = web_dir / "node_modules"
    linked_web_env = web_dir / ".env.local"
    linked_scraper_env = scraper_dir / ".env"
    assert linked_node_modules.is_symlink()
    assert linked_node_modules.resolve() == source_node_modules
    assert linked_web_env.is_symlink()
    assert linked_web_env.resolve() == source_web_env
    assert linked_scraper_env.is_symlink()
    assert linked_scraper_env.resolve() == source_scraper_env


def test_web_resource_setup_leaves_existing_local_files_alone(tmp_path, monkeypatch):
    module = _load_module()
    primary = tmp_path / "primary"
    (primary / "apps" / "web" / "node_modules").mkdir(parents=True)
    source_web_env = primary / "apps" / "web" / ".env.local"
    source_web_env.write_text("NEXTAUTH_SECRET=primary\n")

    workspace = tmp_path / "workspace"
    existing_node_modules = workspace / "apps" / "web" / "node_modules"
    existing_node_modules.mkdir(parents=True)
    existing_web_env = workspace / "apps" / "web" / ".env.local"
    existing_web_env.write_text("NEXTAUTH_SECRET=workspace\n")

    monkeypatch.setattr(
        module,
        "_run_git",
        lambda *_: SimpleNamespace(returncode=0, stdout=str(primary / ".git") + "\n"),
    )

    assert module._ensure_workspace_resources_available(
        str(workspace), str(workspace)
    ) == []

    assert existing_node_modules.is_dir()
    assert not existing_node_modules.is_symlink()
    assert existing_web_env.read_text() == "NEXTAUTH_SECRET=workspace\n"
    assert not existing_web_env.is_symlink()
