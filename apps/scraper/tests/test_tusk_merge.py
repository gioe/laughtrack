import importlib.util
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / ".claude" / "bin" / "tusk-merge.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tusk_merge", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _ok(args, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=stderr)


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
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")


def test_no_checkout_fast_forward_updates_local_default_ref(monkeypatch):
    module = _load_module()
    calls = []
    close_kwargs = {}

    def fake_run(args, check=True):
        calls.append(args)
        if args[:2] == ["git", "rev-parse"]:
            if args[-1] == "feature/TASK-1-demo":
                return _ok(args, stdout="feature-tip\n")
            if args[-1] == "main":
                return _ok(args, stdout="old-main\n")
        return _ok(args)

    monkeypatch.setattr(module, "run", fake_run)
    monkeypatch.setattr(module, "_origin_already_contains", lambda *_: False)
    monkeypatch.setattr(module, "_local_default_unpushed_commits", lambda *_: [])
    monkeypatch.setattr(module, "_resolve_merge_base", lambda *_: "base-sha")
    monkeypatch.setattr(module, "_delete_remote_feature_branch_if_tracking", lambda *_: None)
    monkeypatch.setattr(module, "checkpoint_wal", lambda *_: None)
    monkeypatch.setattr(module, "_run_tusk_subcommand", lambda *_: _ok(["tusk"]))
    monkeypatch.setattr(module, "_try_pop_stash", lambda *_: None)
    monkeypatch.setattr(module, "_warn_branch_auto_stash", lambda *_: None)

    def fake_close_completed_task(*args, **kwargs):
        close_kwargs.update(kwargs)
        return 0

    monkeypatch.setattr(module, "_close_completed_task", fake_close_completed_task)
    monkeypatch.setattr(module, "_maybe_refresh_deployed_bin", lambda *_: False)
    monkeypatch.setattr(module, "_maybe_advise_stale_deployed_bin", lambda *_, **__: "sync_succeeded")
    monkeypatch.setattr(module, "_cleanup_no_checkout_workspace", lambda *_: True)
    monkeypatch.setattr(module, "_reconcile_duplicate_task_workspaces", lambda *_: True)

    rc = module._complete_no_checkout_fast_forward(
        branch_name="feature/TASK-1-demo",
        default_branch="main",
        task_id=1,
        session_id=2,
        tusk_bin="/repo/.claude/bin/tusk",
        db_path="/repo/tusk/tasks.db",
        session_was_closed=False,
        did_stash=False,
        use_rebase=False,
    )

    assert rc == 0
    assert [
        "git",
        "update-ref",
        "refs/heads/main",
        "feature-tip",
        "old-main",
    ] in calls
    assert close_kwargs["merge_commit_sha"] == "feature-tip"
    assert close_kwargs["merge_base_sha"] == "base-sha"


def test_fast_forward_local_default_ref_leaves_files_and_index_untouched(monkeypatch, tmp_path):
    module = _load_module()
    repo = tmp_path / "repo"
    _init_repo(repo)

    tracked = repo / "file.txt"
    tracked.write_text("old\n")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "old")
    old_main = _git(repo, "rev-parse", "main").stdout.strip()
    old_index = _git(repo, "ls-files", "--stage", "file.txt").stdout

    feature = tmp_path / "feature"
    _git(repo, "worktree", "add", "-b", "feature", str(feature))
    (feature / "file.txt").write_text("new\n")
    _git(feature, "commit", "-am", "new")
    feature_tip = _git(feature, "rev-parse", "feature").stdout.strip()

    monkeypatch.chdir(feature)

    assert module._fast_forward_local_default_ref("main", feature_tip) is True
    assert _git(repo, "rev-parse", "main").stdout.strip() == feature_tip
    assert _git(repo, "rev-parse", "main@{1}").stdout.strip() == old_main
    assert tracked.read_text() == "old\n"
    assert _git(repo, "ls-files", "--stage", "file.txt").stdout == old_index
