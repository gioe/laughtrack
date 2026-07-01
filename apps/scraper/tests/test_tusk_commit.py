import importlib.util
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / ".claude" / "bin" / "tusk-commit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tusk_commit", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=check,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")


def test_commit_stages_unstaged_deletion_with_ignored_tracked_file(
    monkeypatch, tmp_path
):
    module = _load_module()
    repo = tmp_path / "repo"
    _init_repo(repo)

    (repo / ".gitignore").write_text(".claude/bin/\n")
    ignored_tracked = repo / ".claude" / "bin" / "tracked-tool"
    ignored_tracked.parent.mkdir(parents=True)
    ignored_tracked.write_text("old\n")
    deleted_tracked = repo / ".agents" / "skills" / "demo" / "SKILL.md"
    deleted_tracked.parent.mkdir(parents=True)
    deleted_tracked.write_text("skill\n")

    _git(repo, "add", ".gitignore", ".agents/skills/demo/SKILL.md")
    _git(repo, "add", "-f", ".claude/bin/tracked-tool")
    _git(repo, "commit", "-m", "initial")

    ignored_tracked.write_text("new\n")
    deleted_tracked.unlink()

    monkeypatch.setattr(
        module,
        "_validate_task_branch",
        lambda repo_root, task_id, allow_branch_mismatch: (True, ""),
    )
    monkeypatch.chdir(repo)
    config_path = repo / "config.json"
    config_path.write_text("{}")

    rc = module.main(
        [
            str(repo),
            str(config_path),
            "1",
            "commit mixed tracked ignored and deletion",
            ".claude/bin/tracked-tool",
            ".agents/skills/demo/SKILL.md",
            "--skip-verify",
        ]
    )

    assert rc == 0
    status = _git(repo, "status", "--short").stdout
    assert status == "?? config.json\n"
    committed = _git(repo, "show", "--name-status", "--format=", "HEAD").stdout
    assert "D\t.agents/skills/demo/SKILL.md" in committed
    assert "M\t.claude/bin/tracked-tool" in committed
