import importlib.util
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / ".claude" / "bin" / "tusk-task-start.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tusk_task_start", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_force_session_diagnostics_warn_for_dirty_recorded_worktree(monkeypatch):
    module = _load_module()
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["git", "-C", "/tmp/task-worktree"]:
            if args[3:] == ["status", "--porcelain"]:
                return subprocess.CompletedProcess(
                    args, 0, stdout=" M .claude/bin/tusk-task-start.py\n?? notes.txt\n"
                )
            if args[3:] == ["branch", "--show-current"]:
                return subprocess.CompletedProcess(args, 0, stdout="feature/TASK-42-demo\n")
        if args[:3] == ["git", "-C", "/repo"] and args[3:] == [
            "merge-base",
            "--is-ancestor",
            "abc123",
            "feature/TASK-42-demo",
        ]:
            return subprocess.CompletedProcess(args, 0, stdout="")
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        module._git_helpers,
        "find_task_commits_with_recovery",
        lambda task_id, repo_root: (["abc123"], None),
    )

    warnings = module._force_session_workspace_warnings(42, "/tmp/task-worktree", "/repo")

    assert any("recorded task workspace is dirty" in warning for warning in warnings)
    assert any("/tmp/task-worktree" in warning for warning in warnings)
    assert any("M .claude/bin/tusk-task-start.py" in warning for warning in warnings)
    assert any("?? notes.txt" in warning for warning in warnings)
    assert ["git", "-C", "/tmp/task-worktree", "status", "--porcelain"] in calls


def test_force_session_diagnostics_warn_when_branch_lost_task_commit(monkeypatch):
    module = _load_module()

    def fake_run(args, **kwargs):
        if args[:3] == ["git", "-C", "/tmp/task-worktree"] and args[3:] == [
            "status",
            "--porcelain",
        ]:
            return subprocess.CompletedProcess(args, 0, stdout="")
        if args[:3] == ["git", "-C", "/tmp/task-worktree"] and args[3:] == [
            "branch",
            "--show-current",
        ]:
            return subprocess.CompletedProcess(args, 0, stdout="feature/TASK-42-demo\n")
        if args[:3] == ["git", "-C", "/repo"] and args[3:] == [
            "merge-base",
            "--is-ancestor",
            "abc123",
            "feature/TASK-42-demo",
        ]:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        module._git_helpers,
        "find_task_commits_with_recovery",
        lambda task_id, repo_root: (["abc123"], "fsck-unreachable"),
    )

    warnings = module._force_session_workspace_warnings(42, "/tmp/task-worktree", "/repo")

    assert any("does not contain 1 existing [TASK-42] commit" in warning for warning in warnings)
    assert any("abc123" in warning for warning in warnings)
    assert any("recovered via fsck-unreachable" in warning for warning in warnings)


def test_force_session_diagnostics_are_best_effort(monkeypatch):
    module = _load_module()

    def boom(*args, **kwargs):
        raise OSError("git unavailable")

    monkeypatch.setattr(module.subprocess, "run", boom)
    monkeypatch.setattr(
        module._git_helpers,
        "find_task_commits_with_recovery",
        lambda task_id, repo_root: (_ for _ in ()).throw(RuntimeError("scan failed")),
    )

    assert module._force_session_workspace_warnings(42, "/tmp/task-worktree", "/repo") == []
