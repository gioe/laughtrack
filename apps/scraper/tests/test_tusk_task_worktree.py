"""Tests for .claude/bin/tusk-task-worktree.py symlink-seeding helpers.

The previous suite exercised private wrappers (_ensure_scraper_venv_available,
_ensure_workspace_resources_available) that were replaced by a generic config-
driven path: _load_symlink_files reads worktree.symlink_files from the project
config, and _link_gitignored_files walks the primary checkout creating absolute-
path symlinks for entries whose basename matches the list.
"""

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / ".claude" / "bin" / "tusk-task-worktree.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tusk_task_worktree", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_link_gitignored_files_symlinks_scraper_venv_from_primary(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    source_venv = primary / "apps" / "scraper" / ".venv"
    source_venv.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    (workspace / "apps" / "scraper").mkdir(parents=True)

    created = module._link_gitignored_files(str(primary), str(workspace), [".venv"])

    linked_venv = workspace / "apps" / "scraper" / ".venv"
    assert linked_venv.is_symlink()
    assert linked_venv.resolve() == source_venv
    assert created == [{"src": str(source_venv), "dst": str(linked_venv)}]


def test_link_gitignored_files_leaves_existing_workspace_venv_alone(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    (primary / "apps" / "scraper" / ".venv").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    existing_venv = workspace / "apps" / "scraper" / ".venv"
    existing_venv.mkdir(parents=True)

    created = module._link_gitignored_files(str(primary), str(workspace), [".venv"])

    assert created == []
    assert existing_venv.is_dir()
    assert not existing_venv.is_symlink()


def test_link_gitignored_files_symlinks_web_and_scraper_resources(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    source_node_modules = primary / "apps" / "web" / "node_modules"
    source_node_modules.mkdir(parents=True)
    source_web_env = primary / "apps" / "web" / ".env.local"
    source_web_env.write_text("NEXTAUTH_SECRET=test\n")
    source_scraper_env = primary / "apps" / "scraper" / ".env"
    source_scraper_env.parent.mkdir(parents=True, exist_ok=True)
    source_scraper_env.write_text("DATABASE_HOST=example.test\n")

    workspace = tmp_path / "workspace"
    (workspace / "apps" / "web").mkdir(parents=True)
    (workspace / "apps" / "scraper").mkdir(parents=True)

    created = module._link_gitignored_files(
        str(primary),
        str(workspace),
        ["node_modules", ".env.local", ".env"],
    )

    linked_node_modules = workspace / "apps" / "web" / "node_modules"
    linked_web_env = workspace / "apps" / "web" / ".env.local"
    linked_scraper_env = workspace / "apps" / "scraper" / ".env"

    assert linked_node_modules.is_symlink()
    assert linked_node_modules.resolve() == source_node_modules
    assert linked_web_env.is_symlink()
    assert linked_web_env.resolve() == source_web_env
    assert linked_scraper_env.is_symlink()
    assert linked_scraper_env.resolve() == source_scraper_env

    created_dsts = {entry["dst"] for entry in created}
    assert created_dsts == {
        str(linked_node_modules),
        str(linked_web_env),
        str(linked_scraper_env),
    }


def test_link_gitignored_files_leaves_existing_local_files_alone(tmp_path):
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

    created = module._link_gitignored_files(
        str(primary),
        str(workspace),
        ["node_modules", ".env.local"],
    )

    assert created == []
    assert existing_node_modules.is_dir()
    assert not existing_node_modules.is_symlink()
    assert existing_web_env.read_text() == "NEXTAUTH_SECRET=workspace\n"
    assert not existing_web_env.is_symlink()


def test_link_gitignored_files_skips_git_directory(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    (primary / ".git" / ".venv").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    created = module._link_gitignored_files(str(primary), str(workspace), [".venv"])

    assert created == []
    assert not (workspace / ".git" / ".venv").exists()


def test_link_gitignored_files_returns_empty_when_names_is_empty(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    (primary / "apps" / "scraper" / ".venv").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    assert module._link_gitignored_files(str(primary), str(workspace), []) == []


def test_link_gitignored_files_leaves_broken_symlink_at_destination_alone(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    source_venv = primary / "apps" / "scraper" / ".venv"
    source_venv.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    dst_parent = workspace / "apps" / "scraper"
    dst_parent.mkdir(parents=True)
    broken_target = workspace / "does-not-exist"
    broken_symlink = dst_parent / ".venv"
    broken_symlink.symlink_to(broken_target)
    assert broken_symlink.is_symlink()
    assert not broken_symlink.exists()  # confirm it is broken

    created = module._link_gitignored_files(str(primary), str(workspace), [".venv"])

    assert created == []
    assert broken_symlink.is_symlink()
    assert broken_symlink.readlink() == broken_target


def test_link_gitignored_files_does_not_recurse_into_symlinked_directory(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    outer_venv = primary / "apps" / "scraper" / ".venv"
    # A nested directory whose basename also matches names — if the walk
    # descended into the outer match it would create a second symlink under
    # the just-linked tree.
    (outer_venv / "nested" / ".venv").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    (workspace / "apps" / "scraper").mkdir(parents=True)

    created = module._link_gitignored_files(str(primary), str(workspace), [".venv"])

    linked_outer = workspace / "apps" / "scraper" / ".venv"
    assert linked_outer.is_symlink()
    assert linked_outer.resolve() == outer_venv
    assert len(created) == 1
    assert created[0]["dst"] == str(linked_outer)


def test_link_gitignored_files_creates_missing_parent_directories(tmp_path):
    module = _load_module()
    primary = tmp_path / "primary"
    source_venv = primary / "apps" / "scraper" / ".venv"
    source_venv.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()  # bare — no apps/scraper subtree

    created = module._link_gitignored_files(str(primary), str(workspace), [".venv"])

    linked_venv = workspace / "apps" / "scraper" / ".venv"
    assert linked_venv.is_symlink()
    assert linked_venv.resolve() == source_venv
    assert created == [{"src": str(source_venv), "dst": str(linked_venv)}]


def test_load_symlink_files_parses_worktree_config(tmp_path):
    module = _load_module()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "worktree": {
                    "symlink_files": [
                        ".venv",
                        "node_modules",
                        ".env",
                    ]
                }
            }
        )
    )

    assert module._load_symlink_files(str(config_path)) == [
        ".venv",
        "node_modules",
        ".env",
    ]


def test_load_symlink_files_returns_empty_on_missing_file(tmp_path):
    module = _load_module()
    assert module._load_symlink_files(str(tmp_path / "missing.json")) == []


def test_load_symlink_files_returns_empty_on_malformed_json(tmp_path):
    module = _load_module()
    bad = tmp_path / "config.json"
    bad.write_text("{not json")
    assert module._load_symlink_files(str(bad)) == []


def test_load_symlink_files_returns_empty_when_worktree_key_missing(tmp_path):
    module = _load_module()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"other": "value"}))
    assert module._load_symlink_files(str(config_path)) == []


def test_load_symlink_files_filters_non_string_entries(tmp_path):
    module = _load_module()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"worktree": {"symlink_files": [".venv", None, "", 42, "node_modules"]}}
        )
    )
    assert module._load_symlink_files(str(config_path)) == [".venv", "node_modules"]
