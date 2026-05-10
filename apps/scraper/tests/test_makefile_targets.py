from pathlib import Path


MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"


def _target_prerequisites(target: str) -> list[str]:
    for line in MAKEFILE.read_text().splitlines():
        if not line.startswith(f"{target}:"):
            continue

        _, prerequisites = line.split(":", 1)
        return prerequisites.split()

    raise AssertionError(f"target {target!r} not found in {MAKEFILE}")


def test_targeted_scrape_targets_link_worktree_env_before_loading_config():
    assert "check-env" in _target_prerequisites("scrape-club")
    assert "check-env" in _target_prerequisites("scrape-club-id")
